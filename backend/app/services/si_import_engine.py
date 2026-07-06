"""
社保公积金智能导入引擎
支持：Excel(xlsx/xls) + PDF 多文件批量上传、多模板自动匹配、字段映射、
      员工姓名匹配、多层级数据校验
"""
import re
import uuid
import io
import logging
from typing import List, Dict, Optional, Tuple
from decimal import Decimal, ROUND_HALF_EVEN

from sqlalchemy.orm import Session

from app.models.models import (
    SocialInsurance, Employee, SiImportTemplate, SiImportLog
)

logger = logging.getLogger(__name__)

# ── 所有可映射字段及其中文标签 ──────────────────────────────────────────
SI_FIELD_LABELS = {
    "employee_name": "员工姓名",
    "employee_social_insurance_no": "个人社保号",
    "period": "缴费月份",
    "si_base": "社保缴存基数",
    "pension_personal_base": "养老保险个人基数",
    "pension_company_base": "养老保险单位基数",
    "unemployment_personal_base": "失业保险个人基数",
    "unemployment_company_base": "失业保险单位基数",
    "medical_personal_base": "医疗保险个人基数",
    "medical_company_base": "医疗保险单位基数",
    "injury_company_base": "工伤保险单位基数",
    "pension_personal": "养老保险个人金额",
    "pension_personal_rate": "养老保险个人比例",
    "pension_company": "养老保险单位金额",
    "pension_company_rate": "养老保险单位比例",
    "unemployment_personal": "失业保险个人金额",
    "unemployment_personal_rate": "失业保险个人比例",
    "unemployment_company": "失业保险单位金额",
    "unemployment_company_rate": "失业保险单位比例",
    "medical_personal": "医疗保险个人金额",
    "medical_personal_rate": "医疗保险个人比例",
    "medical_company": "医疗保险单位金额",
    "medical_company_rate": "医疗保险单位比例",
    "injury_company": "工伤保险单位金额",
    "injury_company_rate": "工伤保险单位比例",
    "si_personal": "社保个人合计",
    "si_company": "社保单位合计",
    "hf_base": "公积金缴存基数",
    "hf_personal": "公积金个人金额",
    "hf_personal_rate": "公积金个人比例",
    "hf_company": "公积金单位金额",
    "hf_company_rate": "公积金单位比例",
    "pension_total": "养老保险合计",
    "unemployment_total": "失业保险合计",
    "medical_total": "医疗保险合计",
    "injury_total": "工伤保险合计",
    "si_grand_total": "社保总合计",
    "hf_total": "公积金合计",
    "grand_total": "社保公积金总合计",
}

# 金额类字段（需要做数值解析和校验）
AMOUNT_FIELDS = [
    "si_base",
    "pension_personal_base", "pension_company_base",
    "unemployment_personal_base", "unemployment_company_base",
    "medical_personal_base", "medical_company_base",
    "injury_company_base",
    "pension_personal", "pension_personal_rate",
    "pension_company", "pension_company_rate",
    "unemployment_personal", "unemployment_personal_rate",
    "unemployment_company", "unemployment_company_rate",
    "medical_personal", "medical_personal_rate",
    "medical_company", "medical_company_rate",
    "injury_company", "injury_company_rate",
    "si_personal", "si_company",
    "hf_base", "hf_personal", "hf_personal_rate",
    "hf_company", "hf_company_rate",
    "pension_total", "unemployment_total", "medical_total", "injury_total",
    "si_grand_total", "hf_total", "grand_total",
    # 通用字段（AI/规则降级时使用，后续由 _resolve_insurance_fields 转为特定险种字段）
    "amount", "rate",
]

# 必须字段（导入时至少要有姓名）
REQUIRED_FIELDS = ["employee_name"]


class ImportResult:
    """导入结果"""
    def __init__(self):
        self.total_files = 0
        self.parsed_files = 0
        self.failed_files = 0
        self.total_rows = 0
        self.created = 0
        self.updated = 0
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []


def _parse_number(value, number_format: Optional[Dict] = None) -> Optional[Decimal]:
    """将单元格值解析为 Decimal"""
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        if isinstance(value, float):
            return Decimal(str(value))
        return Decimal(value)
    s = str(value).strip()
    if not s or s in ("-", "--", "——", "/"):
        return None
    # 根据模板配置去除不需要的字符
    remove_chars = (number_format or {}).get("remove_chars", [","])
    for ch in remove_chars:
        s = s.replace(ch, "")
    # 去除中文单位
    s = re.sub(r"[元圆]", "", s)
    s = s.strip()
    # 处理百分比：10% → 0.10，费率精度保留4位小数（如 0.5000% → 0.0050）
    if s.endswith("%"):
        try:
            return (Decimal(s[:-1]) / Decimal("100")).quantize(Decimal("0.0001"))
        except Exception:
            return None
    try:
        return Decimal(s)
    except Exception:
        return None


def _parse_excel(file_bytes: bytes, filename: str) -> List[List]:
    """解析 Excel 文件，返回二维列表（每行是一个列表），支持合并单元格填充"""
    if filename.lower().endswith(".xls"):
        try:
            import xlrd
            wb = xlrd.open_workbook(file_contents=file_bytes, formatting_info=True)
            ws = wb.sheet_by_index(0)
            
            # 构建合并单元格映射：(row, col) -> value
            merged_values = {}
            for (rlo, rhi, clo, chi) in ws.merged_cells:
                # 获取合并区域左上角的值
                parent_value = ws.cell(rlo, clo).value
                # 填充整个合并区域
                for r in range(rlo, rhi):
                    for c in range(clo, chi):
                        merged_values[(r, c)] = parent_value
            
            rows = []
            for r in range(ws.nrows):
                row = []
                for c in range(ws.ncols):
                    # 优先使用合并单元格的值
                    if (r, c) in merged_values:
                        row.append(merged_values[(r, c)])
                    else:
                        cell = ws.cell(r, c)
                        row.append(cell.value)
                rows.append(row)
            return rows
        except Exception:
            # xlrd 2.0+ 不支持 .xlsx 格式，但有些 .xls 文件实际是 xlsx 格式
            # 降级用 openpyxl 重试
            pass
    # 默认用 openpyxl（支持 .xlsx 和伪装的 .xls）
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active
    
    # 构建合并单元格映射
    merged_values = {}
    for merged_range in ws.merged_cells.ranges:
        # 获取合并区域左上角的值
        min_row, min_col = merged_range.min_row - 1, merged_range.min_col - 1  # openpyxl 是 1-based
        parent_value = ws.cell(merged_range.min_row, merged_range.min_col).value
        # 填充整个合并区域（转为 0-based）
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for col in range(merged_range.min_col, merged_range.max_col + 1):
                merged_values[(row - 1, col - 1)] = parent_value
    
    rows = []
    for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
        row_data = []
        for col_idx, cell_value in enumerate(row):
            # 优先使用合并单元格的值
            if (row_idx, col_idx) in merged_values:
                row_data.append(merged_values[(row_idx, col_idx)])
            else:
                row_data.append(cell_value)
        rows.append(row_data)
    return rows


def _parse_pdf(file_bytes: bytes) -> List[List]:
    """解析 PDF 文件，提取表格数据"""
    import pdfplumber
    all_rows = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and any(cell for cell in row):
                        all_rows.append([cell.strip() if cell else "" for cell in row])
    return all_rows


def _match_template(
    db: Session,
    file_rows: List[List],
    filename: str,
) -> Optional[SiImportTemplate]:
    """为文件匹配最合适的导入模板"""
    templates = (
        db.query(SiImportTemplate)
        .filter(SiImportTemplate.is_active == True)
        .order_by(SiImportTemplate.sort_order)
        .all()
    )
    if not templates:
        return None

    best_template = None
    best_score = 0

    for tpl in templates:
        score = 0

        # 1. 文件名正则匹配
        if tpl.file_pattern:
            try:
                if re.search(tpl.file_pattern, filename, re.IGNORECASE):
                    score += 50
            except re.error:
                pass

        # 2. 文件类型匹配
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if tpl.file_type == "excel" and ext in ("xlsx", "xls"):
            score += 10
        elif tpl.file_type == "pdf" and ext == "pdf":
            score += 10

        # 3. 表头列名匹配
        if tpl.header_rows and tpl.column_mappings:
            header_indices = tpl.header_rows if isinstance(tpl.header_rows, list) else [tpl.header_rows]
            for hr in header_indices:
                if hr < len(file_rows):
                    header_row = file_rows[hr]
                    header_texts = [str(c).strip() if c else "" for c in header_row]
                    mapping_keys = list(tpl.column_mappings.keys())
                    matched = sum(1 for k in mapping_keys if k in header_texts)
                    if mapping_keys:
                        score += int(matched / len(mapping_keys) * 40)

        if score > best_score:
            best_score = score
            best_template = tpl

    if best_score >= 10:
        return best_template
    return None


def _build_column_index(
    file_rows: List[List],
    template: SiImportTemplate,
) -> Dict[str, int]:
    """根据模板的表头配置，建立「数据库字段名 → 文件列序号」的映射"""
    column_index = {}
    header_indices = template.header_rows if isinstance(template.header_rows, list) else [template.header_rows]

    # 合并多层表头为一行，用 " - " 分隔不同层级
    merged_header = []
    if header_indices:
        max_cols = max(len(file_rows[hr]) if hr < len(file_rows) else 0 for hr in header_indices)
        for col_idx in range(max_cols):
            parts = []
            for hr in header_indices:
                if hr < len(file_rows) and col_idx < len(file_rows[hr]):
                    val = str(file_rows[hr][col_idx]).strip() if file_rows[hr][col_idx] else ""
                    if val:
                        # 避免重复：如果和上一个 part 相同，则跳过
                        if not parts or val != parts[-1]:
                            parts.append(val)
            # 多层用 " - " 连接，单层直接用
            merged_header.append(" - ".join(parts) if len(parts) > 1 else (parts[0] if parts else ""))

    # 按 column_mappings 匹配（多级策略，从精确到模糊）
    mappings = template.column_mappings or {}
    for header_name, db_field in mappings.items():
        if not db_field:  # 跳过未映射的列
            continue

        best_idx = None

        # 策略1：精确包含匹配
        for idx, header_text in enumerate(merged_header):
            if header_text and header_name and (
                header_name in header_text or header_text in header_name
            ):
                best_idx = idx
                break

        # 策略2：去除 " - " 分隔符后再匹配
        # 场景：模板 key="基本养老保险(单位缴纳)缴费基数"，合并表头="基本养老保险(单位缴纳) - 缴费基数"
        if best_idx is None:
            hdr_compact = header_name.replace(" - ", "").replace(" ", "").replace("\u3000", "")
            for idx, header_text in enumerate(merged_header):
                if not header_text:
                    continue
                text_compact = header_text.replace(" - ", "").replace(" ", "").replace("\u3000", "")
                if hdr_compact in text_compact or text_compact in hdr_compact:
                    best_idx = idx
                    break

        # 策略3：将模板 key 按 "-" 或空格拆成词组，检查所有词组是否都在 header_text 中
        # 场景：模板 key="工伤保险缴费基数"，合并表头="工伤保险 - 缴费基数"
        if best_idx is None:
            import re as _re
            tokens = [t for t in _re.split(r"\s*[-]\s*|\s+", header_name) if t]
            for idx, header_text in enumerate(merged_header):
                if not header_text:
                    continue
                if all(t in header_text for t in tokens):
                    best_idx = idx
                    break

        # 策略4：前两个字符模糊匹配（兜底）
        if best_idx is None:
            for idx, header_text in enumerate(merged_header):
                if header_name and header_text and len(header_name) >= 2 and (
                    header_name[:2] in header_text or header_text[:2] in header_name
                ):
                    best_idx = idx
                    break

        if best_idx is not None:
            column_index[db_field] = best_idx

    return column_index


def _extract_data(
    file_rows: List[List],
    template: SiImportTemplate,
    filename: str,
    period: str,
    logs: List[Dict],
    batch_id: str,
) -> List[Dict]:
    """根据模板从文件行中提取结构化数据"""
    column_index = _build_column_index(file_rows, template)
    if "employee_name" not in column_index:
        logs.append({
            "file_name": filename, "row_number": None,
            "error_level": "error", "error_type": "template_error",
            "error_message": f"模板「{template.name}」未配置「员工姓名」字段映射，无法导入",
        })
        return []

    row_filters = template.row_filters or {}
    number_format = template.number_format or {}
    data_start = template.data_start_row
    skip_footer = template.skip_footer_rows or 0
    end_row = len(file_rows) - skip_footer if skip_footer > 0 else len(file_rows)

    results = []
    for row_idx in range(data_start, end_row):
        row = file_rows[row_idx] if row_idx < len(file_rows) else []
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue

        # 行过滤
        skip = False
        for filter_col, filter_val in row_filters.items():
            if filter_col not in column_index:
                continue
            ci = column_index[filter_col]
            cell_val = str(row[ci]).strip() if ci < len(row) and row[ci] else ""
            # 支持多种过滤操作符
            if isinstance(filter_val, dict):
                if "$not_in" in filter_val and cell_val in filter_val["$not_in"]:
                    skip = True; break
                if "$not_empty" in filter_val and filter_val["$not_empty"] and not cell_val:
                    skip = True; break
                if "$eq" in filter_val and cell_val != filter_val["$eq"]:
                    skip = True; break
            else:
                if cell_val != str(filter_val):
                    skip = True; break
        if skip:
            continue

        record = {}
        for db_field, col_idx in column_index.items():
            if col_idx < len(row):
                raw_val = row[col_idx]
                if db_field in AMOUNT_FIELDS:
                    val = _parse_number(raw_val, number_format)
                elif db_field == "period" and raw_val:
                    val = str(raw_val).strip()
                else:
                    val = str(raw_val).strip() if raw_val else ""
                record[db_field] = val

        # 设置核算月份
        if not record.get("period"):
            record["period"] = period

        # 姓名检查
        name = record.get("employee_name", "")
        if not name:
            logs.append({
                "file_name": filename, "row_number": row_idx + 1,
                "error_level": "warning", "error_type": "empty_name",
                "error_message": f"第{row_idx + 1}行员工姓名为空，已跳过",
            })
            continue

        record["_source_file"] = filename
        record["_source_row"] = row_idx + 1
        results.append(record)

    return results


def _aggregate_by_name(all_records: List[Dict]) -> Dict[str, Dict]:
    """按员工姓名聚合多文件数据"""
    aggregated = {}
    for rec in all_records:
        name = rec.get("employee_name", "")
        if name not in aggregated:
            aggregated[name] = {
                "employee_name": name,
                "period": rec.get("period", ""),
                "_sources": [],
            }
        # 合并字段：非空值覆盖空值，金额字段取最大值（多数情况同一字段只有一个来源）
        for key, value in rec.items():
            if key.startswith("_"):
                if key == "_source_file":
                    aggregated[name]["_sources"].append({
                        "file": rec.get("_source_file", ""),
                        "row": rec.get("_source_row", ""),
                    })
                continue
            if value is not None and value != "":
                existing = aggregated[name].get(key)
                if existing is None or existing == "" or existing == 0:
                    aggregated[name][key] = value
                elif isinstance(value, (int, float, Decimal)) and value != 0:
                    if existing == 0:
                        aggregated[name][key] = value
    return aggregated


def _match_employees(
    db: Session,
    aggregated: Dict[str, Dict],
    logs: List[Dict],
    batch_id: str,
) -> Tuple[Dict[str, Dict], List[str]]:
    """按姓名匹配员工档案，返回 (有效数据, 跳过姓名列表)"""
    employees = db.query(Employee).all()
    # 按姓名建索引，注意同名情况
    name_index: Dict[str, List[Employee]] = {}
    for emp in employees:
        name_index.setdefault(emp.name, []).append(emp)

    valid_data = {}
    skipped = []

    for name, record in aggregated.items():
        matches = name_index.get(name, [])
        if not matches:
            logs.append({
                "file_name": ", ".join(s["file"] for s in record.get("_sources", [])),
                "row_number": None,
                "employee_name": name,
                "error_level": "warning",
                "error_type": "name_not_found",
                "error_message": f"员工「{name}」在系统中未找到，请确认姓名是否正确或该员工是否已录入档案",
            })
            skipped.append(name)
            continue

        if len(matches) > 1:
            logs.append({
                "file_name": ", ".join(s["file"] for s in record.get("_sources", [])),
                "row_number": None,
                "employee_name": name,
                "error_level": "warning",
                "error_type": "duplicate_name",
                "error_message": f"系统中有{len(matches)}名同名员工「{name}」，已自动匹配第一条记录（工号：{matches[0].employee_no}），请确认是否正确",
            })

        record["employee_id"] = matches[0].id
        record["employee_no"] = matches[0].employee_no
        valid_data[name] = record

    return valid_data, skipped


def _validate_data(
    records: Dict[str, Dict],
    logs: List[Dict],
    batch_id: str,
):
    """多层级数据校验"""
    for name, record in records.items():
        source_info = ", ".join(s["file"] for s in record.get("_sources", []))

        # 1. 缴存基数检查
        si_base = record.get("si_base")
        if si_base is None or (isinstance(si_base, Decimal) and si_base == 0):
            logs.append({
                "file_name": source_info,
                "employee_name": name,
                "error_level": "warning",
                "error_type": "missing_base",
                "error_message": f"员工「{name}」缴存基数为空或为0",
            })

        # 2. 缴费月份检查
        period = record.get("period", "")
        if not period or len(str(period)) < 6:
            logs.append({
                "file_name": source_info,
                "employee_name": name,
                "error_level": "error",
                "error_type": "missing_period",
                "error_message": f"员工「{name}」缴费月份缺失或格式错误",
            })

        # 3. 金额逻辑校验：基数 × 比例 ≈ 金额（允许1元误差）
        checks = [
            ("pension_personal", "pension_personal_rate", "si_base"),
            ("pension_company", "pension_company_rate", "si_base"),
            ("unemployment_personal", "unemployment_personal_rate", "si_base"),
            ("unemployment_company", "unemployment_company_rate", "si_base"),
            ("medical_personal", "medical_personal_rate", "si_base"),
            ("medical_company", "medical_company_rate", "si_base"),
            ("injury_company", "injury_company_rate", "si_base"),
            ("hf_personal", "hf_personal_rate", "hf_base"),
            ("hf_company", "hf_company_rate", "hf_base"),
        ]
        for amount_field, rate_field, base_field in checks:
            amount = record.get(amount_field)
            rate = record.get(rate_field)
            base = record.get(base_field)
            if (amount and isinstance(amount, Decimal) and amount > 0
                    and rate and isinstance(rate, Decimal) and rate > 0
                    and base and isinstance(base, Decimal) and base > 0):
                expected = (base * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
                diff = abs(amount - expected)
                if diff > Decimal("1.00"):
                    field_label = SI_FIELD_LABELS.get(amount_field, amount_field)
                    logs.append({
                        "file_name": source_info,
                        "employee_name": name,
                        "error_level": "warning",
                        "error_type": "amount_mismatch",
                        "error_message": (
                            f"员工「{name}」{field_label}金额不匹配："
                            f"基数{base} × 比例{rate} = 期望{expected}，实际{amount}，差额{diff}"
                        ),
                    })


def _calc_summaries(si_record):
    """自动计算所有合计/汇总字段"""
    # 各险种合计
    si_record.pension_total = Decimal(str((si_record.pension_personal or 0) + (si_record.pension_company or 0)))
    si_record.unemployment_total = Decimal(str((si_record.unemployment_personal or 0) + (si_record.unemployment_company or 0)))
    si_record.medical_total = Decimal(str((si_record.medical_personal or 0) + (si_record.medical_company or 0)))
    si_record.injury_total = Decimal(str(si_record.injury_company or 0))

    # 社保个人/单位合计
    si_record.si_personal = Decimal(str(
        (si_record.pension_personal or 0) + (si_record.unemployment_personal or 0) + (si_record.medical_personal or 0)
    ))
    si_record.si_company = Decimal(str(
        (si_record.pension_company or 0) + (si_record.unemployment_company or 0) +
        (si_record.medical_company or 0) + (si_record.injury_company or 0)
    ))
    si_record.si_grand_total = Decimal(str((si_record.si_personal or 0) + (si_record.si_company or 0)))

    # 公积金合计
    si_record.hf_total = Decimal(str((si_record.hf_personal or 0) + (si_record.hf_company or 0)))

    # 社保公积金总合计
    si_record.grand_total = Decimal(str((si_record.si_grand_total or 0) + (si_record.hf_total or 0)))


def _save_records(
    db: Session,
    period: str,
    records: Dict[str, Dict],
    user_id: int,
    username: str,
    logs: List[Dict],
    batch_id: str,
) -> Tuple[int, int]:
    """保存数据到数据库（新增或更新）"""
    created = 0
    updated = 0

    # 获取现有记录
    existing_map = {}
    existing_records = db.query(SocialInsurance).filter(
        SocialInsurance.period == period
    ).all()
    for r in existing_records:
        existing_map[r.employee_id] = r

    # 数值型字段列表（用于判断导入值是否为0/null以决定是否保留旧值）
    numeric_fields = set([
        "si_base", "pension_personal_base", "pension_company_base",
        "unemployment_personal_base", "unemployment_company_base",
        "medical_personal_base", "medical_company_base",
        "injury_company_base",
        "pension_personal", "pension_personal_rate",
        "pension_company", "pension_company_rate",
        "unemployment_personal", "unemployment_personal_rate",
        "unemployment_company", "unemployment_company_rate",
        "medical_personal", "medical_personal_rate",
        "medical_company", "medical_company_rate",
        "injury_company", "injury_company_rate",
        "si_personal", "si_company",
        "hf_base", "hf_personal", "hf_personal_rate",
        "hf_company", "hf_company_rate",
        "pension_total", "unemployment_total", "medical_total", "injury_total",
        "si_grand_total", "hf_total", "grand_total",
    ])

    for name, record in records.items():
        emp_id = record.get("employee_id")
        if not emp_id:
            continue

        # 检查同一周期是否有重复
        existing = existing_map.get(emp_id)
        if existing:
            existing_map.pop(emp_id, None)  # 已处理则移除

        # 构造写入数据
        write_fields = [
            "employee_social_insurance_no",
            # 社保 — 各险种单独基数
            "si_base", "pension_personal_base", "pension_company_base",
            "unemployment_personal_base", "unemployment_company_base",
            "medical_personal_base", "medical_company_base",
            "injury_company_base",
            # 社保 — 个人/单位 金额
            "pension_personal", "pension_personal_rate",
            "pension_company", "pension_company_rate",
            "unemployment_personal", "unemployment_personal_rate",
            "unemployment_company", "unemployment_company_rate",
            "medical_personal", "medical_personal_rate",
            "medical_company", "medical_company_rate",
            "injury_company", "injury_company_rate",
            "si_personal", "si_company",
            # 公积金
            "hf_base", "hf_personal", "hf_personal_rate",
            "hf_company", "hf_company_rate",
            # 合计字段
            "pension_total", "unemployment_total", "medical_total", "injury_total",
            "si_grand_total", "hf_total", "grand_total",
        ]
        si_data = {"period": period, "employee_id": emp_id}
        for f in write_fields:
            val = record.get(f)
            if isinstance(val, Decimal):
                si_data[f] = val
            else:
                si_data[f] = val or 0

        # si_base 兜底：如果模板未直接映射 si_base，用养老保险单位基数填充
        if not si_data.get("si_base") and si_data.get("pension_company_base"):
            si_data["si_base"] = si_data["pension_company_base"]

        if existing:
            for key, value in si_data.items():
                if key not in ("period", "employee_id"):
                    # 防止不同文件互相覆盖：
                    # 如果新导入数据中该字段为0/null，且旧数据有非零值，保留旧值
                    # 这样社保文件和公积金文件可以分别导入而不互相清零
                    if key in numeric_fields:
                        old_val = getattr(existing, key, None)
                        new_is_zero = (value is None or value == 0)
                        old_is_nonzero = (old_val is not None and old_val != 0)
                        if new_is_zero and old_is_nonzero:
                            continue
                    setattr(existing, key, value)
            # 自动计算合计字段
            _calc_summaries(existing)
            updated += 1
        else:
            si = SocialInsurance(**si_data)
            db.add(si)
            # 新增记录不调用 _calc_summaries，因为 flush 后才能访问属性
            # 合计将在 db.commit() 前统一处理
            created += 1

    db.commit()

    # 对新创建的记录（刚才commit后才有id），也自动计算合计
    # 直接查所有本次period的员工记录，统一重算合计
    all_records = db.query(SocialInsurance).filter(
        SocialInsurance.period == period
    ).all()
    for rec in all_records:
        _calc_summaries(rec)

    db.commit()
    return created, updated


def run_smart_import(
    db: Session,
    period: str,
    files: List,
    user_id: int,
    username: str,
) -> ImportResult:
    """
    智能导入主流程：
    1. 逐个解析文件（Excel/PDF）
    2. 匹配模板并提取字段
    3. 按姓名聚合多文件数据
    4. 姓名匹配员工
    5. 数据校验
    6. 保存入库
    """
    result = ImportResult()
    batch_id = str(uuid.uuid4())
    all_records: List[Dict] = []
    logs: List[Dict] = []

    result.total_files = len(files)

    # ── 第1步：文件解析与字段提取 ──
    for file in files:
        filename = file.filename or "unknown"
        try:
            file_bytes = file.file.read()
            file.file.seek(0)

            ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

            if ext in ("xlsx", "xls"):
                file_rows = _parse_excel(file_bytes, filename)
            elif ext == "pdf":
                file_rows = _parse_pdf(file_bytes)
            else:
                logs.append({
                    "file_name": filename,
                    "error_level": "error",
                    "error_type": "unsupported_format",
                    "error_message": f"不支持的文件格式「.{ext}」，仅支持 Excel(.xlsx/.xls) 和 PDF(.pdf)",
                })
                result.failed_files += 1
                continue

            if not file_rows or len(file_rows) < 2:
                logs.append({
                    "file_name": filename,
                    "error_level": "error",
                    "error_type": "empty_file",
                    "error_message": "文件为空或数据行数不足",
                })
                result.failed_files += 1
                continue

            # 匹配模板（优先已有模板，否则 AI 实时识别并自动保存）
            template = _match_template(db, file_rows, filename)

            if not template:
                # 模板匹配失败 → AI 实时分析文件结构，并自动保存为正式模板
                detected_config = None
                template_source = "unknown"
                try:
                    from app.core.ai_service import is_available as ai_available
                    if ai_available():
                        detected_config = auto_detect_template(file_bytes, filename)
                        template_source = "ai"
                        logger.info(f"AI 实时识别成功: {filename} → {detected_config.get('name', '')}")
                    else:
                        raise Exception("AI 服务不可用")
                except Exception as ai_err:
                    logger.warning(f"AI 实时识别失败: {filename}, 错误: {ai_err}")
                    # AI 不可用，降级为规则匹配
                    try:
                        detected_config = auto_detect_template(file_bytes, filename)
                        template_source = "fallback"
                    except Exception as fallback_err:
                        logger.exception(f"规则降级也失败: {filename}")
                        logs.append({
                            "file_name": filename,
                            "error_level": "error",
                            "error_type": "unknown_format",
                            "error_message": f"无法识别文件格式（AI和规则降级均失败），请在「导入模板配置」中手动添加解析模板",
                        })
                        result.failed_files += 1
                        continue

                # 构造模板对象（用于本次导入）
                template = SiImportTemplate(
                    name=detected_config.get("name", f"自动识别-{filename[:20]}"),
                    source_category=detected_config.get("source_category", "social_insurance"),
                    file_type=detected_config.get("file_type", "excel"),
                    city=detected_config.get("city"),
                    description=f"{'AI' if template_source == 'ai' else '规则降级'}实时识别: {filename[:50]}",
                    file_pattern=detected_config.get("file_pattern", ""),
                    header_rows=detected_config.get("header_rows", []),
                    data_start_row=detected_config.get("data_start_row", 0),
                    skip_footer_rows=detected_config.get("skip_footer_rows", 0),
                    column_mappings=detected_config.get("column_mappings", {}),
                    row_filters=detected_config.get("row_filters"),
                    number_format=detected_config.get("number_format", {}),
                    is_active=True,
                )

                # 自动保存为正式模板（下次遇到相同格式文件就能直接匹配，无需再调AI）
                try:
                    # 检查是否已有同名模板，避免重复
                    existing_tpl = db.query(SiImportTemplate).filter(
                        SiImportTemplate.file_pattern == detected_config.get("file_pattern", "")
                    ).first()
                    if not existing_tpl:
                        db.add(template)
                        db.commit()
                        db.refresh(template)
                        logger.info(f"AI/规则识别结果已自动保存为模板: {template.name} (id={template.id})")
                except Exception as save_err:
                    logger.warning(f"自动保存模板失败: {save_err}（不影响本次导入）")
                    db.rollback()

                # 日志
                level = "info" if template_source == "ai" else "warning"
                log_type = "ai_detected" if template_source == "ai" else "fallback_detected"
                logs.append({
                    "file_name": filename,
                    "error_level": level,
                    "error_type": log_type,
                    "error_message": (
                        f"{'AI' if template_source == 'ai' else '规则降级'}自动识别了文件格式"
                        f"（{detected_config.get('city', '未知城市')}"
                        f"{'社保' if detected_config.get('source_category') == 'social_insurance' else '公积金'}），"
                        f"已自动保存为模板「{template.name}」，下次可直接使用"
                    ),
                })

            # 提取数据
            records = _extract_data(file_rows, template, filename, period, logs, batch_id)

            # 险种字段智能解析：根据文件名将通用字段映射到指定险种字段
            # 例如："2026-06——工伤保险（单位缴纳部分）职工明细.xlsx"
            #   → amount 映射为 injury_company，si_base 映射为 injury_company_base
            records = _resolve_insurance_fields(records, filename)

            all_records.extend(records)
            result.parsed_files += 1

        except Exception as e:
            logger.exception(f"解析文件失败: {filename}")
            logs.append({
                "file_name": filename,
                "error_level": "error",
                "error_type": "file_error",
                "error_message": f"文件解析失败：{str(e)}",
            })
            result.failed_files += 1

    result.total_rows = len(all_records)

    if not all_records:
        result.errors = logs
        _save_logs(db, logs, period, batch_id)
        return result

    # ── 第2步：按姓名聚合 ──
    aggregated = _aggregate_by_name(all_records)

    # ── 第3步：姓名匹配员工 ──
    valid_data, skipped = _match_employees(db, aggregated, logs, batch_id)

    # ── 第4步：数据校验 ──
    _validate_data(valid_data, logs, batch_id)

    # ── 第5步：保存 ──
    created, updated = _save_records(db, period, valid_data, user_id, username, logs, batch_id)
    result.created = created
    result.updated = updated

    # ── 第6步：分类日志 ──
    for log_entry in logs:
        if log_entry.get("error_level") == "error":
            result.errors.append(log_entry)
        else:
            result.warnings.append(log_entry)

    _save_logs(db, logs, period, batch_id)

    return result


def _save_logs(db: Session, logs: List[Dict], period: str, batch_id: str):
    """将导入日志写入数据库"""
    for log_entry in logs:
        db_log = SiImportLog(
            period=period,
            batch_id=batch_id,
            file_name=log_entry.get("file_name"),
            row_number=log_entry.get("row_number"),
            employee_name=log_entry.get("employee_name"),
            error_level=log_entry.get("error_level", "warning"),
            error_type=log_entry.get("error_type", "unknown"),
            error_message=log_entry.get("error_message", ""),
        )
        db.add(db_log)
    db.commit()


# ── 模板自动识别（AI 驱动）───────────────────────────────────────────

def _format_rows_for_ai(file_rows: List[List], max_rows: int = 40) -> str:
    """将文件前 N 行格式化为 AI 可读的文本"""
    lines = []
    for i, row in enumerate(file_rows[:max_rows]):
        cells = []
        for j, cell in enumerate(row):
            val = str(cell).strip() if cell is not None else ""
            if val:
                cells.append(f"  [{j}] {val}")
        if cells:
            lines.append(f"第{i}行:\n" + "\n".join(cells))
        else:
            lines.append(f"第{i}行: (空行)")
    return "\n\n".join(lines)


def _build_ai_prompt(file_rows_text: str, filename: str, field_labels: Dict[str, str]) -> str:
    """构建 AI 识别的提示词"""
    fields_desc = "\n".join(f"- {key}: {label}" for key, label in field_labels.items())
    return f"""请分析以下社保/公积金文件的内容（文件名：{filename}），完成以下任务：

1. **识别表头行号**：找出哪些行是列名表头（0-based 行号）。注意：
   - 元数据行（如操作员、单位名称、统一社会信用代码、经办网点、制表人、"职工明细"标题等）不是表头
   - 表头可以是单层或多层（例如第2行是父标题"养老保险"，第3行是子标题"单位缴纳基数"）
   - 如果有双层表头，返回多行行号

2. **确定数据起始行**（0-based）：表头之后第一行实际数据的行号

3. **跳过末尾行数**：文件末尾的非数据行（如合计行、盖章行等）的数量

4. **列字段映射**：将表头每个非空列名，对应到下面的系统字段。如果无法对应，映射值设为 null。
   **重要**：如果是多层表头（如"养老保险"下分"缴费基数"和"应缴金额"），列名必须使用完整路径格式：
   - 单层表头：直接用列名，如 "姓名"、"个人社保号"
   - 双层表头：用 "一级 - 二级" 格式，如 "基本养老保险(单位缴纳) - 缴费基数"、"基本养老保险(单位缴纳) - 应缴金额"
   
   **文件名推断险种**：仔细分析文件名，从中推断险种类型和缴纳方：
   - 文件名含"养老"则属于养老保险，含"失业"则属于失业保险，含"医疗"则属于医疗保险，含"工伤"则属于工伤保险
   - 文件名含"单位"则为单位缴纳，含"个人"则为个人缴纳
   - 根据推断结果，将"缴费工资"/"缴费基数"映射到对应险种基数（如 pension_company_base、medical_personal_base）
   - 将"应缴费额(元)"/"应缴金额"映射到对应险种金额（如 pension_company、unemployment_personal）
   - 将"费率"映射到对应险种比例（如 medical_company_rate、injury_company_rate）
   - 示例：文件名含"养老保险（单位缴纳部分）" → "缴费基数"→pension_company_base，"应缴费额(元)"→pension_company，"费率"→pension_company_rate
   - 如果文件名不包含险种和缴纳方信息，就使用通用字段（如 si_base、amount）
   
   系统字段列表：
{fields_desc}

5. **数据类别**：判断是 "social_insurance"（社保）还是 "housing_fund"（公积金）

6. **城市**：如果能从内容或文件名判断城市（如广州、邯郸、深圳等），返回城市名，否则 null

7. **行过滤条件**：如果表头中有"缴存状态"或"状态"列，且大部分数据行的值都是某种状态（如"正常"），返回过滤条件，格式为 {{"列名": "正常"}}，否则返回 null

文件内容：
{file_rows_text}

请返回严格的 JSON 格式，不要包含任何其他文字。格式如下：
{{
  "header_rows": [行号数组],
  "data_start_row": 数字,
  "skip_footer_rows": 数字,
  "column_mappings": {{"列名（多层用' - '连接）": "系统字段名或null", ...}},
  "source_category": "social_insurance 或 housing_fund",
  "city": "城市名或null",
  "row_filters": {{"列名": "过滤值"}} 或 null
}}"""


def _detect_city(text: str, filename: str) -> Optional[str]:
    """简单规则检测城市（AI 返回 null 时的降级方案）"""
    city_keywords = {"广州": "广州", "邯郸": "邯郸", "深圳": "深圳", "北京": "北京", "上海": "上海"}
    for kw, city_name in city_keywords.items():
        if kw in text or kw in filename:
            return city_name
    return None


def _detect_insurance_type_from_filename(filename: str) -> Optional[Dict[str, str]]:
    """从文件名推断险种类型和缴纳方。
    返回如：{"insurance": "pension", "payer": "company"} 或 None
    
    支持的关键词：
    - 险种：养老/pension, 失业/unemployment, 医疗/medical, 工伤/injury
    - 缴纳方：单位/company, 个人/personal
    """
    fn = filename.lower()
    result = {}
    
    # 险种检测
    insurance_map = {
        "养老": "pension",
        "失业": "unemployment",
        "医疗": "medical",
        "工伤": "injury",
    }
    for keyword, field_prefix in insurance_map.items():
        if keyword in fn:
            result["insurance"] = field_prefix
            break
    
    # 缴纳方检测
    payer_map = {
        "单位": "company",
        "个人": "personal",
    }
    for keyword, field_suffix in payer_map.items():
        if keyword in fn:
            result["payer"] = field_suffix
            break
    
    return result if result else None


def _resolve_insurance_fields(records: List[Dict], filename: str) -> List[Dict]:
    """根据文件名将通用字段映射到指定的险种字段。
    
    处理场景：邯郸社保分险种文件，每个文件格式相同但属于不同险种。
    文件名如"城镇企业职工基本养老保险（单位缴纳部分）职工明细.xlsx"
    
    通用字段 → 特定字段的映射规则：
    - amount → {insurance}_{payer}（如 pension_company）
    - amount_base → {insurance}_{payer}_base
    - amount_rate → {insurance}_{payer}_rate
    """
    info = _detect_insurance_type_from_filename(filename)
    if not info:
        return records
    
    insurance = info.get("insurance")
    payer = info.get("payer")
    if not insurance or not payer:
        return records
    
    target_amount = f"{insurance}_{payer}"
    target_base = f"{insurance}_{payer}_base"
    target_rate = f"{insurance}_{payer}_rate"
    
    for rec in records:
        # 将通用字段转移为特定字段
        amount = rec.pop("amount", None) or rec.pop("_amount", None)
        base = rec.pop("si_base", None) or rec.pop("_si_base", None)
        rate = rec.pop("rate", None) or rec.pop("_rate", None)
        
        if amount is not None and amount != "" and amount != 0:
            rec[target_amount] = amount
        if base is not None and base != "" and base != 0:
            rec[target_base] = base
        if rate is not None and rate != "" and rate != 0:
            rec[target_rate] = rate
    
    return records


# ── 规则降级函数（AI 不可用时）─────────────────────────────────────

# 精简关键词（金额/合计类优先，避免误匹配）
_FALLBACK_KEYWORDS = {
    "employee_name": ["姓名"],
    "employee_social_insurance_no": ["个人社保号", "社保号", "个人账号"],
    "si_base": ["社保缴存基数", "社保基数", "缴费工资", "缴费基数"],
    "amount": ["应缴费额", "应缴金额", "缴费额", "缴纳金额"],
    "rate": ["费率", "缴存比例", "缴费比例"],
    "si_personal": ["个人部分合计", "个人合计", "社保个人合计"],
    "si_company": ["单位部分合计", "单位合计", "社保单位合计"],
    "si_grand_total": ["应缴金额合计", "社保总合计"],
    "grand_total": ["社保公积金总合计", "总合计"],
    "hf_total": ["公积金合计", "公积金总合计", "汇缴总额", "发生额（元）", "发生额"],
    "hf_base": ["公积金缴存基数", "公积金基数", "缴存基数"],
    "hf_personal": ["公积金个人", "个人缴存额", "公积金个人金额"],
    "hf_company": ["公积金单位", "单位缴存额", "公积金单位金额"],
    "hf_personal_rate": ["个人缴存比例", "公积金个人比例", "缴存比例"],
    "hf_company_rate": ["单位缴存比例", "公积金单位比例"],
    # 险种分项（需指定类别+单位/个人+基数/金额/比例才能匹配）
    "pension_company_base": ["养老保险", "单位", "基数"],
    "pension_company": ["养老保险", "单位", "金额"],
    "pension_personal_base": ["养老保险", "个人", "基数"],
    "pension_personal": ["养老保险", "个人", "金额"],
    "unemployment_company_base": ["失业保险", "单位", "基数"],
    "unemployment_company": ["失业保险", "单位", "金额"],
    "unemployment_personal_base": ["失业保险", "个人", "基数"],
    "unemployment_personal": ["失业保险", "个人", "金额"],
    "medical_company_base": ["医疗保险", "生育", "单位", "基数"],
    "medical_company": ["医疗保险", "生育", "单位", "金额"],
    "medical_personal_base": ["医疗保险", "生育", "个人", "基数"],
    "medical_personal": ["医疗保险", "生育", "个人", "金额"],
    "injury_company_base": ["工伤保险", "基数"],
    "injury_company": ["工伤保险", "金额"],
    "pension_personal_rate": ["养老保险", "个人", "比例"],
    "pension_company_rate": ["养老保险", "单位", "比例"],
    "unemployment_personal_rate": ["失业保险", "个人", "比例"],
    "unemployment_company_rate": ["失业保险", "单位", "比例"],
    "medical_personal_rate": ["医疗保险", "个人", "比例"],
    "medical_company_rate": ["医疗保险", "单位", "比例"],
    "injury_company_rate": ["工伤保险", "比例"],
    "period": ["缴存年月", "缴费月份", "费款所属期", "月份"],
}

_META_CELL_KEYWORDS = [
    "操作员", "单位账号", "单位名称", "统一社会信用代码",
    "社保管理机构", "税务管理机关", "单位社保号", "经办网点",
    "经办人", "制表人", "打印日期", "单位：元",
]

# 标题行关键词（整行文本包含这些词时跳过，如"社会保险费申报个人明细表"）
_TITLE_ROW_KEYWORDS = ["明细表", "申报表", "汇总表", "社会保险"]

_FOOTER_KEYWORDS = ["合计", "总计", "盖章", "制表", "打印日期", "经办人", "操作员", "单位：元"]

# 表头行识别关键词（强标识，用于判断某行是否是表头，比列匹配关键词更严格）
_HEADER_ROW_KEYWORDS = ["姓名", "序号", "证件号码", "个人社保号", "个人账号", "证件类型"]


def _fallback_detect_header(file_rows: List[List]) -> tuple:
    """规则检测表头行、数据起始行、末尾跳过行"""
    total_rows = len(file_rows)

    # 找候选表头行：非空列 ≥ 2，不含元数据关键词
    candidates = []
    for i, row in enumerate(file_rows[:min(30, total_rows)]):
        non_empty = [c for c in row if c and str(c).strip()]
        if len(non_empty) < 2:
            continue

        # 排除标题行（合并单元格导致的整行相同值）
        non_empty_vals = [str(c).strip() for c in row if c and str(c).strip()]
        if non_empty_vals and len(set(non_empty_vals)) == 1:
            # 整行所有非空单元格值都相同 → 典型的合并单元格标题行
            continue

        # 排除元数据行（但不要误杀包含列头关键词的行）
        row_text = " ".join(str(c) for c in row if c)
        # 先检查是否是表头行（优先级最高）
        has_col_header_kw = any(
            any(kw in str(c) for kw in _HEADER_ROW_KEYWORDS)
            for c in row if c
        )
        # 如果包含"姓名"等明确列头关键词，直接认定是表头行，不执行后续排除逻辑
        if has_col_header_kw:
            candidates.append(i)
            continue
        # 否则按元数据排除
        if any(kw in row_text for kw in ["费款所属期"]):
            continue
        if any(kw in row_text for kw in _TITLE_ROW_KEYWORDS):
            continue
        if all(
            any(kw in str(c) for kw in _META_CELL_KEYWORDS)
            for c in row if c and str(c).strip()
        ):
            continue

    if not candidates:
        # 降级：取第一个非空行数 ≥ 3 的行（优先找包含"序号"或"姓名"的）
        for i, row in enumerate(file_rows[:min(20, total_rows)]):
            if not row:
                continue
            non_empty_count = sum(1 for c in row if c and str(c).strip())
            if non_empty_count < 3:
                continue
            # 检查是否包含典型的列头关键词
            row_text = " ".join(str(c) for c in row if c)
            if any(kw in row_text for kw in _HEADER_ROW_KEYWORDS):
                candidates = [i]
                break
        if not candidates:
            # 最后的最后：取第一个超过5个非空列的行
            for i, row in enumerate(file_rows[:min(15, total_rows)]):
                if row and sum(1 for c in row if c and str(c).strip()) >= 5:
                    candidates = [i]
                    break

    if not candidates:
        candidates = [0]

    header_rows = candidates[:1]  # 取第一个候选行
    # 检查下一行是否也是表头（双层表头）
    next_row = candidates[0] + 1
    if next_row < total_rows:
        next_non_empty = [c for c in file_rows[next_row] if c and str(c).strip()]
        has_header = any(
            any(kw in str(c) for kw in ["缴费", "缴存", "基数", "金额", "比例", "单位", "个人"])
            for c in next_non_empty
        ) if next_non_empty else False
        if has_header and len(next_non_empty) >= len([c for c in file_rows[candidates[0]] if c and str(c).strip()]):
            header_rows = [candidates[0], next_row]  # 双层表头

    data_start_row = max(header_rows) + 1
    while data_start_row < total_rows and not any(
        str(c).replace(",", "").replace(".", "").replace("-", "").replace("%", "").strip().isdigit()
        for c in file_rows[data_start_row] if c
    ):
        data_start_row += 1

    skip_footer_rows = 0
    for i in range(total_rows - 1, data_start_row, -1):
        row_text = " ".join(str(c) for c in file_rows[i] if c)
        if any(kw in row_text for kw in _FOOTER_KEYWORDS):
            skip_footer_rows += 1
        else:
            break

    return header_rows, data_start_row, skip_footer_rows


def _fallback_match_columns(file_rows: List[List], header_rows: List[int]) -> Dict[str, Optional[str]]:
    """规则匹配列映射，返回所有列（未匹配的为 None），支持双层表头拼接"""
    # 合并多层表头为一行，用 " - " 分隔
    max_cols = max(len(file_rows[hr]) if hr < len(file_rows) else 0 for hr in header_rows)
    merged_header = []
    for col_idx in range(max_cols):
        parts = []
        for hr in header_rows:
            if hr < len(file_rows) and col_idx < len(file_rows[hr]):
                val = str(file_rows[hr][col_idx]).strip() if file_rows[hr][col_idx] else ""
                if val:
                    if not parts or val != parts[-1]:
                        parts.append(val)
        merged_header.append(" - ".join(parts) if len(parts) > 1 else (parts[0] if parts else ""))

    mappings = {}
    for col_name in merged_header:
        if not col_name:
            continue

        # 尝试匹配
        best_field = None
        best_score = 0
        for field, keywords in _FALLBACK_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in col_name)
            # 完全匹配加分，优先级高于子串匹配
            # 例如: "应缴金额合计" 完全匹配 si_grand_total 的关键词，
            #   而非 amount 的 "应缴金额" 子串匹配
            if any(kw == col_name for kw in keywords):
                score += 10
            if score > best_score:
                best_score = score
                best_field = field

        if best_score >= 1:
            mappings[col_name] = best_field
        else:
            mappings[col_name] = None

    return mappings


def _fallback_detect_meta(file_rows: List[List], filename: str) -> tuple:
    """规则检测数据类别和城市"""
    all_text = " ".join(
        str(c) for row in file_rows[:10] for c in row if c
    )

    has_housing = any(kw in all_text for kw in ["公积金", "缴存额", "缴存比例", "公积金账号", "缴存名单", "汇缴", "缴存年月"])
    has_social = any(kw in all_text for kw in ["养老保险", "医疗保险", "失业保险", "工伤保险", "社保", "社会保险"])
    if has_housing and not has_social:
        source_category = "housing_fund"
    else:
        source_category = "social_insurance"

    city = None
    city_keywords = {"广州": "广州", "邯郸": "邯郸", "深圳": "深圳", "北京": "北京", "上海": "上海"}
    for kw, city_name in city_keywords.items():
        if kw in all_text or kw in filename:
            city = city_name
            break

    return source_category, city


def _fallback_detect_filters(
    file_rows: List[List], header_rows: List[int],
    data_start_row: int, skip_footer_rows: int, total_rows: int
) -> Optional[Dict]:
    """规则检测行过滤条件"""
    h = file_rows[header_rows[0]]
    for col_idx, cell in enumerate(h):
        text = str(cell).strip() if cell else ""
        if "缴存状态" in text or text == "状态":
            status_values = set()
            for r in range(data_start_row, min(data_start_row + 5, total_rows - skip_footer_rows)):
                if r < len(file_rows) and col_idx < len(file_rows[r]):
                    val = str(file_rows[r][col_idx]).strip() if file_rows[r][col_idx] else ""
                    if val:
                        status_values.add(val)
            if "正常" in status_values and len(status_values) >= 2:
                return {text: "正常"}
            break
    return None


# ── AI 驱动的主函数 ─────────────────────────────────────────────


def auto_detect_template(file_bytes: bytes, filename: str) -> Dict:
    """
    自动识别文件结构（AI 驱动）。
    将文件原始内容交给 AI 分析，一次返回表头行号、数据起始行、列映射等全部配置。
    """
    # 1. 解析文件
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext in ("xlsx", "xls"):
        file_rows = _parse_excel(file_bytes, filename)
        file_type = "excel"
    elif ext == "pdf":
        file_rows = _parse_pdf(file_bytes)
        file_type = "pdf"
    else:
        raise ValueError(f"不支持的文件格式「.{ext}」")

    if not file_rows or len(file_rows) < 2:
        raise ValueError("文件为空或数据行数不足")

    total_rows = len(file_rows)

    # 2. 格式化为 AI 可读文本
    rows_text = _format_rows_for_ai(file_rows, max_rows=40)

    # 3. 构建提示词并调用 AI（如果可用），否则用规则降级
    try:
        from app.core.ai_service import chat_json, is_available as ai_available
        if ai_available():
            system_prompt = "你是一位精通社保公积金报表的数据分析师。你只会返回 JSON，不会返回其他内容。"
            user_message = _build_ai_prompt(rows_text, filename, SI_FIELD_LABELS)
            ai_result = chat_json(system_prompt, user_message, temperature=0.1)
            use_ai = True
        else:
            use_ai = False
    except Exception:
        use_ai = False

    if use_ai:
        # ── AI 路径 ──
        header_rows = ai_result.get("header_rows", [])
        if not isinstance(header_rows, list) or not header_rows:
            raise ValueError("AI 未能识别表头行，请手动配置模板")

        data_start_row = ai_result.get("data_start_row", 0)
        if not isinstance(data_start_row, int) or data_start_row < 0:
            data_start_row = max(header_rows) + 1

        skip_footer_rows = ai_result.get("skip_footer_rows", 0)
        if not isinstance(skip_footer_rows, int):
            skip_footer_rows = 0

        column_mappings = ai_result.get("column_mappings", {})
        if not isinstance(column_mappings, dict):
            column_mappings = {}

        source_category = ai_result.get("source_category", "social_insurance")
        if source_category not in ("social_insurance", "housing_fund"):
            source_category = "social_insurance"

        city = ai_result.get("city")
        row_filters = ai_result.get("row_filters")
    else:
        # ── 规则降级路径（AI 不可用时）──
        header_rows, data_start_row, skip_footer_rows = _fallback_detect_header(file_rows)
        column_mappings = _fallback_match_columns(file_rows, header_rows)
        source_category, city = _fallback_detect_meta(file_rows, filename)
        row_filters = _fallback_detect_filters(file_rows, header_rows, data_start_row, skip_footer_rows, total_rows)

    # 确保所有映射值在 SI_FIELD_LABELS 中或为 None
    valid_fields = set(SI_FIELD_LABELS.keys())
    validated_mappings = {}
    for col_name, field_name in column_mappings.items():
        if field_name and field_name in valid_fields:
            validated_mappings[col_name] = field_name
        else:
            validated_mappings[col_name] = None

    # 验证 source_category
    if source_category not in ("social_insurance", "housing_fund"):
        source_category = "social_insurance"

    # 城市降级检测
    if not city or not isinstance(city, str):
        all_text = " ".join(
            str(c) for row in file_rows[:data_start_row + 2] for c in row if c
        )
        city = _detect_city(all_text, filename)

    # row_filters 格式验证
    if not isinstance(row_filters, dict) or not row_filters:
        row_filters = None

    # 5. 构建结果
    basename = filename.rsplit(".", 1)[0] if "." in filename else filename
    name = f"{city or '通用'}{'社保' if source_category == 'social_insurance' else '公积金'}-{basename[:20]}"

    return {
        "name": name,
        "source_category": source_category,
        "file_type": file_type,
        "city": city,
        "description": "AI 自动识别生成的模板",
        "file_pattern": re.escape(basename[:30]),
        "sheet_pattern": None,
        "header_rows": header_rows,
        "data_start_row": data_start_row,
        "skip_footer_rows": skip_footer_rows,
        "column_mappings": validated_mappings,
        "row_filters": row_filters,
        "number_format": {"remove_chars": [",", "，"], "decimal_separator": "."},
    }
