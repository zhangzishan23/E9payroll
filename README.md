# E9 智能化薪资核算系统

> 面向 E9 公司（含北京易玖、广州分公司、邯郸分公司、上海瑞方 4 个法律主体）的薪资核算管理系统。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Tailwind CSS + Element Plus |
| 后端 | Python + FastAPI |
| 数据库 | SQLite（开发阶段）/ PostgreSQL（生产环境） |
| 认证 | JWT（python-jose） |

## 项目结构

```
cm/
├── backend/                # 后端（FastAPI）
│   ├── app/
│   │   ├── api/            # API 路由（auth、employees、attendance、salary、approval、reports、system、performance、social_insurance、ai_assistant）
│   │   ├── core/           # 核心配置（config、database、security）
│   │   ├── models/         # 数据模型（SQLAlchemy ORM）
│   │   ├── schemas/        # Pydantic 请求/响应模型
│   │   ├── services/       # 业务逻辑层
│   │   └── main.py         # 应用入口
│   ├── venv/               # Python 虚拟环境（独立隔离）
│   ├── requirements.txt    # Python 依赖清单
│   ├── seed.py             # 种子数据初始化脚本
│   └── e9_salary.db        # SQLite 数据库文件
├── frontend/               # 前端（Vue 3）
│   ├── src/
│   │   ├── api/            # Axios 封装与拦截器
│   │   ├── router/         # Vue Router 路由配置
│   │   ├── stores/         # Pinia 状态管理
│   │   ├── views/          # 页面组件（按模块分目录）
│   │   ├── App.vue         # 根组件
│   │   └── main.js         # 前端入口
│   ├── index.html          # HTML 模板
│   ├── vite.config.js      # Vite 配置（含 API 代理）
│   └── package.json        # 前端依赖清单
├── .skills/                # 可复用技能单元（Skill）
├── 需求文档.md              # 项目宪法（需求文档）
├── PROJECT_RULES.md         # 项目规则
├── CHANGELOG.md             # 版本变更记录
├── AI_KNOWLEDGE.md          # 全栈技术通识词典
└── .gitignore               # Git 忽略规则
```

## 快速启动

### 环境要求

- Python 3.10+
- Node.js 18+
- npm 9+

### 1. 启动后端

```powershell
cd backend

# 创建虚拟环境（首次）
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 安装依赖
venv\Scripts\python.exe -m pip install -r requirements.txt

# 初始化种子数据
venv\Scripts\python.exe seed.py

# 启动服务（端口 8010）
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

### 2. 启动前端

```powershell
cd frontend

# 安装依赖（首次）
npm install

# 启动开发服务器（端口 5180）
cd frontend
npm run dev
```

### 3. 访问系统

- 前端页面：http://localhost:5180
- 后端 API 文档：http://localhost:8010/docs
- 健康检查：http://localhost:8010/api/health

### 测试账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 系统管理员 |
| hr001 | 123456 | 人事专员 |

## 模块清单

| 模块 | 前端路由 | 后端 API 前缀 | 说明 |
|------|---------|--------------|------|
| 人事信息登记 | /employees | /api/employees | 员工档案管理 |
| 考勤管理 | /attendance | /api/attendance | 考勤导入与统计 |
| 绩效管理 | /performance | /api/performance | 绩效数据录入与管理 |
| 社保公积金 | /insurance | /api/social-insurance | 社保公积金数据管理 |
| 薪资核算 | /salary | /api/salary | 月度薪资计算 |
| 审批流程 | /approval | /api/approval | 薪资审核流程 |
| 报表导出 | /reports | /api/reports | 统计中心 + 报表导出 |
| 用户管理 | /system/users | /api/system | 用户增删改查 |
| 角色管理 | /system/roles | /api/system | 角色与权限配置 |
| 数据字典 | /system/dict | /api/system | 枚举数据管理 |
| 操作日志 | /system/logs | /api/system | 操作日志查看 |
| AI助手 | 浮动入口 | /api/ai | 智能问答与快速操作 |

## 最近一次修改

- **2026-05-18**：②**Skill技能库**：抽取出 7 个可复用技能单元到 `.skills/` 目录：`dict-resolver`（字典解析）、`excel-toolkit`（Excel导入导出）、`log-writer`（操作日志）、`salary-formula`（薪资公式）、`data-completeness`（数据完整性）、`ai-intent`（意图识别）、`auth-guard`（认证权限）。每个 Skill = 代码 + 使用说明 + 依赖与错误处理。

- **2026-05-18**：①**AI助手模块**：在侧边栏新增浮动AI助手入口（🤖图标），支持自然语言查询、录入和编辑系统信息。内置规则引擎可处理员工查询、薪资概况、考勤统计、绩效情况、社保公积金、系统状态等常见查询。复杂问题可配置接入LLM，编辑操作需用户二次确认，权限由系统管理员通过角色管理配置。

- **2026-05-17**：①**社保公积金管理模块**：新增左侧导航「社保公积金」入口，支持按月查看/录入/编辑员工社保公积金数据（社保基数、社保个人、社保公司、公积金基数、公积金个人、公积金公司），支持开启编辑模式内联修改、批量导入Excel、批量删除、按月导出。不同城市（北京/广州/邯郸/上海）的费率和基数不同，可按各公司实际情况填写。②**报表统计中心**：在报表导出页面新增「数据统计中心」卡片区，展示在职员工总数、薪资核算完成进度、审核通过/驳回数、考勤出勤率、人均应发/实发工资、迟到总次数、请假总天数等关键指标。③**薪资核算表工具提示**：鼠标悬停在列名上可查看该字段的说明信息（数据来源、计算公式等），补贴合计/应发工资/社保公积金合计/实发工资/实际应税等总计列黄色高亮。

## 反思

- 当前使用 SQLite 快速验证，后续需切换到 PostgreSQL 以支持并发多设备刷写。
- 薪资核算核心公式已实现自动计算逻辑，但需补充单元测试与集成测试。
- 绩效管理模块已独立，绩效系数通过 `/api/performance` 管理，薪资核算时自动关联。
- 各页面月份筛选已统一使用 el-date-picker，用户体验一致。
- 所有表格已添加复选框支持多选，为批量操作（如批量导出、批量删除）奠定基础。
- AI助手使用规则引擎+LLM混合模式，当前规则引擎覆盖了核心查询场景，复杂语义需接入LLM后进一步提升体验。