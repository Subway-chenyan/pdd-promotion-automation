"""
AI-3: Copywriter - 文案师（带完整追踪）
"""
from typing import Dict, Any, List
from langsmith import traceable
from .base_agent import BaseAgent
from models import EnrichedGoods, CopyResult
import re


class Copywriter(BaseAgent):
    """文案师：生成推广文案，支持动态风格"""

    # 风格定义
    STYLES = {
        "简洁": {
            "description": "直接明了，突出核心卖点",
            "template": "核心卖点为主，语言简洁有力",
        },
        "紧迫": {
            "description": "限时优惠，库存紧张",
            "template": "强调限时、限量、特价，制造紧迫感",
        },
        "专业": {
            "description": "突出技术参数和专业优势",
            "template": "详细说明产品特点和技术优势",
        },
        "生活": {
            "description": "使用场景，用户体验",
            "template": "描述使用场景，营造生活氛围",
        },
    }

    def __init__(
        self,
        system_prompt: str = "",
        user_prompt_template: str = "",
    ):
        # 默认提示词
        if not system_prompt:
            system_prompt = """你是一位资深的电商文案策划，擅长创作吸引人的推广文案。

你的文案风格包括：
1. 简洁直接：突出核心卖点，语言精炼
2. 紧迫感：限时优惠、库存紧张，催促下单
3. 专业风：产品参数、技术优势，建立信任
4. 生活化：使用场景、用户体验，引发共鸣

你的任务：
- 根据商品类型自动选择最合适的风格
- 在文案中适当使用emoji增加吸引力
- 控制在100字以内
- 包含：吸引人的标题、核心卖点(2-3个)、行动召唤"""

        if not user_prompt_template:
            user_prompt_template = """为以下商品生成推广文案：

商品名称: {name}
价格: ¥{price}
优惠券: ¥{coupon}
券后价: ¥{final_price}
佣金比例: {commission_rate}%
销量: {sales}
商品亮点: {highlights}
店铺: {mall_name}
品牌: {brand}

风格要求: {style}

请生成一段简洁有力的推广文案（100字以内），包含：
1. 吸引人的标题
2. 核心卖点（2-3个）
3. 行动召唤
4. 适当使用emoji

直接返回文案内容，不需要额外解释。"""

        super().__init__(system_prompt=system_prompt, user_prompt_template=user_prompt_template)

    @traceable(name="agent_copywriter_execute")
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行文案生成任务

        Args:
            context: 包含 enriched_goods (List[EnrichedGoods]), style_hint (str)

        Returns:
            包含 results (List[CopyResult])
        """
        enriched_goods = context.get("enriched_goods", [])
        style_hint = context.get("style_hint", "自动生成")

        if not enriched_goods:
            return {"results": []}

        results = []

        for eg in enriched_goods:
            try:
                # 确定风格
                if style_hint == "自动生成":
                    style = self._detect_style(eg)
                else:
                    style = style_hint

                # 准备参数
                params = self._prepare_params(eg, style)

                # 调用LLM生成文案
                copy_text = await self._invoke_llm(**params)

                # 清理文案（去除可能的markdown标记）
                copy_text = self._clean_copy(copy_text)

                # 获取短链接和图片
                short_url = ""
                if eg.promotion:
                    short_url = eg.promotion.short_url or eg.promotion.weixin_short_link or ""

                # 获取商品图片（优先详情图，否则用缩略图）
                image_url = eg.info.goods_thumbnail_url
                if eg.detail and eg.detail.goods_image_urls:
                    image_url = eg.detail.goods_image_urls[0]

                result = CopyResult(
                    goods_sign=eg.info.goods_sign,
                    goods_name=eg.info.goods_name,
                    style=style,
                    copy_text=copy_text,
                    short_url=short_url,
                    price=eg.info.price_yuan,
                    coupon=eg.info.coupon_yuan,
                    final_price=eg.info.final_price_yuan,
                    sales=str(eg.info.sales),
                    image_url=image_url,
                    thumbnail_url=eg.info.goods_thumbnail_url,
                )
                results.append(result)

            except Exception as e:
                # 降级：使用模板生成
                print(f"生成文案失败: {str(e)}，使用模板生成")
                result = self._generate_fallback_copy(eg, style_hint)
                results.append(result)

        return {"results": results}

    def _detect_style(self, enriched_goods: EnrichedGoods) -> str:
        """根据商品类型自动检测风格"""
        goods = enriched_goods.info
        detail = enriched_goods.detail

        # 基于规则的风格检测
        name_lower = goods.goods_name.lower()

        # 数码产品 -> 专业风
        if any(kw in name_lower for kw in ["耳机", "音响", "手机", "电脑", "平板", "相机", "键盘", "鼠标"]):
            return "专业"

        # 服饰美妆 -> 生活化
        if any(kw in name_lower for kw in ["衣服", "裙子", "化妆品", "护肤", "香水", "饰品"]):
            return "生活"

        # 食品 -> 简洁
        if any(kw in name_lower for kw in ["零食", "食品", "饮料", "茶叶", "酒"]):
            return "简洁"

        # 有大额优惠券 -> 紧迫感
        if goods.coupon_discount > 5000:  # 50元以上
            return "紧迫"

        # 默认简洁
        return "简洁"

    def _prepare_params(self, enriched_goods: EnrichedGoods, style: str) -> Dict[str, str]:
        """准备LLM调用参数"""
        goods = enriched_goods.info
        detail = enriched_goods.detail

        # 提取亮点
        highlights = []
        if goods.coupon_discount > 0:
            highlights.append(f"领券立减¥{goods.coupon_discount / 100:.0f}")
        if detail and detail.brand_name:
            highlights.append(f"{detail.brand_name}品牌")

        highlights_text = "、".join(highlights) if highlights else "性价比高"

        return {
            "name": goods.goods_name,
            "price": goods.price_yuan,
            "coupon": goods.coupon_yuan,
            "final_price": goods.final_price_yuan,
            "commission_rate": goods.commission_percent,
            "sales": str(goods.sales),
            "highlights": highlights_text,
            "mall_name": goods.mall_name,
            "brand": detail.brand_name if detail else "",
            "style": style,
        }

    def _clean_copy(self, copy: str) -> str:
        """清理文案，去除markdown标记"""
        # 去除可能的引号
        copy = copy.strip().strip('"').strip("'").strip("`")

        # 去除多余的换行
        copy = re.sub(r"\n+", "\n", copy)

        return copy.strip()

    def _generate_fallback_copy(self, enriched_goods: EnrichedGoods, style: str) -> CopyResult:
        """降级：使用模板生成文案"""
        goods = enriched_goods.info

        # 简单模板
        coupon_text = f"，领券立减¥{goods.coupon_discount / 100:.0f}" if goods.coupon_discount > 0 else ""

        templates = [
            f"🔥 {goods.goods_name}\n✨ 超值好物，不容错过{coupon_text}！\n💰 券后价¥{goods.final_price_yuan}\n👇 点击抢购",
            f"✨ {goods.goods_name}\n💥 限时特惠{coupon_text}\n📦 已售{goods.sales}件，速抢！\n👉 券后¥{goods.final_price_yuan}",
        ]

        import random
        copy = random.choice(templates)

        short_url = ""
        if enriched_goods.promotion:
            short_url = enriched_goods.promotion.short_url or ""

        # 获取商品图片
        image_url = goods.goods_thumbnail_url
        if enriched_goods.detail and enriched_goods.detail.goods_image_urls:
            image_url = enriched_goods.detail.goods_image_urls[0]

        return CopyResult(
            goods_sign=goods.goods_sign,
            goods_name=goods.goods_name,
            style=style or "简洁",
            copy_text=copy,
            short_url=short_url,
            price=goods.price_yuan,
            coupon=goods.coupon_yuan,
            final_price=goods.final_price_yuan,
            sales=str(goods.sales),
            image_url=image_url,
            thumbnail_url=goods.goods_thumbnail_url,
        )

    # 辅助方法

    def get_available_styles(self) -> Dict[str, str]:
        """获取可用风格列表"""
        return {name: info["description"] for name, info in self.STYLES.items()}
