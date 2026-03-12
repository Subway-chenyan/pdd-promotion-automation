"""
Base Agent（带完整追踪）
"""
import sys
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langsmith import traceable


def _get_llm_config():
    """获取 LLM 配置（懒加载，避免模块级导入问题）"""
    # 确保项目根目录在 sys.path 中
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from config import get_llm_config
    return get_llm_config()


class BaseAgent(ABC):
    """Agent基类（带完整追踪）"""

    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        system_prompt: str = "",
        user_prompt_template: str = "",
    ):
        if llm is None:
            # 创建默认LLM - 使用统一配置加载器（懒加载）
            llm_config = _get_llm_config()

            llm = ChatOpenAI(
                api_key=llm_config["api_key"],
                base_url=llm_config["base_url"],
                model=llm_config["model"],
                temperature=0.7,
            )

        self.llm = llm
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self._build_chain()

    def _build_chain(self):
        """构建处理链"""
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", self.user_prompt_template),
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

    def update_prompts(self, system_prompt: str, user_prompt_template: str):
        """更新提示词"""
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self._build_chain()

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Agent任务

        Args:
            context: 上下文数据

        Returns:
            处理结果
        """
        pass

    @traceable
    async def _invoke_llm(self, **kwargs) -> str:
        """
        调用LLM（带追踪）

        这个方法会自动被 LangSmith 追踪，显示：
        - 输入的提示词
        - LLM 的返回
        - Token 使用情况
        - 耗时
        """
        try:
            result = await self.chain.ainvoke(kwargs)
            return result
        except Exception as e:
            # 降级处理：返回错误信息
            return f"LLM调用失败: {str(e)}"
