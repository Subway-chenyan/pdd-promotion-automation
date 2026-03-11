# Streamlit Cloud 部署设计

**日期:** 2025-03-11
**状态:** 已批准

## 概述

将拼多多商品推广自动化系统从本地开发环境部署到 Streamlit Cloud，实现公网访问和数据持久化。

## 需求分析

| 需求 | 描述 |
|------|------|
| 使用场景 | 内部/个人使用 |
| 成本要求 | 优先免费方案 |
| 平台偏好 | 原生 Python 平台 |
| 数据持久化 | 需要持久化存储 |

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Cloud                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │            Streamlit App (frontend.py)            │  │
│  │  - 用户界面                                        │  │
│  │  - Agent 协调器                                    │  │
│  │  - 业务逻辑                                        │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   External Services                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Supabase   │  │  LLM API     │  │  拼多多 API  │  │
│  │  (PostgreSQL)│  │  (OpenAI)    │  │             │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 托管平台 | Streamlit Cloud | 官方平台，原生支持，完全免费 |
| 数据库 | Supabase PostgreSQL | 免费版足够用，支持持久化 |
| ORM | SQLAlchemy | 支持 PostgreSQL，与现有代码兼容 |

## 数据库迁移

### 现有 SQLite → Supabase PostgreSQL

**需要修改的文件：**
- `database.py` - 替换为 SQLAlchemy + PostgreSQL
- `requirements.txt` - 添加 `sqlalchemy`, `psycopg2-binary`

**Supabase 免费版限制：**
- 500MB 数据库存储
- 50GB 月带宽
- 2 个并发连接

## 环境变量配置

| 变量名 | 说明 | 来源 |
|--------|------|------|
| `LLM_API_KEY` | LLM API 密钥 | 现有 |
| `LLM_BASE_URL` | LLM API 地址 | 现有 |
| `LLM_MODEL` | 模型名称 | 现有 |
| `PDD_CLIENT_ID` | 拼多多 Client ID | 现有 |
| `PDD_CLIENT_SECRET` | 拼多多 Client Secret | 现有 |
| `PDD_PID` | 拼多多推广位 ID | 现有 |
| `DATABASE_URL` | PostgreSQL 连接字符串 | 新增（Supabase） |

## 部署步骤

### 第一步：准备工作
1. 注册 Streamlit Cloud
2. 注册 Supabase 并创建项目
3. 获取 DATABASE_URL

### 第二步：代码修改
1. 修改 `database.py`
2. 更新 `requirements.txt`
3. 在 Supabase 创建表结构

### 第三步：部署
1. 连接 GitHub 仓库到 Streamlit Cloud
2. 配置 Secrets
3. 部署并验证

### 第四步：数据迁移（可选）
- 导出现有 SQLite 数据
- 导入到 Supabase

## 预计时间

总约 30-45 分钟完成部署。
