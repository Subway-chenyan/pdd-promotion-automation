# 拼多多商品推广自动化系统 - 设计文档

**日期:** 2025-03-11
**状态:** 已批准
**版本:** 1.0

---

## 1. 概述

### 1.1 项目目标

构建一个基于 LangChain 的拼多多商品推广自动化系统，通过三个 AI Agent 协作完成选品、获取详情、生成文案的全流程。

### 1.2 核心功能

- **AI-1 选品经理**: 根据关键词搜索商品，支持价格/销量/佣金筛选
- **AI-2 操作员**: 获取商品详情，生成推广短链
- **AI-3 文案师**: 生成多种风格的推广文案，支持前端自定义提示词

### 1.3 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| AI框架 | LangChain (ChatPromptTemplate, LCEL) |
| 前端 | Streamlit |
| 存储 | SQLite |
| 配置 | .env (python-dotenv) |

---

## 2. 系统架构

### 2.1 目录结构

```
langchain_pdd/
├── .env                      # LLM 配置（API key, base_url等）
├── .env.example              # 环境变量模板
├── config/
│   └── prompts.yaml          # 默认提示词模板
├── data/
│   └── pdd.db                # SQLite 本地存储
├── skills/
│   ├── __init__.py
│   └── pdd_api_skill.py      # 拼多多API封装（参考pdd-api.md）
├── agents/
│   ├── __init__.py
│   ├── base_agent.py         # Agent基类
│   ├── product_selector.py   # AI-1 选品经理
│   ├── product_operator.py   # AI-2 操作员
│   └── copywriter.py         # AI-3 文案师
├── coordinator.py            # 主协调器（顺序调用）
├── frontend.py               # Streamlit 前端
├── database.py               # 数据库操作
├── models.py                 # 数据模型
├── requirements.txt
└── README.md
```

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit 前端                           │
│  ┌────────────┐ ┌────────────┐ ┌──────────────────────────┐ │
│  │ 关键词输入 │ │ 选品个数   │ │ 提示词编辑器（可折叠）    │ │
│  └─────┬──────┘ └─────┬──────┘ └──────────┬───────────────┘ │
│        └────────────────┴───────────────────┴───────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    主协调器 (Coordinator)                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐  │
│  │ AI-1    │───▶│ AI-2     │───▶│ AI-3                 │  │
│  │ 选品经理 │    │ 操作员    │    │ 文案师               │  │
│  └──────────┘    └──────────┘    └──────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    SQLite 本地存储                           │
│  • 历史记录  • 提示词模板  • 商品缓存                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 组件设计

### 3.1 PDD API Skill

```python
# skills/pdd_api_skill.py
class PddApiSkill:
    """拼多多API封装 - 参考pdd-api.md"""

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.gateway_url = "https://gw-api.pinduoduo.com/api/router"

    def search_goods(self, keyword: str, count: int, **filters) -> List[GoodsInfo]:
        """
        搜索商品 - 支持价格/销量/佣金筛选

        Args:
            keyword: 搜索关键词
            count: 返回数量
            **filters: 筛选条件 (min_price, max_price, sort_type等)

        Returns:
            商品信息列表
        """

    def get_goods_detail(self, goods_sign: str) -> GoodsDetail:
        """获取商品详情"""

    def generate_promotion_url(self, goods_sign: str, pid: str) -> PromotionUrl:
        """
        生成推广链接 - 包含短链

        Returns:
            包含 short_url, weixin_short_link 等字段
        """

    # 工具方法
    @staticmethod
    def fen_to_yuan(fen: int) -> str:
        """分转元"""

    @staticmethod
    def calculate_commission(price: int, rate: int, coupon: int) -> int:
        """计算佣金金额"""
```

### 3.2 Base Agent

```python
# agents/base_agent.py
from abc import ABC, abstractmethod
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

class BaseAgent(ABC):
    """Agent基类"""

    def __init__(self, llm, system_prompt: str, user_prompt_template: str):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt_template)
        ])

    @abstractmethod
    async def execute(self, context: dict) -> dict:
        """
        执行Agent任务

        Args:
            context: 上下文数据

        Returns:
            处理结果
        """
        pass
```

### 3.3 AI-1 选品经理

```python
# agents/product_selector.py
class ProductSelector(BaseAgent):
    """选品经理：搜索、筛选、排序商品"""

    def __init__(self, llm, pdd_skill: PddApiSkill, prompts: dict):
        self.pdd_skill = pdd_skill
        super().__init__(
            llm,
            prompts.get("selector_system", "你是一个专业的商品选品经理..."),
            prompts.get("selector_user", "根据以下要求选品：\n关键词: {keywords}\n数量: {count}")
        )

    async def execute(self, context: dict) -> dict:
        keywords = context["keywords"]  # List[str]
        count = context["count"]         # int

        # 调用PDD API搜索
        all_goods = []
        for keyword in keywords:
            goods = await self.pdd_skill.search_goods(
                keyword=keyword,
                count=count,
                sort_type=6  # 按销量降序
            )
            all_goods.extend(goods)

        # LLM筛选和排序（可选）
        # ...

        return {"goods_list": all_goods}
```

### 3.4 AI-2 操作员

```python
# agents/product_operator.py
class ProductOperator(BaseAgent):
    """操作员：获取详情、生成推广链接"""

    def __init__(self, llm, pdd_skill: PddApiSkill, prompts: dict):
        self.pdd_skill = pdd_skill
        super().__init__(
            llm,
            prompts.get("operator_system", "你是商品信息处理专员..."),
            prompts.get("operator_user", "获取以下商品的详情和推广链接...")
        )

    async def execute(self, context: dict) -> dict:
        goods_list = context["goods_list"]
        pid = context.get("pid", "")  # 推广位ID

        enriched_goods = []
        for goods in goods_list:
            # 获取详情
            detail = await self.pdd_skill.get_goods_detail(goods["goods_sign"])
            # 生成推广链接
            url_info = await self.pdd_skill.generate_promotion_url(
                goods["goods_sign"], pid
            )
            enriched_goods.append({
                **goods,
                "detail": detail,
                "short_url": url_info["short_url"]
            })

        return {"enriched_goods": enriched_goods}
```

### 3.5 AI-3 文案师

```python
# agents/copywriter.py
class Copywriter(BaseAgent):
    """文案师：生成推广文案，支持动态风格"""

    def __init__(self, llm, prompts: dict):
        super().__init__(
            llm,
            prompts.get("copywriter_system", "你是一位资深的电商文案策划..."),
            prompts.get("copywriter_user", """
为以下商品生成推广文案：

商品信息：
- 名称: {name}
- 价格: {price}
- 优惠券: {coupon}
- 亮点: {highlights}

风格要求: {style}
""")
        )

    async def execute(self, context: dict) -> dict:
        enriched_goods = context["enriched_goods"]
        style_hint = context.get("style_hint", "自动生成")

        results = []
        for goods in enriched_goods:
            # 动态生成风格（如果需要）
            if style_hint == "自动生成":
                style = await self._detect_style(goods)
            else:
                style = style_hint

            # 生成文案
            chain = self.prompt | self.llm
            response = await chain.ainvoke({
                "name": goods["name"],
                "price": goods["price"],
                "coupon": goods["coupon"],
                "highlights": goods["highlights"],
                "style": style
            })

            results.append({
                **goods,
                "copy": response.content,
                "style": style
            })

        return {"final_results": results}

    async def _detect_style(self, goods: dict) -> str:
        """根据商品类型自动检测风格"""
        # 使用LLM判断最合适的风格
        # ...
        pass
```

---

## 4. 数据流设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Streamlit 前端                               │
│  输入: keywords, count, custom_prompts                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Coordinator 主协调器                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  AI-1         │      │  AI-2         │      │  AI-3         │
│  选品经理     │ ───▶ │  操作员       │ ───▶ │  文案师       │
│               │      │               │      │               │
│ INPUT:        │      │ INPUT:        │      │ INPUT:        │
│ - keywords    │      │ - goods_list  │      │ - goods_data  │
│ - count       │      │               │      │ - style_hint  │
│               │      │ OUTPUT:       │      │               │
│ OUTPUT:       │      │ - enriched    │      │ OUTPUT:       │
│ - goods_list  │      │   goods_data  │      │ - final_copy  │
└───────────────┘      └───────────────┘      └───────────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SQLite 本地存储                                 │
│  • 保存历史记录   • 保存自定义提示词   • 商品缓存（可选）             │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Streamlit 输出                                  │
│  显示: 商品信息 + 推广文案 + 短链接                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. 错误处理策略

### 5.1 分层错误处理

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: PDD API 层                                          │
│   • 网络重试 (3次)                                           │
│   • 限流处理 (50次/分钟)                                     │
│   • 签名验证失败 → 提示检查配置                               │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Agent 层                                            │
│   • LLM 调用失败 → 降级到规则引擎                            │
│   • 解析失败 → 返回原始数据 + 错误提示                       │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: 协调器层                                            │
│   • 某个 Agent 失败 → 继续执行后续流程                        │
│   • 全部失败 → 友好错误消息                                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: 前端层                                              │
│   • 异常捕获 + 友好提示                                      │
│   • 进度条显示                                               │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 错误码定义

| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| PDD_001 | API调用失败 | 重试3次，失败则跳过该商品 |
| PDD_002 | 签名错误 | 提示检查配置 |
| LLM_001 | LLM调用失败 | 降级到模板生成 |
| LLM_002 | 解析失败 | 返回原始LLM输出 |

---

## 6. 数据库设计

### 6.1 Schema

```sql
-- 历史记录表
CREATE TABLE generation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keywords TEXT,              -- 输入的关键词 (JSON数组)
    goods_count INTEGER,        -- 选品数量
    result_json TEXT,           -- 结果JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 提示词模板表
CREATE TABLE prompt_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT,            -- 'selector', 'operator', 'copywriter'
    template_name TEXT,         -- 模板名称
    system_prompt TEXT,         -- 系统提示词
    user_prompt_template TEXT,  -- 用户提示词模板
    is_default BOOLEAN,         -- 是否默认
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 商品缓存表（可选）
CREATE TABLE goods_cache (
    goods_sign TEXT PRIMARY KEY,
    goods_data TEXT,            -- 商品详情JSON
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6.2 初始数据

```sql
-- 默认提示词模板
INSERT INTO prompt_templates (agent_name, template_name, system_prompt, user_prompt_template, is_default) VALUES
('selector', '默认选品', '你是一个专业的商品选品经理，擅长从拼多多平台筛选高性价比商品。', '根据以下要求选品：\n关键词: {keywords}\n数量: {count}', 1),
('operator', '默认操作员', '你是商品信息处理专员，负责获取商品详情并生成推广链接。', '处理以下商品列表', 1),
('copywriter', '默认文案师', '你是一位资深的电商文案策划，擅长创作吸引人的推广文案。', '为以下商品生成推广文案', 1);
```

---

## 7. 前端设计

### 7.1 页面布局

```
┌─────────────────────────────────────────────────────────────────┐
│  🛒 拼多多商品推广自动化系统                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  输入区域                                                    ││
│  │  ┌─────────────────────────────────────────────────────────┐││
│  │  │ 关键词 (每行一个):                                       │││
│  │  │ ┌─────────────────────────────────────────────────────┐│││
│  │  │ │ 蓝牙耳机                                              │││
│  │  │ │ 充电宝                                                │││
│  │  │ │ 数据线                                                │││
│  │  │ └─────────────────────────────────────────────────────┘│││
│  │  │                                                          │││
│  │  │ 每个关键词选品个数: [3]                                  │││
│  │  │                                                          │││
│  │  │ [生成推广文案] 按钮                                      │││
│  │  └─────────────────────────────────────────────────────────┘││
│  │                                                              ││
│  │  ┌─────────────────────┐ ┌─────────────────────────────────┐││
│  │  │ ▶ 提示词编辑器      │ │ 📊 历史记录                     │││
│  │  │ (可折叠展开)        │ │ • 蓝牙耳机 - 2分钟前           │││
│  │  │                     │ │ • 充电宝 - 5分钟前             │││
│  │  │ AI-1 选品经理:      │ │                                │││
│  │  │ [可编辑提示词...]   │ │                                │││
│  │  │                     │ │                                │││
│  │  │ AI-2 操作员:        │ │                                │││
│  │  │ [可编辑提示词...]   │ │                                │││
│  │  │                     │ │                                │││
│  │  │ AI-3 文案师:        │ │                                │││
│  │  │ [可编辑提示词...]   │ │                                │││
│  │  └─────────────────────┘ └─────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  输出区域                                                    ││
│  │  ┌─────────────────────────────────────────────────────────┐││
│  │  │ 🔥 蓝牙耳机                                              │││
│  │  │ ─────────────────────────────────────────────────────   │││
│  │  │ 商品: Sony WH-1000XM5 头戴式降噪耳机                      │││
│  │  │ 价格: ¥1999 | 销量: 10万+ | 佣金: 15%                    │││
│  │  │                                                          │││
│  │  │ 📝 推广文案:                                             │││
│  │  │ ┌────────────────────────────────────────────────────┐  │││
│  │  │ │ 🎧 音质王者回归！Sony WH-1000XM5震撼上市！           │  │││
│  │  │ │ ⚡ 30小时超长续航，行业领先降噪技术                   │  │││
│  │  │ │ 💥 限时特惠，立省500元！                             │  │││
│  │  │ │ 👉 [短链接]                                          │  │││
│  │  │ └────────────────────────────────────────────────────┘  │││
│  │  │                                                          │││
│  │  │ [复制文案] [复制链接]                                    │││
│  │  └─────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 交互流程

1. 用户输入关键词（每行一个）
2. 选择每个关键词的选品数量
3. （可选）展开提示词编辑器，自定义各Agent的提示词
4. 点击"生成推广文案"
5. 系统显示进度条
6. 输出结果：商品信息 + 推广文案 + 短链接
7. 支持复制文案、复制链接

---

## 8. 环境配置

### 8.1 .env 文件

```bash
# LLM 配置
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=gpt-4o-mini

# 拼多多 API 配置
PDD_CLIENT_ID=5b0526d2772944eb988ed13a7c5fcc9e
PDD_CLIENT_SECRET=abe6000acb95ace679578392afe3d05653a5c275
PDD_PID=44136818_314571462

# 数据库
DB_PATH=data/pdd.db
```

### 8.2 requirements.txt

```
langchain>=0.3.0
langchain-openai>=0.2.0
streamlit>=1.40.0
python-dotenv>=1.0.0
httpx>=0.28.0
aiohttp>=3.11.0
pydantic>=2.10.0
```

---

## 9. 实现计划

### 9.1 开发阶段

1. **阶段1: 基础设施**
   - 项目初始化
   - PDD API Skill 封装
   - 数据库初始化

2. **阶段2: Agent 实现**
   - Base Agent
   - AI-1 选品经理
   - AI-2 操作员
   - AI-3 文案师

3. **阶段3: 协调器**
   - 顺序调用逻辑
   - 错误处理

4. **阶段4: 前端**
   - Streamlit 界面
   - 提示词编辑器
   - 历史记录显示

5. **阶段5: 测试与优化**

### 9.2 验收标准

- [ ] 可以输入关键词并生成推广文案
- [ ] 输出包含商品信息、文案、短链接
- [ ] 前端可以编辑各Agent的提示词
- [ ] 历史记录可以查看
- [ ] 错误处理友好

---

## 10. 参考资料

- 拼多多开放平台: https://open.pinduoduo.com/
- LangChain 文档: https://docs.langchain.com/
- Streamlit 文档: https://docs.streamlit.io/
