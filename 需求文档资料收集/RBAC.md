# 通用 RBAC 权限管理系统 - 设计提示词

## 系统定位
一套可复用的、企业级基于角色的访问控制（RBAC）权限管理方案，适用于各类业务系统。

---

## 核心设计原则

### 1. 权限模型（RBAC + 数据范围）
用户(User) ←→ 角色(Role) ←→ 权限(Permission) ↑ ↑ 用户角色表 角色权限表（支持启用/禁用）

### 2. 权限编码规范
采用三级编码格式：`模块:动作:范围`

| 层级 | 说明 | 示例 |
|------|------|------|
| 模块 | 业务模块标识 | user、order、product、report |
| 动作 | 操作类型 | create、view、edit、delete、export、approve |
| 范围 | 数据范围 | own（自己的）、all（全部）、dept（部门） |

**标准权限示例：**
- `user:create` - 创建用户
- `order:view:own` - 查看自己的订单
- `order:view:all` - 查看所有订单
- `report:export:dept` - 导出部门报表

### 3. 角色层级设计

| 角色类型 | 说明 | 典型权限 |
|----------|------|----------|
| 超级管理员 | 系统级绝对权限 | 所有权限，含系统配置、数据回滚 |
| 管理员 | 业务级管理权限 | 管理全部业务数据，可分配权限 |
| 普通用户 | 标准业务权限 | 查看公共数据，管理自己的数据 |
| 访客/只读 | 受限查看权限 | 仅查看指定数据，不可修改 |

### 4. 数据范围控制策略

```python
# 权限继承规则（自动展开）
view:all  → 自动包含 view:own
edit:all  → 自动包含 edit:own
delete:all → 自动包含 delete:own

# 检查优先级
1. 超级管理员 → 直接通过
2. 检查具体权限编码
3. 检查继承权限
4. 拒绝访问
```

---

## 数据库模型设计

### 核心表结构

```sql
-- 用户表
users (id, username, role_key[默认角色], status, ...)

-- 角色表
roles (id, role_key[唯一标识], role_name, is_system[系统内置], description)

-- 权限表
permissions (id, permission_code[唯一], permission_name, module, description)

-- 角色权限关联表（支持细粒度开关）
role_permissions (id, role_id, permission_id, is_enabled)

-- 用户角色关联表（支持多角色）
user_roles (id, user_id, role_id)
```

---

## 权限检查逻辑

### 服务端检查流程

```python
async def check_permission(user, permission_code, db):
    # 1. 超级管理员特权
    if is_super_admin(user):
        return True
    
    # 2. 获取用户所有权限（含多角色合并）
    permissions = await get_user_permissions(user, db)
    
    # 3. 权限继承展开
    expanded = expand_permissions(permissions)
    
    # 4. 检查目标权限
    return permission_code in expanded
```

### 权限使用方式

```python
# 方式1：依赖注入（推荐用于路由）
@router.post("/api/orders")
async def create_order(
    current_user: User = Depends(require_permissions("order:create"))
):
    pass

# 方式2：动态检查（推荐用于业务逻辑）
has_edit_all = await check_permission(user, "order:edit:all", db)
has_edit_own = await check_permission(user, "order:edit:own", db)

if not has_edit_all and not has_edit_own:
    raise PermissionDenied()
```

---

## 前端权限集成

### 权限获取接口
```http
GET /api/auth/permissions

Response:
{
  "permissions": ["order:view:own", "order:view:all", ...],
  "roles": ["user", "manager"]
}
```

### 前端控制方式
```javascript
// 按钮级控制
v-if="hasPermission('order:export:all')"

// 路由级控制
{
  path: '/admin',
  meta: { requiredPermissions: ['system:config'] }
}

// 菜单级控制
{
  name: '用户管理',
  visible: hasAnyPermission(['user:create', 'user:edit', 'user:delete'])
}
```

---

## 扩展能力

### 1. 支持权限维度扩展
- 组织架构维度：`order:view:dept`（查看部门数据）
- 数据字段维度：`salary:view:masked`（查看脱敏数据）
- 时间维度：`report:view:temporary`（临时授权）

### 2. 支持动态权限配置
- 运行时启用/禁用角色权限
- 用户临时授权/回收
- 权限版本控制与回滚

### 3. 审计与监控
- 权限变更日志
- 敏感操作记录
- 权限使用统计

---

## 快速接入指南

### 步骤1：初始化权限数据
```python
DEFAULT_PERMISSIONS = [
    # 模块:动作:范围 → 权限编码, 权限名称, 模块, 描述
    ("user", "create", None) → ("user:create", "创建用户", "USER", "添加新用户"),
    ("order", "view", "own") → ("order:view:own", "查看自己的订单", "ORDER", "..."),
    ("order", "view", "all") → ("order:view:all", "查看所有订单", "ORDER", "..."),
]

DEFAULT_ROLES = {
    "admin": [所有权限],
    "manager": [查看全部, 管理业务数据],
    "user": [查看公共, 管理自己的数据],
}
```

### 步骤2：在业务路由中使用
```python
from auth import check_permission, require_permissions

@router.get("/api/orders")
async def list_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 动态检查数据范围权限
    can_view_all = await check_permission(current_user, "order:view:all", db)
    can_view_own = await check_permission(current_user, "order:view:own", db)
    
    if can_view_all:
        return await get_all_orders(db)
    elif can_view_own:
        return await get_my_orders(current_user.id, db)
    else:
        raise HTTPException(403, "权限不足")
```

### 步骤3：前端同步控制
```javascript
// 获取权限列表
const { permissions } = await fetch('/api/auth/permissions').then(r => r.json());

// 权限检查工具
const hasPermission = (code) => permissions.includes(code);
const hasAnyPermission = (codes) => codes.some(hasPermission);
```

---

## 评估标准

| 能力维度 | 本方案 | 说明 |
|----------|--------|------|
| RBAC 基础 | ✅ | 标准角色-权限模型 |
| 细粒度权限 | ✅ | 模块+动作+范围三级编码 |
| 数据范围隔离 | ✅ | own/all/dept 灵活控制 |
| 权限继承 | ✅ | 自动展开，减少配置 |
| 多角色组合 | ✅ | 用户可拥有多个角色 |
| 动态权限分配 | ✅ | 运行时启用/禁用 |
| 超级管理员特权 | ✅ | 绝对权限绕过检查 |
| 权限审计 | ✅ | 操作日志记录 |
| ABAC（属性权限） | ⚠️ | 可扩展，需自定义 |
| 权限时效控制 | ⚠️ | 可扩展，需自定义 |

---

## 适用场景

✅ **适合使用：**
- 企业管理系统（ERP、CRM、OA）
- 电商平台后台
- 内容管理系统（CMS）
- 数据分析平台
- 任何需要用户权限隔离的系统

❌ **不适合使用：**
- 纯公开访问系统
- 需要复杂属性权限（如"金额>1万需审批"）的金融系统
- 需要多租户完全隔离的 SaaS 平台

---

## 设计优势

1. **简单可理解**：三级编码直观清晰
2. **灵活可扩展**：模块、动作、范围均可扩展
3. **前后端统一**：同一套权限编码贯穿全栈
4. **业务无关**：不绑定具体业务，可复用
5. **渐进增强**：基础功能完备，高级特性可扩展