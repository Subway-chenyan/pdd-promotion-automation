# LangChain 调试指南

## 快速开始

```bash
# 基础调试（打印输出）
python debug_agents.py --mode basic

# LangChain 内置调试
python debug_agents.py --mode langchain

# LangSmith 追踪（需要 API Key）
python debug_agents.py --mode langsmith
```

## 调试模式对比

| 模式 | 环境变量 | 优点 | 缺点 |
|------|----------|------|------|
| **basic** | 无 | 无需配置，快速查看 | 信息有限 |
| **langchain** | `LANGCHAIN_DEBUG=true` | 详细内部日志 | 输出较多 |
| **langsmith** | `LANGCHAIN_TRACING_V2=true` | 完整可视化追踪 | 需要 API Key |

## 方法 1: 基础调试模式

无需任何配置，直接打印每个步骤：

```bash
python debug_agents.py --mode basic --test full
```

## 方法 2: LangChain DEBUG 模式

启用 LangChain 内置调试，查看所有内部调用：

```bash
# Windows PowerShell
$env:LANGCHAIN_DEBUG = "true"
python debug_agents.py --mode langchain

# Windows CMD
set LANGCHAIN_DEBUG=true
python debug_agents.py --mode langchain

# Linux/Mac
export LANGCHAIN_DEBUG=true
python debug_agents.py --mode langchain
```

**输出示例：**
```
[DEBUG] > Entering Chain.run with input: {'keywords': ['蓝牙耳机'], 'count': 3}
[DEBUG] > Chain start completed
[DEBUG] > LLM start: prompt=...
[DEBUG] > LLM end: response=...
```

## 方法 3: LangSmith 追踪（推荐）

完整可视化追踪所有 Agent 调用。

### 3.1 获取 API Key

1. 访问 https://smith.langchain.com/
2. 注册/登录账号
3. 创建 API Key

### 3.2 配置环境变量

在 `.env` 文件中添加：

```bash
# LangSmith 追踪
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=pdd-promotion-debug
```

### 3.3 运行调试

```bash
python debug_agents.py --mode langsmith --test full
```

### 3.4 查看追踪结果

访问 https://smith.langchain.com/ 查看完整追踪：

- ✅ 每个 Agent 的输入/输出
- ✅ LLM 调用的提示词和返回
- ✅ Token 使用统计
- ✅ 耗时分析
- ✅ 错误追踪

## 方法 4: 代码中启用详细输出

在 Agent 代码中添加 `verbose=True`：

```python
from langchain.globals import set_verbose

# 启用全局详细输出
set_verbose(True)

# 或者在 Chain 上
chain = prompt | llm | parser
chain.invoke(input, config={"verbose": True})
```

## 方法 5: 自定义回调函数

创建自己的调试回调：

```python
from langchain.callbacks import BaseCallbackHandler

class MyDebugCallback(BaseCallbackHandler):
    def on_llm_start(self, prompts, **kwargs):
        print(f"LLM 输入: {prompts}")

    def on_llm_end(self, response, **kwargs):
        print(f"LLM 输出: {response}")

# 使用
callback = MyDebugCallback()
result = await chain.ainvoke(
    input,
    config={"callbacks": [callback]}
)
```

## 常见问题排查

### 问题 1: Agent 没有输出

**可能原因：**
- LLM API 配置错误
- 提示词格式问题

**调试方法：**
```bash
# 启用详细日志
python debug_agents.py --mode langchain --test selector
```

### 问题 2: 提示词不符合预期

**调试方法：**
```python
# 打印实际发送给 LLM 的提示词
selector = ProductSelector(pdd_skill=pdd)
print("System Prompt:", selector.system_prompt)
print("User Prompt:", selector.user_prompt_template)
```

### 问题 3: 追踪没有上传到 LangSmith

**检查项：**
1. `LANGCHAIN_API_KEY` 是否正确
2. 网络连接是否正常
3. `LANGCHAIN_TRACING_V2=true` 是否设置

```bash
# 验证环境变量
python -c "import os; print(os.getenv('LANGCHAIN_TRACING_V2'))"
```

## 调试技巧

### 1. 单独测试每个 Agent

```bash
# 只测试选品经理
python debug_agents.py --test selector

# 只测试文案师
python debug_agents.py --test copywriter
```

### 2. 查看中间结果

在代码中添加打印：

```python
async def execute(self, context):
    # 打印输入
    print(f"[DEBUG] 输入: {context}")

    # 执行逻辑
    result = await self._do_something(context)

    # 打印输出
    print(f"[DEBUG] 输出: {result}")

    return result
```

### 3. 使用断点调试

```python
import pdb

async def execute(self, context):
    pdb.set_trace()  # 设置断点
    # ... 执行逻辑
```

## 环境变量速查表

```bash
# LangChain 调试
LANGCHAIN_DEBUG=true                    # 启用内置调试
LANGCHAIN_VERBOSE=true                  # 详细输出

# LangSmith 追踪
LANGCHAIN_TRACING_V2=true               # 启用追踪 v2
LANGCHAIN_API_KEY=lsv2_...              # LangSmith API Key
LANGCHAIN_PROJECT=my-project            # 项目名称

# 拼多多 API（本项目）
PDD_CLIENT_ID=...                       # 拼多多 Client ID
PDD_CLIENT_SECRET=...                   # 拼多多 Client Secret
PDD_PID=...                             # 推广位 ID

# LLM 配置
LLM_API_KEY=...                         # LLM API Key
LLM_BASE_URL=...                        # LLM Base URL
LLM_MODEL=...                           # LLM 模型名称
```

## 推荐调试流程

1. **快速验证** → `python debug_agents.py --mode basic`
2. **深入分析** → `python debug_agents.py --mode langchain`
3. **完整追踪** → `python debug_agents.py --mode langsmith`

按需选择，逐步深入！
