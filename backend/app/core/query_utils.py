"""
查询工具函数
提供通用的数据库查询辅助函数
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import SysDictBase, Employee


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
