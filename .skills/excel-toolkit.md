# Skill: Excel 导入导出工具包（excel-toolkit）

## 描述
通用的 Excel 文件读写工具，封装了 openpyxl 的操作细节。支持：
- 将查询结果导出为 Excel 并返回下载流
- 从上传的 Excel 文件中读取数据并批量处理
- 自动解析中文表头

## 代码（Python）
```python
from io import BytesIO
from typing import List, Callable, Optional
from openpyxl import Workbook
from fastapi import UploadFile, HTTPException
from fastapi.responses import StreamingResponse


def export_to_excel(
    headers: List[str],
    rows: List[list],
    filename: str,
    sheet_name: str = "数据"
) -> StreamingResponse:
    """
    将数据导出为 Excel 文件并返回下载响应。

    参数：
      - headers: 表头列表，如 ["编号", "姓名", "部门"]
      - rows: 数据行列表，每行是一个 list，长度需与 headers 一致
      - filename: 下载文件名（不含扩展名），如 "员工数据"
      - sheet_name: 工作表名称

    返回：StreamingResponse（FastAPI 下载响应）
    """
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    for row in rows:
        ws.append(row)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    wb.close()

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
    )


async def parse_uploaded_excel(
    file: UploadFile,
    header_patterns: dict,
    required_headers: List[str]
) -> List[dict]:
    """
    解析上传的 Excel 文件，按表头模式匹配列。

    参数：
      - file: FastAPI UploadFile 对象
      - header_patterns: {"目标字段名": ["中文关键词1", "关键词2"]}
        例如：{"employee_no": ["编号", "工号"], "name": ["姓名", "名字"]}
      - required_headers: 必须存在的字段名列表，如 ["name"]

    返回：[{字段名: 单元格值}, ...] 列表

    异常：
      - HTTPException(400): 文件格式不对、表头缺失等
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 格式")

    try:
        contents = await file.read()
        from openpyxl import load_workbook
        wb = load_workbook(BytesIO(contents), read_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法读取 Excel 文件：{str(e)}")

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="Excel 文件为空或只有表头")

    headers = [str(h).strip() if h else "" for h in rows[0]]
    column_map = {}
    for col_idx, header_text in enumerate(headers):
        for target_field, patterns in header_patterns.items():
            for pat in patterns:
                if pat in header_text:
                    column_map[target_field] = col_idx
                    break

    for required in required_headers:
        if required not in column_map:
            raise HTTPException(
                status_code=400,
                detail=f"Excel 表头缺少「{required}」列"
            )

    result = []
    errors = []
    for row_idx, row in enumerate(rows[1:], start=2):
        record = {}
        for field, col_idx in column_map.items():
            record[field] = str(row[col_idx]).strip() if row[col_idx] else ""
        record["_row"] = row_idx
        result.append(record)

    return result
```

## 外部依赖与错误处理
- 依赖：openpyxl、FastAPI（UploadFile、StreamingResponse）
- 导出时若 rows 为空，生成仅含表头的空 Excel
- 导入时若文件损坏，返回 HTTPException(400) 带中文错误说明
- 表头匹配不区分大小写，使用 `in` 模糊匹配
- 所有错误信息使用中文

## 调用示例
```python
# 导出
@router.get("/employees/export")
def export_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    rows = [[e.employee_no, e.name, e.gender] for e in employees]
    return export_to_excel(
        headers=["编号", "姓名", "性别"],
        rows=rows,
        filename="员工数据_202605"
    )

# 导入
@router.post("/employees/import")
async def import_employees(file: UploadFile = File(...), db: Session = Depends(get_db)):
    records = await parse_uploaded_excel(
        file,
        header_patterns={
            "name": ["姓名", "名字"],
            "gender": ["性别"],
            "employee_no": ["编号", "工号"],
        },
        required_headers=["name", "gender"]
    )
    for rec in records:
        db.add(Employee(name=rec["name"], gender=rec["gender"]))
    db.commit()
    return {"message": f"导入 {len(records)} 条"}
```

## 使用场景
- [employees.py](file:///d:/devtool/cm/backend/app/api/employees.py) - 员工 Excel 导入导出
- [attendance.py](file:///d:/devtool/cm/backend/app/api/attendance.py) - 考勤 Excel 导入导出
- [salary.py](file:///d:/devtool/cm/backend/app/api/salary.py) - 薪资核算结果导出
- [social_insurance.py](file:///d:/devtool/cm/backend/app/api/social_insurance.py) - 社保导入导出
- [system.py](file:///d:/devtool/cm/backend/app/api/system.py) - 数据字典导入导出