"""
数据模型定义
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class GoodsInfo(BaseModel):
    """商品基本信息"""
    goods_id: str
    goods_sign: str
    goods_name: str
    min_group_price: int = Field(description="最低价格(分)")
    coupon_discount: int = Field(default=0, description="优惠券(分)")
    promotion_amount: int = Field(default=0, description="佣金(分)")
    commission_rate: int = Field(default=0, description="佣金比例(万分之几)")
    sales: str = Field(default="", description="销量(可能是'2.2万+'格式)")
    mall_name: str = Field(default="")
    goods_thumbnail_url: str = Field(default="")
    cat_id: int = Field(default=0)

    @property
    def price_yuan(self) -> str:
        """价格(元)"""
        return f"{self.min_group_price / 100:.2f}"

    @property
    def coupon_yuan(self) -> str:
        """优惠券(元)"""
        return f"{self.coupon_discount / 100:.2f}"

    @property
    def final_price_yuan(self) -> str:
        """券后价(元)"""
        return f"{(self.min_group_price - self.coupon_discount) / 100:.2f}"

    @property
    def commission_percent(self) -> str:
        """佣金比例(%)"""
        return f"{self.commission_rate / 100:.2f}"


class GoodsDetail(BaseModel):
    """商品详情"""
    goods_sign: str
    goods_name: str
    goods_desc: Optional[str] = None
    min_group_price: int
    max_group_price: int
    coupon_discount: int = 0
    commission_rate: int = 0
    commission_amount: int = 0
    sold_quantity: str = "0"
    brand_name: Optional[str] = None
    mall_name: str
    merchant_type: int = 0
    goods_image_urls: List[str] = Field(default_factory=list)
    goods_gallery_urls: List[str] = Field(default_factory=list)
    sku_list: List[dict] = Field(default_factory=list)
    activity_tags: List[int] = Field(default_factory=list)


class PromotionUrl(BaseModel):
    """推广链接"""
    goods_sign: str
    url: str = Field(default="")
    short_url: str = Field(default="")
    mobile_url: str = Field(default="")
    we_app_info: Optional[dict] = None
    weixin_code: str = Field(default="")
    weixin_short_link: str = Field(default="")


class EnrichedGoods(BaseModel):
    """增强后的商品信息（含详情和链接）"""
    info: GoodsInfo
    detail: Optional[GoodsDetail] = None
    promotion: Optional[PromotionUrl] = None


class CopyResult(BaseModel):
    """文案生成结果"""
    goods_sign: str
    goods_name: str
    style: str
    copy_text: str
    short_url: str
    price: str
    coupon: str
    final_price: str
    sales: str
    image_url: str = ""  # 商品图片URL
    thumbnail_url: str = ""  # 缩略图URL


class GenerationRequest(BaseModel):
    """生成请求"""
    keywords: List[str]
    count: int
    prompts: Optional[dict] = None
    style_hint: str = "自动生成"


class GenerationResult(BaseModel):
    """生成结果"""
    request: GenerationRequest
    results: List[CopyResult]
    created_at: datetime = Field(default_factory=datetime.now)


class PromptTemplate(BaseModel):
    """提示词模板"""
    id: Optional[int] = None
    agent_name: str  # 'selector', 'operator', 'copywriter'
    template_name: str
    system_prompt: str
    user_prompt_template: str
    is_default: bool = False
    created_at: Optional[datetime] = None
