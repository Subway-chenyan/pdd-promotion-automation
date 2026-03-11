---
name: pdd-api
description: 拼多多商品推广API技能 - 支持商品查询、详情获取、推广位创建、推广链接生成
---

# 拼多多商品推广API技能

## 技能概述

此技能提供拼多多开放平台API的完整调用功能，用于自动化商品推广工作流。

**核心功能：**
1. **商品查询** - 按关键词、类目、价格、销量等筛选商品
2. **商品详情** - 获取完整商品信息（文案、图片、SKU等）
3. **推广位管理** - 创建和查询推广位
4. **推广链接生成** - 生成多种类型的推广链接

## 快速开始

### 初始化API服务

```typescript
import { PddApiService } from './src/services/pdd-api.service';

const pddApi = new PddApiService(
    clientId,      // 从 config/pdd-config.json 读取
    clientSecret,  // 从 config/pdd-config.json 读取
    'https://gw-api.pinduoduo.com/api/router',
    { requestsPerMinute: 50, retryDelay: 1000 }
);
```

## 功能1: 商品查询

### 基础搜索

```typescript
const result = await pddApi.searchGoods({
    keyword: '蓝牙耳机',
    page: 1,
    page_size: 20
});

console.log(`找到 ${result.total} 个商品`);
result.goodsList.forEach(item => {
    console.log(`- ${item.goods_name}`);
    console.log(`  价格: ¥${PddApiService.fenToYuan(item.min_group_price)}`);
    console.log(`  销量: ${PddApiService.formatSales(item.sales || 0)}`);
});
```

### 高级筛选

```typescript
const result = await pddApi.searchGoods({
    keyword: '充电宝',
    cat_id: 18,                    // 电器类目
    min_price: 50,                 // 最低50元
    max_price: 200,                // 最高200元
    with_coupon: true,             // 只看有券的
    sort_type: 6,                  // 按销量降序
    is_brand_goods: true,          // 只要品牌商品
    merchant_type: 3,              // 只要旗舰店
    activity_tags: [7],            // 百亿补贴商品
    page_size: 10
});
```

### 按佣金范围筛选

```typescript
// 使用 range_list 筛选佣金比例 5%-20% 的商品
const result = await pddApi.searchGoods({
    keyword: '手机壳',
    cat_id: 18,
    range_list: [
        {
            range_id: 2,           // 2=佣金比例
            range_from: 500,       // 5% (500/10000)
            range_to: 2000         // 20% (2000/10000)
        }
    ]
});
```

### 分页查询

```typescript
let listId: string | undefined;
let allGoods: GoodsInfo[] = [];

for (let page = 1; page <= 5; page++) {
    const result = await pddApi.searchGoods({
        keyword: '数据线',
        page,
        page_size: 20,
        list_id  // 翻页时需要传入上一次返回的list_id
    });

    allGoods.push(...result.goodsList);
    listId = result.list_id;

    if (result.goodsList.length === 0) break;
}
```

### 排序方式 (sort_type)

| 值 | 说明 |
|----|------|
| 0 | 综合排序 |
| 1 | 佣金比例升序 |
| 2 | 佣金比例降序 |
| 3 | 价格升序 |
| 4 | 价格降序 |
| 5 | 销量升序 |
| 6 | 销量降序 |
| 7 | 优惠券金额升序 |
| 8 | 优惠券金额降序 |
| 9 | 券后价升序 |
| 10 | 券后价降序 |
| 14 | 佣金金额降序 |

### 活动标签 (activity_tags)

| 值 | 说明 |
|----|------|
| 4 | 秒杀 |
| 7 | 百亿补贴 |
| 31 | 品牌黑标 |
| 24 | 品牌高佣 |

## 功能2: 商品详情获取

### 获取完整商品信息

```typescript
const detail = await pddApi.getGoodsDetail('goods_sign_xxx', {
    pid: '推广位ID',
    search_id: '搜索ID',
    goods_img_type: 1,       // 1-场景图, 2-白底图
    need_sku_info: true      // 需要SKU信息
});

if (detail) {
    console.log('商品名称:', detail.goods_name);
    console.log('商品描述:', detail.goods_desc);
    console.log('价格区间:', detail.min_group_price, '-', detail.max_group_price);
    console.log('优惠券:', detail.coupon_discount);
    console.log('佣金比例:', detail.commission_rate / 100, '%');
    console.log('品牌:', detail.brand_name);
    console.log('店铺:', detail.mall_name);
    console.log('图片:', detail.goods_image_urls);
    console.log('SKU列表:', detail.sku_list);
}
```

### 提取商品亮点

```typescript
function extractHighlights(detail: GoodsDetail): string[] {
    const highlights: string[] = [];

    // 优惠券信息
    if (detail.coupon_discount > 0) {
        highlights.push(
            `领券立减 ¥${PddApiService.fenToYuan(detail.coupon_discount)}`
        );
    }

    // 百亿补贴
    if (detail.activity_tags.includes(7)) {
        highlights.push('百亿补贴，超值优惠');
    }

    // 品牌商品
    if (detail.brand_name) {
        highlights.push(`${detail.brand_name} 品牌正品`);
    }

    // 高销量
    const sales = parseInt(detail.sold_quantity) || 0;
    if (sales >= 10000) {
        highlights.push(`已售${PddApiService.formatSales(sales)}件`);
    }

    // 旗舰店
    if (detail.merchant_type === 3) {
        highlights.push('官方旗舰店');
    }

    return highlights;
}
```

## 功能3: 推广位管理

### 查询推广位列表

```typescript
const pidList = await pddApi.getPidList(1, 20);

pidList.forEach(pid => {
    console.log(`PID: ${pid.p_id}`);
    console.log(`名称: ${pid.pid_name}`);
    console.log(`创建时间: ${new Date(pid.create_time * 1000).toLocaleString()}`);
});
```

### 创建推广位

```typescript
// 创建10个默认推广位
const result = await pddApi.createPid({
    number: 10
});

console.log(`成功创建 ${result.pidList.length} 个推广位`);
console.log(`剩余可用数量: ${result.remainCount}`);

// 使用自定义名称创建推广位
const customResult = await pddApi.createPid({
    number: 5,
    p_id_name_list: ['群A', '群B', '群C', '群D', '群E']
});

customResult.pidList.forEach(pid => {
    console.log(`创建成功: ${pid.p_id} - ${pid.pid_name}`);
});
```

### 推广位用途

**1. 代理/分销模式**
```
为用户A创建: pid_1_1
为用户B创建: pid_1_2
当用户通过pid_1_2购买时，可以追踪到B的推广，实现佣金分成
```

**2. 多渠道效果追踪**
```
微信群A → pid_A
微信群B → pid_B
通过订单查询可以统计不同渠道的推广效果
```

## 功能4: 推广链接生成

### 生成基础推广链接

```typescript
const urls = await pddApi.generatePromotionUrl({
    pid: '推广位ID',
    goods_sign_list: ['goods_sign_1', 'goods_sign_2'],
    generate_short_url: true,
    multi_group: false          // false=单人团, true=多人团
});

urls.forEach(item => {
    console.log('普通链接:', item.url);
    console.log('短链接:', item.short_url);
    console.log('Schema链接:', item.schema_url);
});
```

### 生成微信小程序推广

```typescript
const urls = await pddApi.generatePromotionUrl({
    pid: '推广位ID',
    goods_sign_list: ['goods_sign_xxx'],
    generate_we_app: true,
    generate_weixin_code: true,
    generate_short_link: true
});

const wechatInfo = urls[0].we_app_info;
console.log('小程序AppID:', wechatInfo.app_id);
console.log('小程序路径:', wechatInfo.page_path);
console.log('小程序码:', urls[0].weixin_code);
console.log('小程序短链:', urls[0].weixin_short_link);
```

### 生成多人团推广链接

```typescript
// 多人团: 用户分享给好友参团，推手可获得双份佣金
const urls = await pddApi.generatePromotionUrl({
    pid: '推广位ID',
    goods_sign_list: ['goods_sign_xxx'],
    multi_group: true,
    generate_short_url: true
});
```

### 添加自定义参数（追踪）

```typescript
const urls = await pddApi.generatePromotionUrl({
    pid: '推广位ID',
    goods_sign_list: ['goods_sign_xxx'],
    custom_parameters: {
        uid: 'user_12345',        // 用户唯一标识
        sid: 'session_67890',     // 会话ID
        channel: 'wechat_group_a' // 渠道标识
    },
    search_id: '搜索ID',  // 来自搜索接口的search_id，可提高收益
    generate_short_url: true
});
```

### 推广链接类型说明

| 链接类型 | 使用场景 | 说明 |
|---------|---------|------|
| `url` | 通用 | 普通长链，微信内进入领券页拉起小程序 |
| `short_url` | 通用 | 短链接，功能同url |
| `schema_url` | APP唤醒 | 唤醒拼多多APP |
| `weixin_short_link` | 微信 | 小程序短链，直接唤起小程序 |
| `weixin_code` | 微信 | 小程序码图片 |

## 数据处理工具

### 价格转换

```typescript
// 分转元
PddApiService.fenToYuan(599900);  // "5999.00"

// 元转分
PddApiService.yuanToFen(59.99);   // 5999
```

### 佣金计算

```typescript
// 计算佣金金额
const commission = PddApiService.calculateCommission(
    599900,    // 商品价格(分)
    500,       // 佣金比例(万分之几, 500=5%)
    20000      // 优惠券(分)
);
// 结果: 28995 分 = 289.95元
// 公式: (5999-200) * 5% = 289.95
```

### 销量格式化

```typescript
PddApiService.formatSales(150000);    // "15.0万+"
PddApiService.formatSales(5500);      // "5.5千+"
PddApiService.formatSales(999);       // "999"
```

## 完整工作流示例

```typescript
import { PddApiService } from './src/services/pdd-api.service';

// 1. 初始化
const pddApi = new PddApiService(clientId, clientSecret);

// 2. 搜索商品
const searchResult = await pddApi.searchGoods({
    keyword: '蓝牙耳机',
    cat_id: 18,
    min_price: 100,
    max_price: 500,
    with_coupon: true,
    sort_type: 6,              // 按销量降序
    page_size: 5
});

console.log(`找到 ${searchResult.total} 个商品`);

// 3. 获取商品详情
const goodsSign = searchResult.goodsList[0].goods_sign;
const detail = await pddApi.getGoodsDetail(goodsSign, {
    need_sku_info: true
});

// 4. 生成推广链接
const urls = await pddApi.generatePromotionUrl({
    pid: 'your_pid_here',
    goods_sign_list: [goodsSign],
    generate_short_url: true,
    generate_we_app: true,
    generate_weixin_code: true
});

// 5. 输出结果
const url = urls[0];
console.log(`
商品: ${detail.goods_name}
价格: ¥${PddApiService.fenToYuan(detail.min_group_price)}
优惠券: ¥${PddApiService.fenToYuan(detail.coupon_discount)}
券后价: ¥${PddApiService.fenToYuan(detail.min_group_price - detail.coupon_discount)}
佣金: ¥${PddApiService.fenToYuan(detail.commission_amount)}
销量: ${PddApiService.formatSales(parseInt(detail.sold_quantity) || 0)}

推广链接: ${url.short_url}
小程序码: ${url.weixin_code}
`);
```

## 错误处理

### 检查API错误

```typescript
const result = await pddApi.searchGoods({ keyword: '手机' });

// 检查是否有错误响应
if (result.error_response) {
    const { error_code, error_msg, sub_code, sub_msg } = result.error_response;

    console.error(`API错误 [${error_code}]: ${error_msg}`);

    // 常见错误处理
    switch (sub_code) {
        case '60001':
            console.error('需要推广位授权备案');
            console.error('请访问: https://jinbao.pinduoduo.com/qa-system?questionId=204');
            break;
        case '60010':
            console.error('推广位ID不存在');
            break;
        default:
            console.error(`[${sub_code}] ${sub_msg}`);
    }
}
```

### 常见错误码

| 错误码 | 说明 | 解决方案 |
|-------|------|---------|
| 60001 | 推广位未授权备案 | 完成授权备案 |
| 60010 | 推广位ID不存在 | 检查pid参数 |
| 60011 | goods_sign无效 | 检查商品签名 |
| 50001 | 参数错误 | 检查请求参数 |

## 类目ID速查表

| ID | 名称 | ID | 名称 |
|----|------|----|------|
| 15 | 百货 | 18 | 电器 |
| 4 | 母婴 | 16 | 美妆 |
| 1 | 食品 | 743 | 男装 |
| 14 | 女装 | 818 | 家纺 |
| 1281 | 鞋包 | 2478 | 文具 |
| 1282 | 内衣 | 1451 | 运动 |
| 13 | 水果 | 590 | 虚拟 |
| 2048 | 汽车 | 1917 | 家装 |
| 2974 | 家具 | 3279 | 医药 |

## 授权备案说明

### 哪些API需要授权？

| API | 是否需要授权 |
|-----|-------------|
| pdd.goods.cats.get | ❌ 不需要 |
| pdd.ddk.goods.pid.query | ❌ 不需要 |
| pdd.ddk.goods.pid.generate | ❌ 不需要 |
| pdd.ddk.goods.search | ✅ **需要** |
| pdd.ddk.goods.detail | ✅ **需要** |
| pdd.ddk.goods.promotion.url.generate | ✅ **需要** |

### 完成授权备案

1. 访问 https://jinbao.pinduoduo.com/
2. 登录拼多多账号
3. 进入「推广管理」→「推广位管理」
4. 选择需要授权的推广位
5. 提交授权备案申请（通常即时生效）

## 配置文件

config/pdd-config.json:

```json
{
  "clientId": "你的客户端ID",
  "clientSecret": "你的客户端密钥",
  "gatewayUrl": "https://gw-api.pinduoduo.com/api/router",
  "defaultPid": "默认推广位ID",
  "rateLimit": {
    "requestsPerMinute": 50,
    "retryDelay": 1000
  }
}
```

## 使用检查清单

使用此技能时，请按以下清单检查：

- [ ] API配置正确（clientId、clientSecret）
- [ ] 推广位已完成授权备案（如需调用商品相关API）
- [ ] 价格单位：API使用分，显示时转换为元
- [ ] 佣金比例：以万为单位（500=5%）
- [ ] 遵守API频率限制（建议<50次/分钟）
- [ ] 使用search_id可提高收益
- [ ] 错误处理完善
- [ ] 自定义参数格式正确（JSON字符串）

## API参考

- 拼多多开放平台: https://open.pinduoduo.com/
- 多多进宝: https://jinbao.pinduoduo.com/
- 授权备案说明: https://jinbao.pinduoduo.com/qa-system?questionId=204
- goods_sign说明: https://jinbao.pinduoduo.com/qa-system?questionId=252
