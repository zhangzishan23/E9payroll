# E9 智能化薪资核算系统 - Docker 部署指南

## 环境要求

- Docker ≥ 20.10
- Docker Compose ≥ 2.0
- 操作系统：Windows / Linux / macOS

## 快速开始

### 1. 准备环境变量

复制环境变量模板并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少修改以下配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `DB_PASSWORD` | 数据库密码 | `e9salary_change_me` |
| `SECRET_KEY` | JWT 密钥（生产环境必须修改） | 占位符 |
| `LLM_API_KEY` | 阿里云百炼 API Key | 空 |
| `DINGTALK_CLIENT_ID` | 钉钉应用 Client ID | 空 |
| `DINGTALK_CLIENT_SECRET` | 钉钉应用 Client Secret | 空 |
| `DINGTALK_AGENT_ID` | 钉钉应用 Agent ID | 空 |

### 2. 启动服务

```bash
docker-compose up -d --build
```

首次启动会自动：
- 创建 PostgreSQL 数据库
- 构建前后端镜像
- 初始化数据库表结构
- 创建默认管理员账号（admin / admin123）

### 3. 访问系统

| 服务 | 地址 |
|------|------|
| 前端页面 | http://localhost:8080/e9salary/ |
| 后端 API | http://localhost:8001 |
| API 文档 | http://localhost:8001/e9salary/docs |
| 数据库（外部） | localhost:5433 |

默认登录账号：
- 用户名：`admin`
- 密码：`admin123`

## 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 8080 | 前端 | Nginx 提供 Web 服务 |
| 8001 | 后端 | FastAPI 后端服务 |
| 5433 | PostgreSQL | 数据库外部访问端口（容器内为 5432） |

## 目录结构

```
project/
├── data/
│   ├── postgres/    # PostgreSQL 数据文件
│   └── app/         # 应用数据（上传文件等）
├── backups/         # 数据库备份文件
├── temp/            # 临时文件目录
├── docker-compose.yml
├── .env
└── .env.example
```

**注意**：所有数据都存储在项目目录下的 `data/` 文件夹中，备份只需复制整个 `data/` 和 `backups/` 目录即可。

## 常用命令

### 查看服务状态

```bash
docker-compose ps
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### 停止服务

```bash
docker-compose down
```

### 停止服务并删除数据（⚠️ 危险）

```bash
docker-compose down -v
```

### 重启服务

```bash
docker-compose restart
```

### 重新构建并启动

```bash
docker-compose up -d --build
```

### 进入后端容器

```bash
docker-compose exec backend bash
```

### 数据库备份

```bash
docker-compose exec db pg_dump -U e9salary e9_salary > backups/backup_$(date +%Y%m%d_%H%M%S).sql
```

### 数据库恢复

```bash
cat backups/backup_file.sql | docker-compose exec -T db psql -U e9salary e9_salary
```

## 本地开发 vs Docker 部署

| 项 | 本地开发 (start.bat) | Docker 部署 |
|----|---------------------|-------------|
| 数据库 | 本地 PostgreSQL 5432 | Docker 容器 5433（外部）|
| 后端端口 | 8010 | 8001 |
| 前端端口 | 5180 | 8080 |
| 启动方式 | 双击 start.bat | docker-compose up -d |

## 注意事项

1. **首次启动**可能需要几分钟时间构建镜像和初始化数据库，请耐心等待
2. **生产环境**务必修改 `SECRET_KEY` 和数据库密码
3. **数据持久化**：所有数据都在 `data/` 目录下，不要删除
4. **备份迁移**：直接复制 `data/` 和 `backups/` 目录到新服务器即可
5. **钉钉/AI配置**：如不需要相关功能，可留空不影响系统运行
6. **上传限制**：系统默认支持最大 50MB 的 Excel 文件上传

## 故障排查

### 端口被占用

修改 `.env` 文件中的端口配置：

```env
FRONTEND_PORT=8081
BACKEND_PORT=8002
DB_EXTERNAL_PORT=5434
```

### 数据库连接失败

检查数据库容器是否健康：

```bash
docker-compose ps
```

如果 db 服务状态不是 `healthy`，查看日志：

```bash
docker-compose logs db
```

### 前端无法访问 API

检查后端是否启动完成，后端需要等待数据库完全就绪后才能启动。

```bash
docker-compose logs backend
```

看到类似 `Application startup complete` 的日志表示后端已就绪。

### 重置管理员密码

进入后端容器执行：

```bash
docker-compose exec backend python init_admin.py
```

此命令会检测 admin 用户是否存在，不存在则创建，存在则跳过。
