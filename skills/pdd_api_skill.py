"""
拼多多API封装 - Skill（带完整追踪）
参考: pdd-api.md
"""
import hashlib
import time
import json
from typing import List, Optional, Dict, Any
from models import GoodsInfo, GoodsDetail, PromotionUrl
import httpx
from langsmith import traceable


class PddApiSkill:
    """拼多多API技能封装"""

    def __init__(self, client_id: str, client_secret: str, pid: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.pid = pid
        self.gateway_url = "https://gw-api.pinduoduo.com/api/router"
        self._last_call_time = 0
        self._min_interval = 1.2  # 限流: 最大50次/分钟

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """生成签名"""
        # 按字母顺序排序
        sorted_keys = sorted(params.keys())
        sign_str = ""
        for key in sorted_keys:
            if key != "sign":
                sign_str += key + str(params[key])
        # 首尾拼接client_secret
        sign_str = self.client_secret + sign_str + self.client_secret
        # MD5加密并转大写
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

    @traceable(name="pdd_api_call")
    async def _call_api(self, api_type: str, data_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """调用API"""
        # 限流处理
        import asyncio
        current_time = time.time()
        elapsed = current_time - self._last_call_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_call_time = time.time()

        # 构建请求参数
        timestamp = str(int(time.time()))
        all_params = {
            "type": api_type,
            "client_id": self.client_id,
            "timestamp": timestamp,
            "data_type": "JSON",
        }
        if data_params:
            all_params.update(data_params)

        # 生成签名
        all_params["sign"] = self._generate_sign(all_params)

        # 发送请求
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.gateway_url,
                json=all_params,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=30.0
            )
            result = response.json()

        # 错误处理
        if "error_response" in result:
            error = result["error_response"]
            raise Exception(f"PDD API Error [{error.get('error_code')}]: {error.get('error_msg')} - {error.get('sub_msg', '')}")

        return result

    def _parse_goods_info(self, item: Dict[str, Any]) -> GoodsInfo:
        """解析商品信息"""
        return GoodsInfo(
            goods_id=str(item.get("goods_id", "")),
            goods_sign=item.get("goods_sign", ""),
            goods_name=item.get("goods_name", ""),
            min_group_price=item.get("min_group_price", 0),
            coupon_discount=item.get("coupon_discount", 0),
            promotion_amount=item.get("promotion_amount", 0),
            commission_rate=item.get("commission_rate", 0),
            sales=item.get("sales_tip", item.get("sales", "0")),
            mall_name=item.get("mall_name", ""),
            goods_thumbnail_url=item.get("goods_thumbnail_url", ""),
            cat_id=item.get("cat_id", 0),
        )

    @traceable(name="pdd_search_goods")
    async def search_goods(
        self,
        keyword: str,
        count: int = 10,
        page: int = 1,
        sort_type: int = 6,
        with_coupon: bool = True,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
    ) -> List[GoodsInfo]:
        """
        搜索商品

        Args:
            keyword: 搜索关键词
            count: 返回数量
            page: 页码
            sort_type: 排序方式 (0=综合, 2=佣金降序, 4=价格降序, 6=销量降序)
            with_coupon: 是否只看有券的
            min_price: 最低价格(分)
            max_price: 最高价格(分)

        Returns:
            商品信息列表
        """
        params = {
            "keyword": keyword,
            "pid": self.pid,
            "page": page,
            "page_size": max(min(count, 100), 10),
            "sort_type": sort_type,
        }

        if with_coupon:
            params["with_coupon"] = "true"
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price

        result = await self._call_api("pdd.ddk.goods.search", params)

        response = result.get("goods_search_response", {})
        goods_list = response.get("goods_list", [])

        return [self._parse_goods_info(item) for item in goods_list[:count]]

    @traceable(name="pdd_get_goods_detail")
    async def get_goods_detail(
        self,
        goods_sign: str,
        need_sku_info: bool = False,
    ) -> Optional[GoodsDetail]:
        """
        获取商品详情

        Args:
            goods_sign: 商品签名
            need_sku_info: 是否需要SKU信息

        Returns:
            商品详情
        """
        params = {
            "goods_sign": goods_sign,
            "pid": self.pid,
        }
        if need_sku_info:
            params["need_sku_info"] = "true"

        result = await self._call_api("pdd.ddk.goods.detail", params)

        response = result.get("goods_detail_response", {})
        details = response.get("goods_details", [])

        if not details:
            return None

        detail_data = details[0]
        return GoodsDetail(
            goods_sign=detail_data.get("goods_sign", goods_sign),
            goods_name=detail_data.get("goods_name", ""),
            goods_desc=detail_data.get("goods_desc"),
            min_group_price=detail_data.get("min_group_price", 0),
            max_group_price=detail_data.get("max_group_price", 0),
            coupon_discount=detail_data.get("coupon_discount", 0),
            commission_rate=detail_data.get("commission_rate", 0),
            commission_amount=detail_data.get("commission_amount", 0),
            sold_quantity=detail_data.get("sold_quantity", "0"),
            brand_name=detail_data.get("brand_name"),
            mall_name=detail_data.get("mall_name", ""),
            merchant_type=detail_data.get("merchant_type", 0),
            goods_image_urls=detail_data.get("goods_image_urls", []),
            goods_gallery_urls=detail_data.get("goods_gallery_urls", []),
            sku_list=detail_data.get("sku_list", []),
            activity_tags=detail_data.get("activity_tags", []),
        )

    @traceable(name="pdd_generate_promotion_url")
    async def generate_promotion_url(
        self,
        goods_sign: str,
        generate_short_url: bool = True,
        generate_we_app: bool = True,
    ) -> Optional[PromotionUrl]:
        """
        生成推广链接

        Args:
            goods_sign: 商品签名
            generate_short_url: 是否生成短链接
            generate_we_app: 是否生成小程序信息

        Returns:
            推广链接信息
        """
        params = {
            "p_id": self.pid,
            "goods_sign_list": json.dumps([goods_sign]),
            "generate_short_url": "true" if generate_short_url else "false",
            "generate_we_app": "true" if generate_we_app else "false",
        }

        result = await self._call_api("pdd.ddk.goods.promotion.url.generate", params)

        response = result.get("goods_promotion_url_generate_response", {})
        url_list = response.get("goods_promotion_url_list", [])

        if not url_list:
            return None

        url_data = url_list[0]
        return PromotionUrl(
            goods_sign=goods_sign,
            url=url_data.get("url", ""),
            short_url=url_data.get("short_url", ""),
            mobile_url=url_data.get("mobile_url", ""),
            we_app_info=url_data.get("we_app_info"),
            weixin_code=url_data.get("weixin_code", ""),
            weixin_short_link=url_data.get("weixin_short_link", ""),
        )

    async def get_pid_list(self, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """
        获取推广位列表

        Returns:
            推广位列表
        """
        params = {
            "page": page,
            "page_size": page_size,
        }

        result = await self._call_api("pdd.ddk.goods.pid.query", params)

        response = result.get("p_id_query_response", {})
        return response.get("p_id_list", [])

    # 工具方法

    @staticmethod
    def fen_to_yuan(fen: int) -> str:
        """分转元"""
        return f"{fen / 100:.2f}"

    @staticmethod
    def yuan_to_fen(yuan: float) -> int:
        """元转分"""
        return int(yuan * 100)

    @staticmethod
    def calculate_commission(price: int, rate: int, coupon: int = 0) -> int:
        """
        计算佣金金额

        Args:
            price: 商品价格(分)
            rate: 佣金比例(万分之几, 500=5%)
            coupon: 优惠券(分)

        Returns:
            佣金金额(分)
        """
        return (price - coupon) * rate // 10000

    @staticmethod
    def format_sales(sales: int) -> str:
        """格式化销量"""
        if sales >= 10000:
            return f"{sales / 10000:.1f}万+"
        elif sales >= 1000:
            return f"{sales / 1000:.1f}千+"
        return str(sales)
