"""
主协调器 - 顺序调用三个Agent（带完整追踪）
"""
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# 导入追踪相关模块
from langsmith import traceable

from skills.pdd_api_skill import PddApiSkill
from agents.product_selector import ProductSelector
from agents.product_operator import ProductOperator
from agents.copywriter import Copywriter
from database import Database
from models import CopyResult

load_dotenv()


class Coordinator:
    """主协调器：顺序调用三个AI Agent（带完整追踪）"""

    def __init__(
        self,
        custom_prompts: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        # 初始化PDD API Skill
        self.pdd_skill = PddApiSkill(
            client_id=os.getenv("PDD_CLIENT_ID", ""),
            client_secret=os.getenv("PDD_CLIENT_SECRET", ""),
            pid=os.getenv("PDD_PID", ""),
        )

        # 初始化三个Agent
        self.selector = ProductSelector(pdd_skill=self.pdd_skill)
        self.operator = ProductOperator(pdd_skill=self.pdd_skill)
        self.copywriter = Copywriter()

        # 应用自定义提示词
        if custom_prompts:
            self._apply_custom_prompts(custom_prompts)

        # 数据库
        self.db = Database(db_path=os.getenv("DB_PATH", "data/pdd.db"))

    def _apply_custom_prompts(self, custom_prompts: Dict[str, Dict[str, str]]):
        """应用自定义提示词"""
        if "selector" in custom_prompts:
            prompts = custom_prompts["selector"]
            self.selector.update_prompts(
                system_prompt=prompts.get("system", self.selector.system_prompt),
                user_prompt_template=prompts.get("user", self.selector.user_prompt_template),
            )

        if "operator" in custom_prompts:
            prompts = custom_prompts["operator"]
            self.operator.update_prompts(
                system_prompt=prompts.get("system", self.operator.system_prompt),
                user_prompt_template=prompts.get("user", self.operator.user_prompt_template),
            )

        if "copywriter" in custom_prompts:
            prompts = custom_prompts["copywriter"]
            self.copywriter.update_prompts(
                system_prompt=prompts.get("system", self.copywriter.system_prompt),
                user_prompt_template=prompts.get("user", self.copywriter.user_prompt_template),
            )

    @traceable(name="coordinator_process")
    async def process(
        self,
        keywords: List[str],
        count: int = 3,
        style_hint: str = "自动生成",
        sort_type: str = "sales",
        save_history: bool = True,
    ) -> List[CopyResult]:
        """
        处理完整的推广文案生成流程（带追踪）

        Args:
            keywords: 关键词列表
            count: 每个关键词选品数量
            style_hint: 文案风格提示
            sort_type: 排序方式 (sales/commission/price_asc/coupon/final_price)
            save_history: 是否保存历史记录

        Returns:
            文案生成结果列表
        """
        results = []

        try:
            # Step 1: AI-1 选品经理
            print(f"[STEP 1] AI-1 选品经理正在搜索商品...")
            selector_context = {"keywords": keywords, "count": count, "sort_type": sort_type}
            selector_output = await self._step_selector(selector_context)
            goods_list = selector_output.get("goods_list", [])
            print(f"[STEP 1] 找到 {len(goods_list)} 个商品")

            if not goods_list:
                return results

            # Step 2: AI-2 操作员
            print(f"[STEP 2] AI-2 操作员正在获取商品详情...")
            operator_context = {"goods_list": goods_list}
            operator_output = await self._step_operator(operator_context)
            enriched_goods = operator_output.get("enriched_goods", [])
            print(f"[STEP 2] 完成 {len(enriched_goods)} 个商品的详情获取")

            if not enriched_goods:
                return results

            # Step 3: AI-3 文案师
            print(f"[STEP 3] AI-3 文案师正在生成推广文案...")
            copywriter_context = {
                "enriched_goods": enriched_goods,
                "style_hint": style_hint,
            }
            copywriter_output = await self._step_copywriter(copywriter_context)
            results = copywriter_output.get("results", [])
            print(f"[STEP 3] 生成 {len(results)} 条推广文案")

            # 保存历史记录
            if save_history and results:
                result_data = [r.model_dump() for r in results]
                self.db.save_history(
                    keywords=keywords,
                    count=count,
                    result={"results": result_data, "style": style_hint, "sort_type": sort_type},
                )

        except Exception as e:
            print(f"[ERROR] 处理失败: {str(e)}")
            raise

        return results

    @traceable(name="step_selector")
    async def _step_selector(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1: 选品经理（带追踪）"""
        return await self.selector.execute(context)

    @traceable(name="step_operator")
    async def _step_operator(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: 操作员（带追踪）"""
        return await self.operator.execute(context)

    @traceable(name="step_copywriter")
    async def _step_copywriter(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: 文案师（带追踪）"""
        return await self.copywriter.execute(context)

    # 提示词管理

    def get_prompt_templates(self) -> Dict[str, List[Dict]]:
        """获取所有提示词模板"""
        templates = self.db.get_prompt_templates()
        result = {"selector": [], "operator": [], "copywriter": []}

        for t in templates:
            result[t.agent_name].append({
                "id": t.id,
                "name": t.template_name,
                "system": t.system_prompt,
                "user": t.user_prompt_template,
                "is_default": t.is_default,
            })

        return result

    def update_prompt_template(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        template_name: str = "自定义",
    ) -> int:
        """更新提示词模板"""
        from models import PromptTemplate

        template = PromptTemplate(
            agent_name=agent_name,
            template_name=template_name,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt,
            is_default=False,
        )

        return self.db.save_prompt_template(template)

    def get_history(self, limit: int = 20) -> List[Dict]:
        """获取历史记录"""
        return self.db.get_history(limit)

    # 静态方法

    @staticmethod
    def get_available_styles() -> Dict[str, str]:
        """获取可用的文案风格"""
        return Copywriter.get_available_styles(None)

    @staticmethod
    def get_available_sort_types() -> Dict[str, str]:
        """获取可用的排序方式"""
        return ProductSelector.get_sort_options()
