import re
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import LLM_API_KEY, LLM_API_URL, LLM_MODEL
from app.core.log_helper import write_log
from app.models.models import (
    SysUser, SysRole, SysUserRole, SysPermission, SysDictBase, SysLog,
    Employee, EmployeeSalary, AttendanceRecord, PerformanceScore,
    SocialInsurance, SalaryCalculation
)
from app.api.auth import get_current_user, UserInfo

router = APIRouter()

pending_confirmations: Dict[str, dict] = {}


class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []


class ChatResponse(BaseModel):
    reply: str
    requires_confirmation: bool = False
    confirmation_id: Optional[str] = None
    confirmation_detail: Optional[str] = None


class ConfirmationRequest(BaseModel):
    confirmation_id: str
    confirmed: bool


def has_ai_permission(user_id: int, db: Session) -> bool:
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if user and user.is_admin:
        return True
    user_roles = db.query(SysUserRole).filter(SysUserRole.user_id == user_id).all()
    role_ids = [ur.role_id for ur in user_roles]
    if not role_ids:
        return False
    perm = db.query(SysPermission).filter(
        SysPermission.role_id.in_(role_ids),
        SysPermission.module == "ai_assistant",
        SysPermission.action == "use"
    ).first()
    return perm is not None


def extract_employee_name(text: str) -> Optional[str]:
    patterns = [
        r'(?:查询|查看|搜索|找|员工|档案).{0,4}?([\u4e00-\u9fa5]{2,4})(?:的|这|那|信息|档案|薪资|工资|考勤|绩效|社保)?',
        r'(?:新增|添加|创建|录入|编辑|修改|删除|导入).{0,4}?([\u4e00-\u9fa5]{2,4})',
        r'([\u4e00-\u9fa5]{2,4})(?:的|这).{0,6}(?:信息|档案|薪资|工资|考勤|绩效|社保|公积金|员工)',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            name = m.group(1)
            if name not in ('所有', '全部', '本月', '这个', '什么', '哪个', '如何', '怎么', '系统', '模块', '功能'):
                return name
    return None


def detect_intent(text: str) -> dict:
    text_lower = text.lower().strip()

    intent_map = [
        (r'查询.*员工|查看.*员工|员工.*信息|员工.*档案|列出.*员工|所有.*员工|全部.*员工|多少.*员工|员工.*列表|员工.*数量|有.*几个.*员工|搜索.*员工', 'query_employee'),
        (r'查询.*薪资|查看.*薪资|薪资.*多少|工资.*多少|薪资.*明细|工资.*明细|本月.*薪资|本月.*工资|薪资.*计算|工资.*计算|薪资核算|薪酬', 'query_salary'),
        (r'查询.*考勤|查看.*考勤|考勤.*情况|考勤.*记录|出勤.*情况|出勤率|请假|迟到|早退|缺卡|考勤.*统计', 'query_attendance'),
        (r'查询.*绩效|查看.*绩效|绩效.*情况|绩效.*评分|绩效.*系数|绩效.*记录|绩效.*统计', 'query_performance'),
        (r'查询.*社保|查看.*社保|社保.*多少|公积金.*多少|社保.*明细|公积金.*明细|社保.*记录|社保公积金|五险一金', 'query_insurance'),
        (r'查询.*审批|查看.*审批|审批.*状态|审批.*记录|审批.*列表|审核.*状态', 'query_approval'),
        (r'新增.*员工|添加.*员工|录入.*员工|创建.*员工|导入.*员工', 'create_employee'),
        (r'编辑.*员工|修改.*员工|更新.*员工|变更.*员工', 'edit_employee'),
        (r'删除.*员工|移除.*员工', 'delete_employee'),
        (r'系统.*状态|系统.*信息|系统.*概况|系统.*概览|当前.*模块|模块.*列表|功能.*列表|数据.*统计', 'query_system'),
        (r'字典|数据字典|字典项|字典分类', 'query_dict'),
        (r'日志|操作日志|系统日志', 'query_log'),
        (r'你好|hello|hi|嗨|在吗|帮助|help|能做什么|你会什么|你是谁|介绍一下', 'greeting'),
    ]

    for pattern, intent in intent_map:
        if re.search(pattern, text_lower):
            return {'intent': intent, 'employee_name': extract_employee_name(text)}

    return {'intent': 'unknown', 'employee_name': extract_employee_name(text)}


def handle_query_employee(text: str, db: Session, user: UserInfo) -> str:
    name = extract_employee_name(text)
    if name:
        emp = db.query(Employee).filter(Employee.name.like(f'%{name}%')).first()
        if not emp:
            return f'未找到名为「{name}」的员工，请确认姓名是否正确。'
        dept = db.query(SysDictBase).filter(SysDictBase.id == emp.department_id).first()
        pos = db.query(SysDictBase).filter(SysDictBase.id == emp.position_id).first()
        status = db.query(SysDictBase).filter(SysDictBase.id == emp.status_id).first()
        company = db.query(SysDictBase).filter(SysDictBase.id == emp.contract_company_id).first()

        salary_info = db.query(EmployeeSalary).filter(
            EmployeeSalary.employee_id == emp.id
        ).order_by(EmployeeSalary.effective_date.desc()).first()

        lines = [
            f'📋 **{emp.name}** 的员工档案：',
            f'- 员工编号：{emp.employee_no}',
            f'- 性别：{emp.gender}',
            f'- 部门：{dept.name if dept else "未知"}',
            f'- 职位：{pos.name if pos else "未知"}',
            f'- 合同公司：{company.name if company else "未知"}',
            f'- 用工状态：{status.name if status else "未知"}',
            f'- 入职日期：{emp.entry_date}',
            f'- 手机号：{emp.phone or "未填写"}',
        ]
        if salary_info:
            lines.append(f'\n💰 薪资信息（{salary_info.effective_date}起）：')
            lines.append(f'- 基本工资：{float(salary_info.base_salary):,.2f} 元')
            lines.append(f'- 绩效标准：{float(salary_info.performance_standard):,.2f} 元')
            lines.append(f'- 各项补贴合计：{float(salary_info.meal_allowance or 0) + float(salary_info.transport_allowance or 0) + float(salary_info.communication_allowance or 0) + float(salary_info.computer_allowance or 0) + float(salary_info.housing_allowance or 0):,.2f} 元')
        return '\n'.join(lines)
    else:
        total = db.query(Employee).count()
        active_count = db.query(Employee).join(
            SysDictBase, Employee.status_id == SysDictBase.id
        ).filter(SysDictBase.code != 'resigned').count()
        return f'📊 当前系统共有 **{total}** 名员工，其中在职 **{active_count}** 人。\n\n💡 你可以对我说「查询员工 张三」来查看具体某人的档案信息。'


def handle_query_salary(text: str, db: Session, user: UserInfo) -> str:
    name = extract_employee_name(text)
    now = datetime.now()
    current_period = f'{now.year}-{now.month:02d}'

    if name:
        emp = db.query(Employee).filter(Employee.name.like(f'%{name}%')).first()
        if not emp:
            return f'未找到名为「{name}」的员工，请确认姓名是否正确。'
        calcs = db.query(SalaryCalculation).filter(
            SalaryCalculation.employee_id == emp.id
        ).order_by(SalaryCalculation.period.desc()).limit(3).all()
        if not calcs:
            return f'「{name}」暂无薪资核算记录。'
        lines = [f'💰 **{name}** 的薪资记录（最近3条）：']
        for c in calcs:
            lines.append(
                f'\n📅 {c.period}：'
                f'应发 {float(c.gross_salary):,.2f} 元，'
                f'实发 {float(c.net_salary):,.2f} 元，'
                f'状态：{c.review_status}'
            )
        return '\n'.join(lines)
    else:
        total = db.query(SalaryCalculation).filter(
            SalaryCalculation.period == current_period
        ).count()
        draft = db.query(SalaryCalculation).filter(
            SalaryCalculation.period == current_period,
            SalaryCalculation.calculation_status == '草稿'
        ).count()
        reviewed = db.query(SalaryCalculation).filter(
            SalaryCalculation.period == current_period,
            SalaryCalculation.review_status == '已通过'
        ).count()
        return (
            f'📊 **{current_period}** 薪资核算概况：\n'
            f'- 总记录数：{total}\n'
            f'- 草稿状态：{draft}\n'
            f'- 已审核通过：{reviewed}\n\n'
            f'💡 你可以对我说「查询员工 张三的薪资」来查看具体某人的薪资明细。'
        )


def handle_query_attendance(text: str, db: Session, user: UserInfo) -> str:
    name = extract_employee_name(text)
    now = datetime.now()
    current_period = f'{now.year}-{now.month:02d}'

    if name:
        emp = db.query(Employee).filter(Employee.name.like(f'%{name}%')).first()
        if not emp:
            return f'未找到名为「{name}」的员工，请确认姓名是否正确。'
        records = db.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == emp.id
        ).order_by(AttendanceRecord.period.desc()).limit(3).all()
        if not records:
            return f'「{name}」暂无考勤记录。'
        lines = [f'📅 **{name}** 的考勤记录（最近3条）：']
        for r in records:
            lines.append(
                f'\n📌 {r.period}：'
                f'应出勤 {float(r.total_work_days)}天，'
                f'实际出勤 {float(r.actual_work_days)}天，'
                f'出勤率 {float(r.attendance_rate)*100:.1f}%，'
                f'迟到 {r.late_count}次，早退 {r.early_count}次'
            )
        return '\n'.join(lines)
    else:
        records = db.query(AttendanceRecord).filter(
            AttendanceRecord.period == current_period
        ).all()
        if not records:
            return f'📊 {current_period} 暂无考勤记录。'
        avg_rate = sum(float(r.attendance_rate) for r in records) / len(records)
        return (
            f'📊 **{current_period}** 考勤概况：\n'
            f'- 记录数：{len(records)}\n'
            f'- 平均出勤率：{avg_rate*100:.1f}%\n\n'
            f'💡 你可以对我说「查询员工 张三的考勤」来查看具体某人的考勤详情。'
        )


def handle_query_performance(text: str, db: Session, user: UserInfo) -> str:
    name = extract_employee_name(text)
    now = datetime.now()
    current_period = f'{now.year}-{now.month:02d}'

    if name:
        emp = db.query(Employee).filter(Employee.name.like(f'%{name}%')).first()
        if not emp:
            return f'未找到名为「{name}」的员工，请确认姓名是否正确。'
        scores = db.query(PerformanceScore).filter(
            PerformanceScore.employee_id == emp.id
        ).order_by(PerformanceScore.period.desc()).limit(3).all()
        if not scores:
            return f'「{name}」暂无绩效记录。'
        lines = [f'📈 **{name}** 的绩效记录（最近3条）：']
        for s in scores:
            lines.append(
                f'\n📌 {s.period}：'
                f'初评 {float(s.initial_score) if s.initial_score else "未评"}分，'
                f'终评 {float(s.final_score) if s.final_score else "未评"}分，'
                f'系数 {float(s.coefficient):.2f}'
            )
        return '\n'.join(lines)
    else:
        scores = db.query(PerformanceScore).filter(
            PerformanceScore.period == current_period
        ).all()
        if not scores:
            return f'📊 {current_period} 暂无绩效记录。'
        scored = [s for s in scores if s.final_score is not None]
        return (
            f'📊 **{current_period}** 绩效概况：\n'
            f'- 总记录数：{len(scores)}\n'
            f'- 已完成评分：{len(scored)}\n'
            f'- 待评分：{len(scores) - len(scored)}\n\n'
            f'💡 你可以对我说「查询员工 张三的绩效」来查看具体某人的绩效详情。'
        )


def handle_query_insurance(text: str, db: Session, user: UserInfo) -> str:
    name = extract_employee_name(text)
    now = datetime.now()
    current_period = f'{now.year}-{now.month:02d}'

    if name:
        emp = db.query(Employee).filter(Employee.name.like(f'%{name}%')).first()
        if not emp:
            return f'未找到名为「{name}」的员工，请确认姓名是否正确。'
        records = db.query(SocialInsurance).filter(
            SocialInsurance.employee_id == emp.id
        ).order_by(SocialInsurance.period.desc()).limit(3).all()
        if not records:
            return f'「{name}」暂无社保公积金记录。'
        lines = [f'🏦 **{name}** 的社保公积金记录（最近3条）：']
        for r in records:
            lines.append(
                f'\n📌 {r.period}：'
                f'社保基数 {float(r.si_base):,.2f}，'
                f'个人缴纳 {float(r.si_personal):,.2f}，'
                f'公积金基数 {float(r.hf_base):,.2f}，'
                f'个人缴纳 {float(r.hf_personal):,.2f}'
            )
        return '\n'.join(lines)
    else:
        records = db.query(SocialInsurance).filter(
            SocialInsurance.period == current_period
        ).all()
        if not records:
            return f'📊 {current_period} 暂无社保公积金记录。'
        return (
            f'📊 **{current_period}** 社保公积金概况：\n'
            f'- 记录数：{len(records)}\n\n'
            f'💡 你可以对我说「查询员工 张三的社保」来查看具体某人的社保详情。'
        )


def handle_query_system(text: str, db: Session, user: UserInfo) -> str:
    employee_count = db.query(Employee).count()
    user_count = db.query(SysUser).count()
    role_count = db.query(SysRole).count()
    now = datetime.now()
    current_period = f'{now.year}-{now.month:02d}'
    salary_count = db.query(SalaryCalculation).filter(
        SalaryCalculation.period == current_period
    ).count()

    modules = [
        '📋 档案管理', '📅 考勤管理', '📈 绩效管理',
        '💰 薪资核算', '🏦 社保公积金', '✅ 审批流程',
        '📄 报表导出', '⚙️ 系统管理'
    ]

    return (
        f'🏢 **E9 Payroll** 概况：\n\n'
        f'📊 数据统计：\n'
        f'- 员工总数：{employee_count}\n'
        f'- 系统用户：{user_count}\n'
        f'- 角色数量：{role_count}\n'
        f'- 本月薪资记录：{salary_count}\n\n'
        f'📦 功能模块：\n' +
        '\n'.join(f'  {m}' for m in modules) +
        f'\n\n💡 你可以直接对我说：\n'
        f'  · 「查询员工 张三」- 查看档案\n'
        f'  · 「本月薪资概况」- 查看核算进度\n'
        f'  · 「考勤统计」- 查看出勤情况\n'
        f'  · 「系统状态」- 查看系统概况'
    )


def handle_greeting(text: str, db: Session, user: UserInfo) -> str:
    return (
        f'👋 你好，**{user.display_name}**！我是 E9 Payroll 的 AI 助手 🤖\n\n'
        f'我可以帮你快速完成以下操作：\n\n'
        f'🔍 **查询类**（直接执行）：\n'
        f'  · 「查询员工 张三」— 查看员工档案\n'
        f'  · 「本月薪资概况」— 查看薪资核算进度\n'
        f'  · 「考勤统计」— 查看出勤情况\n'
        f'  · 「绩效情况」— 查看绩效评分\n'
        f'  · 「社保公积金」— 查看社保明细\n'
        f'  · 「系统状态」— 查看系统概况\n\n'
        f'✏️ **录入类**（直接执行）：\n'
        f'  · 「新增员工 李四」— 录入新员工（需补充信息）\n\n'
        f'⚠️ **编辑类**（需二次确认）：\n'
        f'  · 「修改员工 张三的薪资」— 需要你确认后执行\n\n'
        f'💬 你想做什么？直接告诉我就好！'
    )


def handle_create_employee(text: str, db: Session, user: UserInfo) -> str:
    name = extract_employee_name(text)
    if not name:
        return (
            '请告诉我你要新增的员工姓名。例如：「新增员工 李四」。\n\n'
            '新增员工还需要以下信息：\n'
            '- 性别、身份证号\n'
            '- 部门、职位\n'
            '- 合同公司\n'
            '- 入职日期\n'
            '请在后续对话中补充这些信息。'
        )
    existing = db.query(Employee).filter(Employee.name == name).first()
    if existing:
        return f'系统中已存在名为「{name}」的员工（编号：{existing.employee_no}），请勿重复录入。如需修改信息，请说「修改员工 {name}」。'

    max_no = db.query(Employee).order_by(Employee.id.desc()).first()
    if max_no:
        try:
            last_num = int(max_no.employee_no[2:]) if len(max_no.employee_no) > 2 else 0
            new_no = f'E9{last_num + 1:04d}'
        except ValueError:
            new_no = f'E9{max_no.id + 1:04d}'
    else:
        new_no = 'E90001'

    return (
        f'✅ 好的，准备新增员工「**{name}**」！\n\n'
        f'系统将自动分配员工编号：`{new_no}`\n\n'
        f'⚠️ 但是我还缺少以下必要信息，请逐项补充：\n'
        f'  1. 性别（男/女）\n'
        f'  2. 身份证号（18位）\n'
        f'  3. 部门（如：技术部、人事部等）\n'
        f'  4. 职位（如：工程师、主管等）\n'
        f'  5. 合同公司（北京易玖/广州分公司/邯郸分公司/上海瑞方）\n'
        f'  6. 入职日期（如：2026-05-18）\n\n'
        f'💡 建议你到「档案管理」页面手动录入，那里有完整的表单校验。'
    )


def handle_query_approval(text: str, db: Session, user: UserInfo) -> str:
    now = datetime.now()
    current_period = f'{now.year}-{now.month:02d}'
    calcs = db.query(SalaryCalculation).filter(
        SalaryCalculation.period == current_period
    ).all()

    if not calcs:
        return f'📊 {current_period} 暂无审批记录。'

    pending = sum(1 for c in calcs if c.review_status == '待审核')
    passed = sum(1 for c in calcs if c.review_status == '已通过')
    rejected = sum(1 for c in calcs if c.review_status == '已驳回')

    return (
        f'📊 **{current_period}** 审批概况：\n'
        f'- 待审核：{pending}\n'
        f'- 已通过：{passed}\n'
        f'- 已驳回：{rejected}\n'
        f'- 总计：{len(calcs)}'
    )


def try_llm(message: str, history: List[dict], db: Session, user: UserInfo) -> str:
    if not LLM_API_KEY or not LLM_API_URL:
        return None

    try:
        import httpx

        system_prompt = (
            f'你是 E9 Payroll 的 AI 助手。当前用户是 {user.display_name}。\n'
            f'系统模块包括：档案管理、考勤管理、绩效管理、薪资核算、社保公积金、审批流程、报表导出、系统管理。\n'
            f'请用简洁、友好的方式回答用户关于系统使用的任何问题。回答使用中文。'
        )

        messages = [{'role': 'system', 'content': system_prompt}]
        for h in history[-10:]:
            messages.append({'role': h.get('role', 'user'), 'content': h.get('content', '')})
        messages.append({'role': 'user', 'content': message})

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f'{LLM_API_URL}/chat/completions',
                headers={
                    'Authorization': f'Bearer {LLM_API_KEY}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': LLM_MODEL,
                    'messages': messages,
                    'max_tokens': 800,
                    'temperature': 0.3,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data['choices'][0]['message']['content']
    except Exception:
        pass

    return None


INTENT_HANDLERS = {
    'query_employee': handle_query_employee,
    'query_salary': handle_query_salary,
    'query_attendance': handle_query_attendance,
    'query_performance': handle_query_performance,
    'query_insurance': handle_query_insurance,
    'query_approval': handle_query_approval,
    'query_system': handle_query_system,
    'create_employee': handle_create_employee,
    'greeting': handle_greeting,
}


@router.post('/chat', response_model=ChatResponse)
def ai_chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    if not has_ai_permission(current_user.id, db):
        raise HTTPException(status_code=403, detail='您没有使用AI助手的权限，请联系系统管理员开通')

    result = detect_intent(req.message)
    intent = result['intent']

    if intent in INTENT_HANDLERS:
        reply = INTENT_HANDLERS[intent](req.message, db, current_user)
    elif intent == 'edit_employee' or intent == 'delete_employee':
        name = result.get('employee_name', '')
        confirm_id = str(uuid.uuid4())[:8]
        pending_confirmations[confirm_id] = {
            'intent': intent,
            'message': req.message,
            'employee_name': name,
            'user_id': current_user.id,
            'created_at': datetime.now().isoformat(),
        }
        return ChatResponse(
            reply=(
                f'⚠️ **操作需确认**\n\n'
                f'你正在尝试 **{"编辑" if intent == "edit_employee" else "删除"}** 员工'
                + (f'「{name}」' if name else '') + '的信息。\n\n'
                f'这是一个修改操作，需要你二次确认后才能执行。\n\n'
                f'💡 建议操作：请到对应模块页面手动操作，表单更完善也更安全。\n\n'
                f'如果你想继续通过AI执行，请回复「确认」或「取消」。'
            ),
            requires_confirmation=True,
            confirmation_id=confirm_id,
            confirmation_detail=f'确认{"编辑" if intent == "edit_employee" else "删除"}员工信息',
        )
    else:
        reply = try_llm(req.message, req.history, db, current_user)
        if reply is None:
            reply = (
                f'🤔 抱歉，我没有完全理解你的意思。\n\n'
                f'你可以尝试这样说：\n'
                f'  · 「查询员工 张三」— 查看员工信息\n'
                f'  · 「本月薪资概况」— 查看薪资进度\n'
                f'  · 「考勤统计」— 查看考勤情况\n'
                f'  · 「系统状态」— 查看系统概况\n'
                f'  · 「你好」— 查看我能做什么\n\n'
                f'或者换一种说法再试试？'
            )

    write_log(
        db, 'ai_chat', current_user.id, current_user.username,
        'ai_assistant', 'chat',
        f'用户询问：{req.message[:100]} | 意图：{intent}',
    )
    return ChatResponse(reply=reply)


@router.post('/confirm', response_model=ChatResponse)
def ai_confirm(
    req: ConfirmationRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    if not has_ai_permission(current_user.id, db):
        raise HTTPException(status_code=403, detail='您没有使用AI助手的权限，请联系系统管理员开通')

    pending = pending_confirmations.get(req.confirmation_id)
    if not pending:
        return ChatResponse(reply='该确认请求已过期或不存在，请重新发起操作。')

    if pending['user_id'] != current_user.id:
        return ChatResponse(reply='该确认请求由其他用户发起，您无权确认此操作。')

    if req.confirmed:
        intent = pending['intent']
        name = pending.get('employee_name', '')
        del pending_confirmations[req.confirmation_id]

        if intent == 'edit_employee' and name:
            return ChatResponse(
                reply=(
                    f'✅ 确认通过！\n\n'
                    f'💡 但是，编辑员工「{name}」信息涉及多个字段（部门、职位、薪资等），'
                    f'建议你到「档案管理」页面直接操作，表单更完善。\n\n'
                    f'如果你只是想修改薪资，可以去「薪资核算」模块处理。'
                )
            )
        return ChatResponse(reply='✅ 确认通过！但由于安全限制，复杂的编辑操作请到对应功能页面手动完成。')
    else:
        del pending_confirmations[req.confirmation_id]
        return ChatResponse(reply='❌ 操作已取消。')


@router.get('/permission-status')
def check_permission_status(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    has_perm = has_ai_permission(current_user.id, db)
    return {
        'has_permission': has_perm,
        'is_admin': current_user.is_admin,
        'message': '您可以使用AI助手' if has_perm else '您没有AI助手的使用权限，请联系系统管理员',
    }