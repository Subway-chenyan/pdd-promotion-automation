# 拼多多商品推广自动化系统

基于 LangChain Deep Agents 的智能选品与文案生成系统。

## 功能特性

### 🤖 AI-1 选品经理
- 根据关键词搜索商品
- 价格/销量/佣金筛选
- 智能排序和推荐

### 🔧 AI-2 操作员
- 获取商品详细信息
- 生成推广链接
- 整理商品卖点

### ✍️ AI-3 文案师
- 多种文案风格（简洁/紧迫/专业/生活）
- 动态风格匹配
- Emoji装饰

### 🎨 前端界面
- Streamlit 简洁界面
- 可自定义提示词
- 历史记录查看

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# LLM 配置
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# 拼多多 API 配置
PDD_CLIENT_ID=your_client_id_here
PDD_CLIENT_SECRET=your_client_secret_here
PDD_PID=your_pid_here

# 数据库
DB_PATH=data/pdd.db
```

### 3. 运行前端

```bash
streamlit run frontend.py
```

## 项目结构

```
langchain_pdd/
├── .env                      # 环境变量配置
├── .env.example              # 环境变量模板
├── config/
│   └── prompts.yaml          # 默认提示词模板
├── data/
│   └── pdd.db                # SQLite 本地存储
├── skills/
│   ├── __init__.py
│   └── pdd_api_skill.py      # 拼多多API封装
├── agents/
│   ├── __init__.py
│   ├── base_agent.py         # Agent基类
│   ├── product_selector.py   # AI-1 选品经理
│   ├── product_operator.py   # AI-2 操作员
│   └── copywriter.py         # AI-3 文案师
├── coordinator.py            # 主协调器
├── frontend.py               # Streamlit 前端
├── database.py               # 数据库操作
├── models.py                 # 数据模型
├── requirements.txt
└── README.md
```

## 使用说明

1. 在输入框中输入关键词（每行一个）
2. 设置每个关键词的选品数量
3. 选择文案风格（或使用"自动生成"）
4. 点击"生成推广文案"
5. 查看结果并复制文案/链接

## 技术栈

- **Python 3.10+**
- **LangChain** - AI Agent 框架
- **Streamlit** - 前端界面
- **SQLite** - 本地存储
- **Pydantic** - 数据模型

## 注意事项

1. 确保已获取拼多多开放平台 API 密钥
2. 推广位需要完成授权备案
3. API 调用有频率限制（建议 < 50次/分钟）
4. LLM API 需要自行配置

## 部署到 Streamlit Cloud

### 前置准备

1. 注册 [Supabase](https://supabase.com) 并创建项目
2. 在 Supabase SQL Editor 中运行以下 SQL 创建表：

```sql
CREATE TABLE IF NOT EXISTS generation_history (
    id SERIAL PRIMARY KEY,
    keywords TEXT NOT NULL,
    goods_count INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50) NOT NULL,
    template_name VARCHAR(100) NOT NULL,
    system_prompt TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS goods_cache (
    goods_sign VARCHAR(100) PRIMARY KEY,
    goods_data TEXT NOT NULL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

3. 获取 Supabase DATABASE_URL (Project Settings → Database → Connection string)

### 部署步骤

1. 注册 [Streamlit Cloud](https://streamlit.io/cloud)
2. 点击 "New app"
3. 连接你的 GitHub 仓库
4. 选择主分支
5. Main file path: `frontend.py`
6. 在 "Secrets" 中添加以下环境变量：

```
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
PDD_CLIENT_ID=your_client_id_here
PDD_CLIENT_SECRET=your_client_secret_here
PDD_PID=your_pid_here
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
```

7. 点击 "Deploy"

### 部署后

- 应用会在每次 push 到主分支时自动重新部署
- 可在 Streamlit Cloud 查看应用日志
- 免费版限制: 每月 750 小时运行时间

## 许可证

MIT License
