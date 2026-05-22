# Skill: 薪资核算核心公式（salary-formula）

## 描述
E9 薪资核算系统的核心计算逻辑。完全复现 Excel 手工核算中的计算规则，将分散的数据源（薪资档案、考勤、绩效、社保、调整项）合并计算为最终的薪资结果。

## 代码（Python）
```python
from decimal import Decimal

def safe_decimal(val, default=Decimal("0")) -> Decimal:
    """安全转换为 Decimal，避免 None 导致崩溃"""
    if val is None:
        return default
    return Decimal(str(val))


def calc_monthly_standard(base, perf_std, meal=0, transport=0,
                           comm=0, housing=0) -> Decimal:
    """月薪标准 = 基本工资 + 绩效奖金标准 + 固定补贴合计（不含电脑补贴，电脑补贴为非固定收入）"""
    return (
        safe_decimal(base) +
        safe_decimal(perf_std) +
        safe_decimal(meal) +
        safe_decimal(transport) +
        safe_decimal(comm) +
        safe_decimal(housing)
    )


def calc_allowance_total(meal=0, transport=0, comm=0, computer=0, housing=0) -> Decimal:
    """补贴合计"""
    return (
        safe_decimal(meal) +
        safe_decimal(transport) +
        safe_decimal(comm) +
        safe_decimal(computer) +
        safe_decimal(housing)
    )


def calc_actual_performance(perf_std, coefficient) -> Decimal:
    """实际绩效奖金 = 绩效奖金标准 × 绩效系数"""
    return safe_decimal(perf_std) * safe_decimal(coefficient)


def calc_gross_salary(base, allowance_total, actual_perf,
                      commission=0, pretax_adj=0, attendance_rate=1.0) -> Decimal:
    """
    总应发工资 = (基本工资 + 补贴合计 + 实际绩效奖金 + 提成奖金 + 税前调整) × 出勤率
    """
    subtotal = (
        safe_decimal(base) +
        safe_decimal(allowance_total) +
        safe_decimal(actual_perf) +
        safe_decimal(commission) +
        safe_decimal(pretax_adj)
    )
    return subtotal * safe_decimal(attendance_rate)


def calc_actual_taxable(gross_salary, last_month_untaxed=0,
                        travel_untaxed=0, compensation_tax=0) -> Decimal:
    """
    本月实际报税金额 = 总应发工资 + 上月未报税金额 + 临时差旅补贴未报税 + 补偿金报税
    """
    return (
        safe_decimal(gross_salary) +
        safe_decimal(last_month_untaxed) +
        safe_decimal(travel_untaxed) +
        safe_decimal(compensation_tax)
    )


def calc_si_personal(pension, unemployment, medical) -> Decimal:
    """社保个人缴纳合计 = 养老保险个人 + 失业保险个人 + 医疗保险个人"""
    return safe_decimal(pension) + safe_decimal(unemployment) + safe_decimal(medical)


def calc_si_hf_total(si_personal, hf_personal) -> Decimal:
    """社保公积金个人缴纳合计 = 社保个人合计 + 公积金个人"""
    return safe_decimal(si_personal) + safe_decimal(hf_personal)


def calc_net_salary(gross_salary, si_hf_total, tax_deduction, posttax_adj=0) -> Decimal:
    """
    实发工资 = 总应发工资 - 社保公积金个人合计 - 本月应扣个税 + 税后调整
    """
    return (
        safe_decimal(gross_salary) -
        safe_decimal(si_hf_total) -
        safe_decimal(tax_deduction) +
        safe_decimal(posttax_adj)
    )


def calc_attendance_rate(total_work_days, actual_work_days) -> Decimal:
    """出勤率 = 实际出勤天数 / 应出勤天数"""
    total = safe_decimal(total_work_days)
    if total == Decimal("0"):
        return Decimal("1.0")
    return safe_decimal(actual_work_days) / total


SALARY_FORMULA_DOCS = {
    "月薪标准": "基本工资 + 绩效奖金标准 + 固定补贴合计（餐补 + 交通补 + 通讯补 + 住房补），不含电脑补贴（非固定收入）",
    "实际绩效奖金": "绩效奖金标准 × 绩效系数",
    "总应发工资": "(基本工资 + 补贴合计 + 实际绩效奖金 + 提成/项目奖金/补发 + 税前调整金额) × 出勤率",
    "社保个人缴纳合计": "养老保险个人 + 失业保险个人 + 医疗保险个人",
    "社保公积金个人缴纳合计": "社保个人合计 + 公积金个人",
    "本月实际报税金额": "本月总应发工资 + 上月未报税金额 + 临时性差旅补贴未报税费用 + 补偿金报税",
    "实发工资": "总应发工资 - 社保公积金个人缴纳合计 - 本月应扣个税 + 税后调整金额",
    "出勤率": "实际出勤天数 / 应出勤天数",
    "补贴合计": "餐补 + 交通补 + 通讯补 + 电脑补 + 住房补",
}

VALIDATION_RULES = {
    "实发工资": "必须 >= 0，如果为负数提示「实发工资不能为负数，请检查各项数据是否正确」",
    "社保公积金合计": "社保公积金个人合计不能超过总应发工资",
    "税后调整原因": "当本月实际报税金额 < 总应发工资时，必须填写税后调整原因",
}
```

## 外部依赖与错误处理
- 依赖：Python 标准库 `decimal.Decimal`（精确货币计算，避免浮点误差）
- 所有输入使用 `safe_decimal()` 包裹，None 自动视为 0
- 出勤率分母为 0 时返回 1.0（避免除零崩溃）
- 所有金额计算使用 Decimal 而非 float（财务计算精度要求）
- `SALARY_FORMULA_DOCS` 字典可用于前端 tooltip 展示和 AI 助手解释

## 调用示例
```python
# 完整薪资核算流程
gross = calc_gross_salary(
    base=15000,
    allowance_total=calc_allowance_total(300, 200, 100, 200, 500),
    actual_perf=calc_actual_performance(3000, 1.0),
    commission=0,
    pretax_adj=0,
    attendance_rate=calc_attendance_rate(22, 22)
)
# gross = 15000 + 1300 + 3000 + 0 + 0 = 19300

net = calc_net_salary(
    gross_salary=gross,
    si_hf_total=calc_si_hf_total(1575, 1200),
    tax_deduction=500,
    posttax_adj=0
)
# net = 19300 - 2775 - 500 = 16025
```

## 使用场景
- [salary.py](file:///d:/devtool/cm/backend/app/api/salary.py) - 核心薪资核算 `calculate_salary()`
- [需求文档.md](file:///d:/devtool/cm/需求文档.md) 第 2.5 节 - 现有薪资计算公式定义
- 前端 [SalaryCalc.vue](file:///d:/devtool/cm/frontend/src/views/salary/SalaryCalc.vue) - 列 tooltip 说明