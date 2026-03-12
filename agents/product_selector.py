"""
AI-1: Product Selector - 选品经理（带完整追踪）
"""
from typing import Dict, Any, List, Optional
from langsmith import traceable
from .base_agent import BaseAgent
from skills.pdd_api_skill import PddApiSkill
from models import GoodsInfo


class ProductSelector(BaseAgent):
    """选品经理：搜索、筛选、排序商品"""

    # 排序选项定义
    SORT_OPTIONS = {
        "sales": {
            "name": "销量优先",
            "description": "按销量降序，选择用户认可度高的商品",
            "sort_type": 6,  # 按销量降序
        },
        "commission": {
            "name": "佣金最高",
            "description": "按佣金比例降序，选择收益最高的商品",
            "sort_type": 2,  # 按佣金比例降序
        },
        "price_asc": {
            "name": "价格最低",
            "description": "按价格升序，选择最便宜的商品",
            "sort_type": 3,  # 按价格升序
        },
        "coupon": {
            "name": "优惠最大",
            "description": "按优惠券金额降序，选择优惠力度最大的商品",
            "sort_type": 8,  # 按优惠券金额降序
        },
        "final_price": {
            "name": "券后价最低",
            "description": "按券后价升序，选择最实惠的商品",
            "sort_type": 9,  # 按券后价升序
        },
    }

    def __init__(
        self,
        pdd_skill: PddApiSkill,
        system_prompt: str = "",
        user_prompt_template: str = "",
    ):
        # 默认提示词
        if not system_prompt:
            system_prompt = """你是一个专业的商品选品经理，擅长从拼多多平台筛选高性价比商品。

你的工作原则：
1. 优先选择有优惠券的商品
2. 根据用户选择的排序标准进行筛选
3. 关注店铺信誉，优先选择旗舰店和品牌店
4. 综合考虑性价比，不只是单一指标

请根据用户的关键词和排序要求，筛选出最合适的商品。"""

        if not user_prompt_template:
            user_prompt_template = """请根据以下要求筛选商品：

关键词: {keywords}
每个关键词选品数量: {count}
排序方式: {sort_type}

筛选标准:
- 有优惠券优先
- 店铺信誉好
- 根据{sort_type}排序

请直接返回筛选后的商品列表，不需要额外解释。"""

        super().__init__(system_prompt=system_prompt, user_prompt_template=user_prompt_template)
        self.pdd_skill = pdd_skill

    @traceable(name="agent_selector_execute")
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行选品任务

        Args:
            context: 包含 keywords (List[str]), count (int), sort_type (str, 可选)

        Returns:
            包含 goods_list (List[GoodsInfo])
        """
        keywords = context.get("keywords", [])
        count = context.get("count", 3)
        sort_type = context.get("sort_type", "sales")  # 默认按销量

        if not keywords:
            return {"goods_list": []}

        # 获取排序配置
        sort_config = self.SORT_OPTIONS.get(sort_type, self.SORT_OPTIONS["sales"])

        all_goods = []
        for keyword in keywords:
            try:
                # 调用PDD API搜索商品
                goods_list = await self.pdd_skill.search_goods(
                    keyword=keyword,
                    count=count,
                    sort_type=sort_config["sort_type"],
                    with_coupon=True,
                )
                all_goods.extend(goods_list)
            except Exception as e:
                # 单个关键词失败不影响其他关键词
                print(f"搜索 '{keyword}' 失败: {str(e)}")
                continue

        # 如果是优惠最大排序，进行二次筛选确保选出真正优惠最大的
        if sort_type == "coupon" and all_goods:
            all_goods = self._sort_by_coupon(all_goods)

        # 如果是价格最低排序，进行二次筛选确保选出最便宜的
        if sort_type == "price_asc" and all_goods:
            all_goods = self._sort_by_price(all_goods)

        # 如果是佣金最高排序，进行二次筛选确保选出佣金最高的
        if sort_type == "commission" and all_goods:
            all_goods = self._sort_by_commission(all_goods)

        # 每个关键词只返回指定数量
        result = self._limit_per_keyword(all_goods, keywords, count)

        return {
            "goods_list": result,
            "sort_type": sort_type,
            "sort_name": sort_config["name"],
        }

    def _sort_by_commission(self, goods_list: List[GoodsInfo]) -> List[GoodsInfo]:
        """按佣金比例排序（二次筛选）"""
        return sorted(
            goods_list,
            key=lambda x: (
                x.commission_rate,  # 佣金比例
                x.promotion_amount,  # 佣金金额
            ),
            reverse=True
        )

    def _sort_by_price(self, goods_list: List[GoodsInfo]) -> List[GoodsInfo]:
        """按券后价排序（二次筛选）"""
        return sorted(
            goods_list,
            key=lambda x: x.min_group_price - x.coupon_discount
        )

    def _sort_by_coupon(self, goods_list: List[GoodsInfo]) -> List[GoodsInfo]:
        """按优惠券金额排序（二次筛选）"""
        return sorted(
            goods_list,
            key=lambda x: x.coupon_discount,
            reverse=True
        )

    def _limit_per_keyword(self, goods_list: List[GoodsInfo], keywords: List[str], count: int) -> List[GoodsInfo]:
        """每个关键词只返回指定数量"""
        if not keywords:
            return goods_list[:count]

        # 按关键词分组
        from collections import defaultdict
        keyword_groups = defaultdict(list)
        for goods in goods_list:
            # 找到匹配的关键词
            for keyword in keywords:
                if keyword in goods.goods_name:
                    keyword_groups[keyword].append(goods)
                    break

        # 每个关键词取前N个
        result = []
        for keyword in keywords:
            result.extend(keyword_groups[keyword][:count])

        # 如果结果不足，补充其他商品
        if len(result) < count:
            for goods in goods_list:
                if goods not in result:
                    result.append(goods)
                    if len(result) >= count:
                        break

        return result

    # 辅助方法

    def _format_goods_for_llm(self, goods_list: List[GoodsInfo]) -> str:
        """格式化商品列表供LLM使用"""
        if not goods_list:
            return "没有找到商品"

        lines = []
        for i, goods in enumerate(goods_list, 1):
            lines.append(f"""
{i}. {goods.goods_name}
   价格: ¥{goods.price_yuan}
   优惠券: ¥{goods.coupon_yuan}
   券后价: ¥{goods.final_price_yuan}
   销量: {goods.sales}
   佣金: {goods.commission_percent}%
   店铺: {goods.mall_name}
""")
        return "\n".join(lines)

    @staticmethod
    def get_sort_options() -> Dict[str, str]:
        """获取所有排序选项"""
        return {
            key: value["name"]
            for key, value in ProductSelector.SORT_OPTIONS.items()
        }
