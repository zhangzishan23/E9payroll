# Skill: 字典值解析（dict-resolver）

## 描述
将数据库中存储的字典 ID（如部门ID、职位ID、状态ID）批量转换为可读的中文名称。
这是整个系统使用频率最高的工具函数，所有需要展示数据的地方都会用到。

## 代码（Python）
```python
from sqlalchemy.orm import Session
from app.models.models import SysDictBase

def resolve_dict_names(db: Session, *dict_ids: int) -> dict:
    """
    批量解析字典ID为名称。
    参数：db（数据库会话）、*dict_ids（多个字典ID）
    返回：{id: name} 映射字典
    """
    if not dict_ids:
        return {}
    ids = [i for i in dict_ids if i is not None]
    if not ids:
        return {}
    items = db.query(SysDictBase).filter(SysDictBase.id.in_(ids)).all()
    return {d.id: d.name for d in items}


def enrich_with_dict_names(db: Session, obj, field_map: dict) -> dict:
    """
    给任意对象的字典字段附加中文名称。
    参数：
      - db: 数据库会话
      - obj: 包含 dict_id 字段的对象
      - field_map: {"属性名_dict_id字段": "附加的后缀名"}
    例如：{"department_id": "department_name", "position_id": "position_name"}
    返回：包含原始属性 + 名称属性的字典
    """
    result = {}
    id_fields = []
    for id_field in field_map:
        val = getattr(obj, id_field, None)
        result[id_field] = val
        if val:
            id_fields.append(val)

    name_map = resolve_dict_names(db, *id_fields)

    for id_field, name_suffix in field_map.items():
        val = getattr(obj, id_field, None)
        result[name_suffix] = name_map.get(val)

    return result
```

## 外部依赖与错误处理
- 依赖：SQLAlchemy Session、SysDictBase 模型
- 若传入空列表，返回空字典，不抛异常
- 若查不到对应字典项，名称字段为 None（不崩溃）
- 数据库连接异常由 SQLAlchemy 自行管理

## 调用示例
```python
# 解析单个员工的所有字典字段
name_map = resolve_dict_names(db, emp.department_id, emp.position_id, emp.status_id)
dept_name = name_map.get(emp.department_id)  # "技术部"

# 批量 enrich
data = enrich_with_dict_names(db, emp, {
    "department_id": "department_name",
    "position_id": "position_name",
    "status_id": "status_name",
    "contract_company_id": "contract_company_name",
})
```

## 使用场景
- [employees.py](file:///d:/devtool/cm/backend/app/api/employees.py) 的 `_enrich_employee` 函数
- [attendance.py](file:///d:/devtool/cm/backend/app/api/attendance.py) 的列表查询
- [salary.py](file:///d:/devtool/cm/backend/app/api/salary.py) 的核算结果展示
- [social_insurance.py](file:///d:/devtool/cm/backend/app/api/social_insurance.py) 列表查询
- [AI助手](file:///d:/devtool/cm/backend/app/api/ai_assistant.py) 的自然语言查询展示