# E9 智能化薪资核算系统 — 项目规则

> **版本**: v1.0
> **日期**: 2026-05-13
> **状态**: 项目启动阶段，尚未进入编码

---

## 1. 项目标识

| 项 | 值 |
|---|-----|
| 项目名称 | E9 智能化薪资核算系统 |
| 简称 | E9-Salary |
| 需求文档 | `需求文档资料收集/需求文档.md`（项目宪法） |
| 目标用户 | 人事专员、人事主管、人事经理、会计、普通员工（约 61 人规模） |

---

## 2. 技术栈（公司强制规范）

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + Tailwind CSS + Element Plus | 管理后台模式 |
| 后端 | Python + FastAPI | RESTful API |
| 数据库 | PostgreSQL | 最新稳定版 |
| AI | 阿里云百炼 | Qwen3.5-Plus / Flash 及 VL 版 |
| 部署 | Docker Compose | Windows 环境优先，支持本地部署 |

---

## 3. 模块清单

### 3.1 业务模块

| 模块 | 英文标识 | 说明 | 依赖 |
|------|---------|------|------|
| 人事信息登记 | employee | 员工档案、入转调离、人事月报、绩效评分、社保公积金管理 | 无 |
| 考勤管理 | attendance | 考勤导入、异常识别、计薪天数计算 | 人事信息登记（弱） |
| 薪资核算 | salary | 数据源汇总、公式计算、个税匹配、实发工资核算 | 人事信息登记（强）、考勤管理（强） |
| 审批流程 | approval | 薪资审核（主管 + 经理两级） | 薪资核算（强） |
| 报表导出 | report | 花名册、考勤表、工资条、人事月报等导出 | 所有业务模块（弱） |

### 3.2 系统模块

| 模块 | 英文标识 | 说明 |
|------|---------|------|
| 用户管理 | sys_user | 用户增删改查、密码重置、账号锁定、批量导入 |
| 权限管理 | sys_permission | 角色管理、功能/数据范围/字段三级权限配置 |
| 操作日志 | sys_log | 登录日志、操作日志、数据变更日志、日志导出 |
| 数据字典 | sys_dict | 合同公司、部门、职务、用工状态、薪资项目、假期类型等枚举管理 |

---

## 4. 架构铁律

### 4.1 模块独立

- 每个模块拥有独立的界面、业务逻辑、数据层
- **严禁**模块间直接 import 对方的 Service / State / Controller
- 模块间通信仅通过以下两种方式：
  - **共享数据表**：直接查询共享表获取数据
  - **事件总线**：发布/订阅事件触发动作

### 4.2 共享表清单

| 共享表 | 主要读取方 | 主要写入方 | 说明 |
|--------|-----------|-----------|------|
| employees（员工表） | 所有业务模块 | 人事信息登记模块 | 员工基础档案 |
| employee_salaries（员工薪资表） | 薪资核算模块、报表模块 | 人事信息登记模块 | 员工薪资标准档案 |
| salary_calculations（薪资核算表） | 审批流程模块、报表模块 | 薪资核算模块 | 月度薪资计算结果 |
| attendance_records（考勤记录表） | 薪资核算模块 | 考勤管理模块 | 月度考勤统计 |
| performance_scores（绩效记录表） | 薪资核算模块 | 人事信息登记模块 | 月度绩效评价 |
| social_insurance（社保公积金表） | 薪资核算模块 | 人事信息登记模块 | 月度社保公积金缴纳 |
| legacy_adjustments（遗留金额调整表） | 薪资核算模块 | 人事信息登记模块 | 历史错漏补救金额 |
| travel_reimbursements（差旅补贴表） | 薪资核算模块 | 会计/人事 | 差旅报销费用 |
| labor_compensations（劳动补偿金表） | 薪资核算模块 | 人事信息登记模块 | 单独报税的经济补偿金 |
| calculation_logs（核算日志表） | 所有模块 | 薪资核算模块 | 薪资核算过程日志 |
| sys_dict_base（数据字典基础表） | 所有模块 | 系统管理模块 | 统一数据字典 |

### 4.3 模块开关机制

- 每个模块在系统配置表中有一个 `enabled` 开关
- admin 可在系统设置中逐个开启/关闭模块
- 关闭模块时：前端隐藏入口、停止后台任务、**保留数据不删除**
- 重新开启后：恢复入口和任务，数据完整可用

### 4.4 优雅降级

- 外部数据源不可用时（钉钉 API、个税系统），显示友好中文提示，不崩溃
- 详见需求文档第 8.11 节错误处理规范

---

## 5. 环境要求

### 5.1 虚拟环境隔离

- 本项目使用**独立的 Python 虚拟环境**（`venv`），不得与其他项目共用
- 前端依赖安装在项目本地 `node_modules`，不使用全局安装
- 数据库使用独立的 PostgreSQL 实例或 Docker 容器

### 5.2 开发环境

| 工具 | 版本要求 |
|------|---------|
| Python | ≥ 3.10 |
| Node.js | ≥ 18 |
| PostgreSQL | 最新稳定版 |
| Docker | 可选，用于 docker-compose 部署 |

### 5.3 操作系统

- 开发与部署均优先支持 **Windows**
- 注意路径分隔符和行尾符（CRLF）

---

## 6. 接口规范

- 遵循 RESTful 风格
- **仅限 GET 和 POST 方法**（PUT / DELETE / PATCH 全部转为 POST）
- 必须输出 Swagger API 文档（FastAPI 自动生成）
- 所有错误响应使用中文提示，含错误码（详见需求文档 8.11 节）

---

## 7. 数据规范

| 规范项 | 说明 |
|--------|------|
| 金额精度 | DECIMAL(10,2)，底层单位为**元** |
| 金额展示 | 前端若展示"万"为单位，须自动除以 10000 |
| 日期格式 | YYYY-MM-DD |
| 核算周期 | YYYYMM（VARCHAR(7)） |
| 密码存储 | bcrypt 加密 |
| 认证方式 | JWT Token，过期时间 ≤ 24 小时 |

---

## 8. UI 视觉与交互规范

### 8.1 整体风格

- **苹果风半透明蓝色渐变**作为主视觉基调，专业大气
- 全局表格、表单、提示弹窗与确认框样式必须统一
- 组件库：**Element Plus**
- 主色调：蓝色，白色/半透磨砂卡片背景（可加入轻微毛玻璃效果）

### 8.2 页面结构

1. 最外层用 `el-card` 包裹（卡片可带半透明蓝白渐变）
2. 顶部操作栏：左侧放操作按钮，右侧放搜索框
3. 中间数据表格（带边框、隔行变色）
4. 底部分页控件

### 8.3 按钮规范

- 新增按钮：蓝色，带 Plus 图标
- 删除按钮：红色，带 Delete 图标
- 表格内操作：link 样式（文字链接）
- 所有按钮都要有图标

### 8.4 表格规范

- 使用 `el-table`，配置 `border` 和 `stripe`
- 操作列固定在右侧（`fixed="right"`）
- 长文本显示省略号，鼠标悬停显示完整内容
- 表头与行样式需与苹果风半透明蓝色渐变统一

### 8.5 表单规范

- 使用 `el-form`，标签宽度 100px
- 必填项前面加红色星号
- 弹窗宽度 500-600px
- 弹窗背景、边框、阴影需与整体半透明蓝渐变风格统一

### 8.6 弹窗与确认框规范

- 所有弹窗和确认框样式必须统一
- 使用 Element Plus 的 Dialog 和 MessageBox
- 确认框采用危险主题（红色确认）

### 8.7 交互要求

- 删除操作要有确认提示
- 操作成功要有消息提示
- 加载数据时显示 loading 状态
- AI 交互采用**流式输出**（打字机效果）

---

## 9. 权限模型

- **三层权限**：功能权限 + 数据范围权限 + 字段级权限
- admin 拥有绝对特权（系统配置 + 数据回滚），不可被其他角色限制
- 其余角色按"最小必要权限"原则配置
- 支持用户关联多角色，权限取并集
- 支持临时授权
- 新增功能必须同步纳入权限配置体系

---

## 10. 禁止事项（红线）

- 硬编码业务常量或枚举（一律使用数据字典）
- 模块间直接 import 代码依赖
- 关闭模块时删除其数据
- 角色固化权限
- 错误提示不使用中文
- 忽略控制台警告
- 多个项目共用同一个 Python 环境
- 使用非 MIT / Apache 2.0 许可证的第三方组件

---

## 11. 目录结构（规划）

```
project/
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── core/           # 核心配置、安全、数据库
│   │   │   ├── config.py           # 配置管理
│   │   │   ├── database.py         # 数据库连接
│   │   │   ├── security.py         # 密码加密、JWT
│   │   │   └── exceptions.py       # 自定义异常
│   │   ├── modules/        # 业务模块（按模块独立目录）
│   │   │   ├── employee/   # 人事信息登记
│   │   │   │   ├── models.py       # 数据模型（employees, employee_salaries, performance_scores, social_insurance）
│   │   │   │   ├── schemas.py      # Pydantic 模式
│   │   │   │   ├── service.py      # 业务逻辑
│   │   │   │   └── routes.py       # API 路由
│   │   │   ├── attendance/ # 考勤管理
│   │   │   │   ├── models.py       # 数据模型（attendance_records）
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   └── routes.py
│   │   │   ├── salary/     # 薪资核算
│   │   │   │   ├── models.py       # 数据模型（salary_calculations, calculation_logs, legacy_adjustments, travel_reimbursements, labor_compensations）
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   ├── calculator.py   # 薪资计算引擎
│   │   │   │   └── routes.py
│   │   │   ├── approval/   # 审批流程
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   └── routes.py
│   │   │   ├── report/     # 报表导出
│   │   │   │   ├── export.py       # Excel/PDF 导出
│   │   │   │   └── routes.py
│   │   │   └── system/     # 系统管理（用户/权限/日志/字典）
│   │   │       ├── user.py         # 用户管理
│   │   │       ├── permission.py   # 权限管理
│   │   │       ├── log.py          # 操作日志
│   │   │       └── dict.py         # 数据字典
│   │   └── shared/         # 共享表模型
│   │       └── models.py   # 所有模块共享的数据模型导入
│   ├── requirements.txt
│   └── main.py
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── views/          # 按模块分目录
│   │   │   ├── employee/   # 人事信息登记
│   │   │   ├── attendance/ # 考勤管理
│   │   │   ├── salary/     # 薪资核算
│   │   │   ├── approval/   # 审批流程
│   │   │   ├── report/     # 报表导出
│   │   │   └── system/     # 系统管理
│   │   ├── components/     # 共享组件
│   │   │   ├── TableCard.vue       # 表格卡片封装
│   │   │   ├── SearchBar.vue       # 搜索栏封装
│   │   │   ├── Pagination.vue      # 分页控件封装
│   │   │   └── PermissionWrapper.vue # 权限控制封装
│   │   ├── stores/         # 状态管理（Pinia）
│   │   │   ├── user.js             # 用户状态
│   │   │   ├── permission.js       # 权限状态
│   │   │   └── app.js              # 应用全局状态
│   │   ├── api/            # API 接口
│   │   │   ├── employee.js
│   │   │   ├── attendance.js
│   │   │   ├── salary.js
│   │   │   ├── approval.js
│   │   │   ├── report.js
│   │   │   └── system.js
│   │   ├── utils/          # 工具函数
│   │   │   ├── request.js          # Axios 封装
│   │   │   ├── auth.js             # 认证工具
│   │   │   └── format.js           # 格式化工具（金额、日期）
│   │   └── styles/         # 全局样式
│   │       └── tailwind.css
│   └── package.json
├── docker-compose.yml      # Docker 编排
├── DEPLOY.md              # 部署文档
├── README.md              # 项目说明
├── PROJECT_RULES.md       # 本文件
├── CHANGELOG.md           # 版本文件
├── AI_KNOWLEDGE.md        # 全栈技术通识词典
├── .gitignore
└── 需求文档资料/
    └── 需求文档.md         # 项目宪法
```

---

> **下一步**: 待用户确认待确认事项（需求文档第10章）后，进入骨架搭建阶段。

---

## 12. 数据表结构（与需求文档同步）

> 本节定义系统核心数据表结构，详细字段定义以需求文档第 6 章为准。

### 12.1 核心业务表

| 表名 | 中文名 | 主要字段 | 说明 |
|------|------|---------|------|
| employees | 员工表 | id, employee_no, name, gender, id_card, contract_company_id, department_id, position_id, status_id, entry_date, regular_date, resign_date, bank_card, home_address | 员工基础档案 |
| employee_salaries | 员工薪资表 | id, employee_id, base_salary, performance_standard, meal/transport/communication/computer/housing_allowance, effective_date | 员工薪资标准档案 |
| attendance_records | 考勤记录表 | id, period, employee_id, total_work_days, actual_work_days, attendance_rate, late_count, early_count, sick_leave_days, personal_leave_days | 月度考勤统计 |
| performance_scores | 绩效评分表 | id, period, employee_id, initial_score, final_score, coefficient | 月度绩效评价 |
| social_insurance | 社保公积金表 | id, period, employee_id, si_base, si_personal, si_company, hf_base, hf_personal, hf_company | 月度社保公积金缴纳 |
| salary_calculations | 薪资核算表 | id, period, employee_id, base_salary, performance_coefficient, gross_salary, social_insurance_personal, housing_fund_personal, tax_deduction, net_salary, review_status | 月度薪资计算结果 |

### 12.2 辅助数据表

| 表名 | 中文名 | 主要字段 | 说明 |
|------|------|---------|------|
| legacy_adjustments | 遗留金额调整表 | id, period, employee_id, pretax_amount, posttax_amount, reason | 历史错漏补救金额 |
| travel_reimbursements | 差旅补贴表 | id, period, employee_id, amount, is_taxed | 差旅报销费用 |
| labor_compensations | 劳动补偿金表 | id, period, employee_id, amount, tax_status | 单独报税的经济补偿金 |
| calculation_logs | 核算日志表 | id, period, batch_no, start_time, end_time, employee_count, success_count, detail_log | 薪资核算过程日志 |

### 12.3 系统表

| 表名 | 中文名 | 主要字段 | 说明 |
|------|------|---------|------|
| sys_users | 用户表 | id, username, password_hash, employee_id, role_ids, data_scope, is_locked | 系统登录用户 |
| sys_roles | 角色表 | id, name, description, is_system | 角色定义 |
| sys_permissions | 权限表 | id, role_id, module, action, data_scope, field_config | 权限配置 |
| sys_operation_logs | 操作日志表 | id, user_id, module, action, target, detail, created_at | 操作审计日志 |
| sys_dict_base | 数据字典表 | id, dict_type, code, name, parent_id, sort_order, is_enabled, extra_config | 统一数据字典 |