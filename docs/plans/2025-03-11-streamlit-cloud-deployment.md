# Streamlit Cloud 部署实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将拼多多商品推广自动化系统从本地 SQLite 迁移到 Supabase PostgreSQL，并部署到 Streamlit Cloud。

**Architecture:** 使用 SQLAlchemy ORM 支持 PostgreSQL，保持现有 Database 类接口不变。通过 Supabase 免费版提供持久化存储，Streamlit Cloud 托管应用。

**Tech Stack:** Streamlit Cloud, SQLAlchemy, psycopg2, Supabase PostgreSQL

---

## 准备工作

### Task 1: 注册并创建 Supabase 项目

**Step 1: 访问 Supabase 并注册**

访问: https://supabase.com
点击 "Start your project"

**Step 2: 创建新项目**

- 组织名称: 随意（如 "Personal"）
- 项目名称: `pdd-promotion` (或类似)
- 数据库密码: 生成并保存强密码（记录到密码管理器）
- 区域: 选择 Southeast Asia (Singapore) 或离你最近的
- 点击 "Create new project"

**Step 3: 获取数据库连接字符串**

等待项目创建完成（约 2 分钟）
进入 Project Settings → Database
找到 Connection string → 选择 "Python" 格式
复制连接字符串（格式: `postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres`）

**Expected Output:** 获得类似 `postgresql://postgres:xxx@xxx.supabase.co:5432/postgres` 的连接字符串

---

### Task 2: 更新 requirements.txt

**Files:**
- Modify: `requirements.txt`

**Step 1: 添加 SQLAlchemy 和 PostgreSQL 驱动**

编辑 `requirements.txt`，添加以下行到文件末尾:

```
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
```

**Step 2: 验证文件内容**

运行: `cat requirements.txt`

Expected: 文件应包含新的依赖项

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add SQLAlchemy and PostgreSQL dependencies

Prepare for migration from SQLite to Supabase PostgreSQL."
```

---

### Task 3: 创建新数据库实现

**Files:**
- Create: `database_new.py`

**Step 1: 创建新的数据库实现文件**

创建 `database_new.py`:

```python
"""
数据库操作 - SQLAlchemy + PostgreSQL
"""
import json
import os
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from models import GenerationResult, PromptTemplate

Base = declarative_base()


# ORM 模型定义
class GenerationHistory(Base):
    """历史记录表"""
    __tablename__ = 'generation_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    keywords = Column(Text, nullable=False)
    goods_count = Column(Integer, nullable=False)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))


class PromptTemplateDB(Base):
    """提示词模板表"""
    __tablename__ = 'prompt_templates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(50), nullable=False)
    template_name = Column(String(100), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))


class GoodsCache(Base):
    """商品缓存表"""
    __tablename__ = 'goods_cache'

    goods_sign = Column(String(100), primary_key=True)
    goods_data = Column(Text, nullable=False)
    cached_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))


class Database:
    """PostgreSQL 数据库操作"""

    def __init__(self, database_url: str = None):
        if database_url is None:
            database_url = os.getenv('DATABASE_URL', 'sqlite:///data/pdd.db')

        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._init_db()

    def _get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    def _init_db(self):
        """初始化数据库表"""
        # 检查是否是 PostgreSQL
        is_postgresql = 'postgres' in str(self.engine.url)

        if is_postgresql:
            # PostgreSQL: 使用 SERIAL 实现自增
            Base.metadata.create_all(self.engine)
        else:
            # SQLite: 使用 INTEGER PRIMARY KEY AUTOINCREMENT
            Base.metadata.create_all(self.engine)

        # 插入默认提示词模板
        session = self._get_session()
        try:
            existing_count = session.query(PromptTemplateDB).count()
            if existing_count == 0:
                self._insert_default_prompts(session)
            session.commit()
        finally:
            session.close()

    def _insert_default_prompts(self, session: Session):
        """插入默认提示词模板"""
        default_prompts = [
            {
                "agent_name": "selector",
                "template_name": "默认选品",
                "system_prompt": "你是一个专业的商品选品经理，擅长从拼多多平台筛选高性价比商品。你需要根据关键词搜索商品，并按照性价比、销量、优惠等标准筛选。",
                "user_prompt_template": "根据以下要求选品：\n关键词: {keywords}\n数量: {count}",
                "is_default": True,
            },
            {
                "agent_name": "operator",
                "template_name": "默认操作员",
                "system_prompt": "你是商品信息处理专员，负责获取商品详情并生成推广链接。你需要整理商品信息，包括价格、优惠券、佣金、销量等关键数据。",
                "user_prompt_template": "处理以下商品列表，获取详情和推广链接",
                "is_default": True,
            },
            {
                "agent_name": "copywriter",
                "template_name": "默认文案师",
                "system_prompt": "你是一位资深的电商文案策划，擅长创作吸引人的推广文案。你的文案风格包括：简洁直接、紧迫感、专业风、生活化。你需要根据商品类型自动选择最合适的风格，并在文案中适当使用emoji。",
                "user_prompt_template": "为以下商品生成推广文案\n商品信息：{goods_info}\n风格要求：{style}",
                "is_default": True,
            },
        ]

        for prompt in default_prompts:
            db_prompt = PromptTemplateDB(**prompt)
            session.add(db_prompt)

    # 历史记录操作

    def save_history(self, keywords: List[str], count: int, result: dict) -> int:
        """保存生成历史"""
        session = self._get_session()
        try:
            history = GenerationHistory(
                keywords=json.dumps(keywords),
                goods_count=count,
                result_json=json.dumps(result, ensure_ascii=False)
            )
            session.add(history)
            session.commit()
            session.refresh(history)
            return history.id
        finally:
            session.close()

    def get_history(self, limit: int = 20) -> List[dict]:
        """获取历史记录"""
        session = self._get_session()
        try:
            records = session.query(GenerationHistory).order_by(
                GenerationHistory.created_at.desc()
            ).limit(limit).all()

            return [
                {
                    "id": r.id,
                    "keywords": json.loads(r.keywords),
                    "goods_count": r.goods_count,
                    "result": json.loads(r.result_json),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        finally:
            session.close()

    # 提示词模板操作

    def get_prompt_templates(self, agent_name: Optional[str] = None) -> List[PromptTemplate]:
        """获取提示词模板"""
        session = self._get_session()
        try:
            query = session.query(PromptTemplateDB)
            if agent_name:
                query = query.filter(PromptTemplateDB.agent_name == agent_name)
                query = query.order_by(PromptTemplateDB.is_default.desc(), PromptTemplateDB.created_at.desc())
            else:
                query = query.order_by(PromptTemplateDB.agent_name, PromptTemplateDB.is_default.desc(), PromptTemplateDB.created_at.desc())

            records = query.all()

            return [
                PromptTemplate(
                    id=r.id,
                    agent_name=r.agent_name,
                    template_name=r.template_name,
                    system_prompt=r.system_prompt,
                    user_prompt_template=r.user_prompt_template,
                    is_default=bool(r.is_default),
                    created_at=r.created_at,
                )
                for r in records
            ]
        finally:
            session.close()

    def save_prompt_template(self, template: PromptTemplate) -> int:
        """保存提示词模板"""
        session = self._get_session()
        try:
            if template.id:
                # 更新
                record = session.query(PromptTemplateDB).filter(PromptTemplateDB.id == template.id).first()
                if record:
                    record.agent_name = template.agent_name
                    record.template_name = template.template_name
                    record.system_prompt = template.system_prompt
                    record.user_prompt_template = template.user_prompt_template
                    record.is_default = template.is_default
                    session.commit()
                    return template.id
            else:
                # 新建
                record = PromptTemplateDB(
                    agent_name=template.agent_name,
                    template_name=template.template_name,
                    system_prompt=template.system_prompt,
                    user_prompt_template=template.user_prompt_template,
                    is_default=template.is_default,
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                return record.id
        finally:
            session.close()

    def delete_prompt_template(self, template_id: int) -> bool:
        """删除提示词模板"""
        session = self._get_session()
        try:
            record = session.query(PromptTemplateDB).filter(PromptTemplateDB.id == template_id).first()
            if record:
                session.delete(record)
                session.commit()
                return True
            return False
        finally:
            session.close()

    # 商品缓存操作

    def cache_goods(self, goods_sign: str, goods_data: dict):
        """缓存商品数据"""
        session = self._get_session()
        try:
            # 使用 merge 实现 upsert
            record = GoodsCache(
                goods_sign=goods_sign,
                goods_data=json.dumps(goods_data, ensure_ascii=False)
            )
            session.merge(record)
            session.commit()
        finally:
            session.close()

    def get_cached_goods(self, goods_sign: str) -> Optional[dict]:
        """获取缓存的商品数据"""
        session = self._get_session()
        try:
            record = session.query(GoodsCache).filter(GoodsCache.goods_sign == goods_sign).first()
            if record:
                return json.loads(record.goods_data)
            return None
        finally:
            session.close()
```

**Step 2: 验证文件创建**

运行: `ls -la database_new.py`

Expected: 文件已创建

**Step 3: Commit**

```bash
git add database_new.py
git commit -m "feat: add SQLAlchemy-based PostgreSQL database implementation

Create new database implementation using SQLAlchemy ORM with
PostgreSQL support. Maintains same interface as existing Database class."
```

---

### Task 4: 在 Supabase 中创建数据库表

**Step 1: 访问 Supabase SQL Editor**

在 Supabase 项目中，点击左侧菜单 "SQL Editor"
点击 "New query"

**Step 2: 创建数据库表**

复制并执行以下 SQL:

```sql
-- 历史记录表
CREATE TABLE IF NOT EXISTS generation_history (
    id SERIAL PRIMARY KEY,
    keywords TEXT NOT NULL,
    goods_count INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 提示词模板表
CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50) NOT NULL,
    template_name VARCHAR(100) NOT NULL,
    system_prompt TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 商品缓存表
CREATE TABLE IF NOT EXISTS goods_cache (
    goods_sign VARCHAR(100) PRIMARY KEY,
    goods_data TEXT NOT NULL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_generation_history_created_at ON generation_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_agent_name ON prompt_templates(agent_name);
```

**Step 3: 验证表创建**

点击左侧菜单 "Table Editor"
确认看到三个表: `generation_history`, `prompt_templates`, `goods_cache`

**Expected Output:** 三个表已创建

---

### Task 5: 本地测试新的数据库实现

**Files:**
- Create: `test_database_new.py`

**Step 1: 创建测试脚本**

创建 `test_database_new.py`:

```python
"""测试新数据库实现"""
import os
os.environ['DATABASE_URL'] = 'sqlite:///data/test_pdd.db'  # 本地测试用 SQLite

from database_new import Database
from models import PromptTemplate

def test_database():
    print("Testing new database implementation...")

    # 初始化数据库
    db = Database()
    print("✓ Database initialized")

    # 测试历史记录
    keywords = ["测试关键词"]
    result = {"test": "data"}
    row_id = db.save_history(keywords, 1, result)
    print(f"✓ Saved history with id: {row_id}")

    # 获取历史记录
    history = db.get_history(limit=1)
    assert len(history) > 0, "History should not be empty"
    print(f"✓ Retrieved {len(history)} history records")

    # 测试提示词模板
    templates = db.get_prompt_templates()
    assert len(templates) > 0, "Should have default templates"
    print(f"✓ Retrieved {len(templates)} prompt templates")

    # 测试商品缓存
    db.cache_goods("test_sign", {"name": "测试商品"})
    cached = db.get_cached_goods("test_sign")
    assert cached is not None, "Cached goods should exist"
    assert cached["name"] == "测试商品", "Cached data should match"
    print("✓ Goods cache working")

    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_database()
```

**Step 2: 运行测试**

运行: `python test_database_new.py`

Expected: 所有测试通过，输出 "✅ All tests passed!"

**Step 3: 清理测试文件**

```bash
rm data/test_pdd.db
```

**Step 4: Commit**

```bash
git add test_database_new.py
git commit -m "test: add database implementation test script"
```

---

### Task 6: 替换数据库导入

**Files:**
- Modify: `coordinator.py`

**Step 1: 查看当前导入**

运行: `grep -n "from database import" coordinator.py`

Expected: 找到导入语句

**Step 2: 替换导入语句**

将 `from database import Database` 改为:
```python
from database_new import Database
```

**Step 3: 验证修改**

运行: `grep "from database" coordinator.py`

Expected: 应显示 `from database_new import Database`

**Step 4: Commit**

```bash
git add coordinator.py
git commit -m "refactor: switch to new SQLAlchemy-based database"
```

---

### Task 7: 更新 .env.example

**Files:**
- Modify: `.env.example`

**Step 1: 添加 DATABASE_URL 变量**

在 `.env.example` 中添加:

```
# 数据库 (PostgreSQL for Streamlit Cloud deployment)
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
```

**Step 2: 验证修改**

运行: `cat .env.example`

Expected: 文件包含 DATABASE_URL 变量

**Step 3: Commit**

```bash
git add .env.example
git commit -m "docs: add DATABASE_URL to environment variables example"
```

---

### Task 8: 创建 Streamlit 配置文件

**Files:**
- Create: `.streamlit/config.toml`

**Step 1: 创建配置目录**

运行: `mkdir -p .streamlit`

**Step 2: 创建配置文件**

创建 `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#667eea"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[client]
showErrorDetails = false
maxUploadSize = 200

[logger]
level = "info"
```

**Step 3: Commit**

```bash
git add .streamlit/config.toml
git commit -m "feat: add Streamlit configuration"
```

---

### Task 9: 创建 README 部署说明

**Files:**
- Modify: `README.md`

**Step 1: 在 README.md 末尾添加部署章节**

```markdown
## 部署到 Streamlit Cloud

### 前置准备

1. 注册 [Supabase](https://supabase.com) 并创建项目
2. 在 Supabase SQL Editor 中运行以下 SQL 创建表：

\`\`\`sql
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
\`\`\`

3. 获取 Supabase DATABASE_URL (Project Settings → Database → Connection string)

### 部署步骤

1. 注册 [Streamlit Cloud](https://streamlit.io/cloud)
2. 点击 "New app"
3. 连接你的 GitHub 仓库
4. 选择主分支
5. Main file path: `frontend.py`
6. 在 "Secrets" 中添加以下环境变量：

\`\`\`
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
PDD_CLIENT_ID=your_client_id_here
PDD_CLIENT_SECRET=your_client_secret_here
PDD_PID=your_pid_here
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
\`\`\`

7. 点击 "Deploy"

### 部署后

- 应用会在每次 push 到主分支时自动重新部署
- 可在 Streamlit Cloud 查看应用日志
- 免费版限制: 每月 750 小时运行时间
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add Streamlit Cloud deployment instructions"
```

---

### Task 10: 清理和最终验证

**Step 1: 本地验证应用运行**

运行: `streamlit run frontend.py`

Expected: 应用正常启动，无错误

**Step 2: 运行测试脚本验证数据库**

运行: `python test_database_new.py`

Expected: 测试通过

**Step 3: 清理测试文件**

```bash
rm test_database_new.py
rm -rf data/test_pdd.db __pycache__ .streamlit/__pycache__
```

**Step 4: 最终提交**

```bash
git add -A
git commit -m "chore: clean up test files and prepare for deployment"
```

**Step 5: 推送到 GitHub**

```bash
git push origin master
```

---

### Task 11: 部署到 Streamlit Cloud

**Step 1: 访问 Streamlit Cloud**

访问: https://streamlit.io/cloud
登录 GitHub 账号

**Step 2: 创建新应用**

1. 点击 "New app"
2. 选择仓库: `pdd-promotion-automation`
3. 选择分支: `master`
4. Main file path: `frontend.py`
5. 点击 "Advanced settings"
6. 在 "Secrets" 中添加环境变量:

```
LLM_API_KEY=your_value
LLM_BASE_URL=your_value
LLM_MODEL=your_value
PDD_CLIENT_ID=your_value
PDD_CLIENT_SECRET=your_value
PDD_PID=your_value
DATABASE_URL=your_supabase_url
```

7. 点击 "Save" 然后 "Deploy"

**Step 3: 等待部署完成**

Expected: 看到 "Your app is live!" 消息

**Step 4: 访问应用**

点击提供的 URL 访问应用

**Expected:** 应用正常加载，可以使用

---

## 验收标准

- [ ] Supabase 项目创建，三个表已创建
- [ ] 新数据库实现 `database_new.py` 已创建并测试通过
- [ ] `coordinator.py` 使用新的数据库导入
- [ ] `requirements.txt` 包含 SQLAlchemy 和 psycopg2-binary
- [ ] `.env.example` 包含 DATABASE_URL
- [ ] README 包含部署说明
- [ ] 代码已推送到 GitHub
- [ ] 应用已部署到 Streamlit Cloud
- [ ] 可以通过公网 URL 访问应用
- [ ] 历史记录功能正常工作（数据持久化）
