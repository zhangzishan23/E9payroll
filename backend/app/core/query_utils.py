"""
查询工具函数
提供通用的数据库查询辅助函数
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import SysDictBase, Employee, SysUser


def get_disabled_dept_ids(db: Session) -> list[int]:
    """
    获取所有已禁用部门的ID列表
    
    Args:
        db: 数据库会话
        
    Returns:
        已禁用部门的ID列表
    """
    result = db.query(SysDictBase.id).filter(
        SysDictBase.category == 'department',
        SysDictBase.is_enabled == False
    ).all()
    return [item[0] for item in result]


def get_pending_resign_status_id(db: Session) -> list[int]:
    """获取待离职状态对应的字典ID列表"""
    result = db.query(SysDictBase.id).filter(
        SysDictBase.category == 'employee_status',
        SysDictBase.name == '待离职'
    ).all()
    return [item[0] for item in result]


def get_user_employee_id(db: Session, user_id: int) -> Optional[int]:
    """
    获取系统用户关联的员工档案ID
    
    Args:
        db: 数据库会话
        user_id: 系统用户ID
        
    Returns:
        员工档案ID，如果未关联则返回None
    """
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if user and user.employee_id:
        return user.employee_id
    return None


def get_user_department_id(db: Session, user_id: int) -> Optional[int]:
    """
    获取用户所在部门ID（通过关联的员工档案）
    
    Args:
        db: 数据库会话
        user_id: 系统用户ID
        
    Returns:
        部门ID，如果未找到则返回None
    """
    employee_id = get_user_employee_id(db, user_id)
    if not employee_id:
        return None
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee:
        return employee.department_id
    return None


def apply_data_scope(
    query,
    db: Session,
    data_scope: str,
    user_id: int,
    employee_model=Employee,
    employee_id_field=None
):
    """
    根据数据范围权限过滤查询
    
    Args:
        query: SQLAlchemy查询对象
        db: 数据库会话
        data_scope: 数据范围 ("all", "dept", "self")
        user_id: 当前用户ID
        employee_model: 员工模型类，默认为Employee
        employee_id_field: 模型中关联员工ID的字段，用于非Employee模型的过滤
            (例如 Attendance模型用 employee_id，SalaryCalculation也用 employee_id)
            如果为None，则假设查询的就是Employee模型本身
            
    Returns:
        过滤后的查询对象
        
    Example:
        # 员工列表查询
        query = db.query(Employee)
        query = apply_data_scope(query, db, current_user.data_scope, current_user.id)
        employees = query.all()
        
        # 考勤记录查询 (Attendance模型有employee_id字段)
        query = db.query(Attendance)
        query = apply_data_scope(query, db, current_user.data_scope, current_user.id, employee_id_field=Attendance.employee_id)
        records = query.all()
    """
    if data_scope == "all":
        return query
    
    if data_scope == "self":
        emp_id = get_user_employee_id(db, user_id)
        if not emp_id:
            return query.filter(employee_model.id == -1)
        if employee_id_field is not None:
            return query.filter(employee_id_field == emp_id)
        else:
            return query.filter(employee_model.id == emp_id)
    
    if data_scope == "dept":
        dept_id = get_user_department_id(db, user_id)
        if not dept_id:
            return query.filter(employee_model.id == -1)
        if employee_id_field is not None:
            allowed_emp_ids = db.query(Employee.id).filter(Employee.department_id == dept_id).all()
            allowed_emp_ids = [e[0] for e in allowed_emp_ids]
            if not allowed_emp_ids:
                return query.filter(employee_id_field == -1)
            return query.filter(employee_id_field.in_(allowed_emp_ids))
        else:
            return query.filter(employee_model.department_id == dept_id)
    
    return query


def filter_active_employees(query, db: Session, employee_model=Employee, hide_status_id: Optional[int] = None):
    """
    过滤查询，排除已禁用部门的员工，可选隐藏指定状态的员工
    
    Args:
        query: SQLAlchemy查询对象
        db: 数据库会话
        employee_model: 员工模型类，默认为Employee
        hide_status_id: 要隐藏的员工状态ID，None表示不隐藏任何状态
        
    Returns:
        过滤后的查询对象
        
    Example:
        query = db.query(Employee)
        query = filter_active_employees(query, db)
        employees = query.all()
    """
    disabled_ids = get_disabled_dept_ids(db)
    if disabled_ids:
        query = query.filter(employee_model.department_id.notin_(disabled_ids))
    
    if hide_status_id:
        query = query.filter(employee_model.status_id != hide_status_id)
    return query


def filter_employees_by_dept_status(employees: list, db: Session) -> list:
    """
    过滤员工列表，排除已禁用部门的员工
    
    Args:
        employees: 员工列表
        db: 数据库会话
        
    Returns:
        过滤后的员工列表
        
    Example:
        employees = db.query(Employee).all()
        employees = filter_employees_by_dept_status(employees, db)
    """
    disabled_ids = set(get_disabled_dept_ids(db))
    if not disabled_ids:
        return employees
    return [emp for emp in employees if emp.department_id not in disabled_ids]
