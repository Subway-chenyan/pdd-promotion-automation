"""
AI-2: Product Operator - 操作员（带完整追踪）
"""
from typing import Dict, Any, List
from langsmith import traceable
from .base_agent import BaseAgent
from skills.pdd_api_skill import PddApiSkill
from models import GoodsInfo, EnrichedGoods


class ProductOperator(BaseAgent):
    """操作员：获取详情、生成推广链接"""

    def __init__(
        self,
        pdd_skill: PddApiSkill,
        system_prompt: str = "",
        user_prompt_template: str = "",
    ):
        # 默认提示词
        if not system_prompt:
            system_prompt = """你是商品信息处理专员，负责获取商品详情并生成推广链接。

你的工作：
1. 获取商品的详细信息（描述、图片、SKU等）
2. 生成推广短链接
3. 整理商品的核心卖点信息

请确保信息准确、完整。"""

        if not user_prompt_template:
            user_prompt_template = """处理以下商品列表，获取详情和推广链接：

{goods_list}

返回整理后的商品信息。"""

        super().__init__(system_prompt=system_prompt, user_prompt_template=user_prompt_template)
        self.pdd_skill = pdd_skill

    @traceable(name="agent_operator_execute")
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行操作员任务

        Args:
            context: 包含 goods_list (List[GoodsInfo])

        Returns:
            包含 enriched_goods (List[EnrichedGoods])
        """
        goods_list = context.get("goods_list", [])

        if not goods_list:
            return {"enriched_goods": []}

        enriched_goods = []

        for goods in goods_list:
            try:
                # 并行获取详情和推广链接
                import asyncio

                detail_task = self.pdd_skill.get_goods_detail(goods.goods_sign)
                url_task = self.pdd_skill.generate_promotion_url(goods.goods_sign)

                detail, promotion = await asyncio.gather(detail_task, url_task)

                enriched = EnrichedGoods(
                    info=goods,
                    detail=detail,
                    promotion=promotion,
                )
                enriched_goods.append(enriched)

            except Exception as e:
                # 单个商品失败不影响其他商品
                print(f"处理商品 '{goods.goods_name}' 失败: {str(e)}")
                # 仍然添加基本信息，只是没有详情
                enriched = EnrichedGoods(info=goods)
                enriched_goods.append(enriched)
                continue

        return {"enriched_goods": enriched_goods}

    # 辅助方法

    def _extract_highlights(self, enriched_goods: EnrichedGoods) -> List[str]:
        """提取商品亮点"""
        highlights = []

        if not enriched_goods.detail:
            return highlights

        detail = enriched_goods.detail

        # 优惠券信息
        if detail.coupon_discount > 0:
            highlights.append(f"领券立减 ¥{detail.coupon_discount / 100:.0f}")

        # 百亿补贴
        if 7 in detail.activity_tags:
            highlights.append("百亿补贴，超值优惠")

        # 品牌商品
        if detail.brand_name:
            highlights.append(f"{detail.brand_name} 品牌正品")

        # 高销量
        try:
            sales = int(detail.sold_quantity)
            if sales >= 10000:
                highlights.append(f"已售{sales / 10000:.1f}万+件")
        except:
            pass

        # 旗舰店
        if detail.merchant_type == 3:
            highlights.append("官方旗舰店")

        return highlights

    def _format_enriched_goods(self, enriched_goods: List[EnrichedGoods]) -> str:
        """格式化增强商品信息供LLM使用"""
        if not enriched_goods:
            return "没有商品信息"

        lines = []
        for i, eg in enumerate(enriched_goods, 1):
            goods = eg.info
            detail = eg.detail

            lines.append(f"""
{i}. {goods.goods_name}
   价格: ¥{goods.price_yuan}
   优惠券: ¥{goods.coupon_yuan}
   券后价: ¥{goods.final_price_yuan}
   销量: {goods.sales}
   佣金: {goods.commission_percent}%
   店铺: {goods.mall_name}
""")

            if detail:
                if detail.brand_name:
                    lines.append(f"   品牌: {detail.brand_name}")
                if detail.goods_desc:
                    desc = detail.goods_desc[:100] + "..." if len(detail.goods_desc) > 100 else detail.goods_desc
                    lines.append(f"   描述: {desc}")

            highlights = self._extract_highlights(eg)
            if highlights:
                lines.append(f"   亮点: {', '.join(highlights)}")

        return "\n".join(lines)
