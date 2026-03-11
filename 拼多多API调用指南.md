# 拼多多开放平台 API 调用指南

## 📋 目录

- [环境准备](#环境准备)
- [API签名算法](#api签名算法)
- [API调用流程](#api调用流程)
- [常用API示例](#常用api示例)
- [错误处理](#错误处理)
- [常见问题](#常见问题)

---

## 环境准备

### 1. 获取API密钥

1. 登录 [拼多多开放平台](https://open.pinduoduo.com/)
2. 进入「控制台」→「应用管理」
3. 查看应用的 `client_id` 和 `client_secret`

```
client_id:     5b0526d2772944eb988ed13a7c5fcc9e
client_secret: abe6000acb95ace679578392afe3d05653a5c275
```

### 2. API网关地址

```
正式环境: https://gw-api.pinduoduo.com/api/router
```

### 3. 请求方式

```
Method: POST
Content-Type: application/json; charset=utf-8
```

---

## API签名算法

### 签名规则

拼多多使用 **MD5** 签名算法，签名步骤如下：

```
┌─────────────────────────────────────────────────────────────┐
│                     签名生成流程                              │
├─────────────────────────────────────────────────────────────┤
│  1. 所有参数按字母顺序排列（ASCII升序）                        │
│  2. 拼接成 key1value1key2value2... 的字符串                   │
│  3. 在字符串首尾拼接 client_secret                           │
│  4. 对整个字符串进行MD5加密                                   │
│  5. 将结果转为大写，得到签名 sign                             │
└─────────────────────────────────────────────────────────────┘
```

### 签名公式

```
sign = MD5(client_secret + sorted_params + client_secret).toUpperCase()
```

### 签名示例

假设有以下参数：

```javascript
{
  type: "pdd.ddk.goods.search",
  client_id: "5b0526d2772944eb988ed13a7c5fcc9e",
  timestamp: "1773060313",
  keyword: "手机",
  page: "1"
}
```

**步骤1: 参数排序**

```
按字母顺序排列后:
client_id, keyword, page, timestamp, type
```

**步骤2: 拼接参数**

```
client_id5b0526d2772944eb988ed13a7c5fcc9ekeyword手机page1timestamp1773060313typepdd.ddk.goods.search
```

**步骤3: 首尾拼接密钥**

```
abe6000acb95ace679578392afe3d05653a5c275client_id5b0526d2772944eb988ed13a7c5fcc9ekeyword手机page1timestamp1773060313typepdd.ddk.goods.searchabe6000acb95ace679578392afe3d05653a5c275
```

**步骤4: MD5加密并转大写**

```
sign = 857FAD1626CD8F7CBF5E22F0B87285E7
```

### Node.js 签名实现

```javascript
const crypto = require('crypto');

function generateSign(params, clientSecret) {
    // 1. 按字母顺序排序
    const sortedKeys = Object.keys(params).sort();

    // 2. 拼接参数
    let signStr = '';
    for (const key of sortedKeys) {
        if (key !== 'sign') {  // sign参数不参与签名
            signStr += key + params[key];
        }
    }

    // 3. 首尾拼接client_secret
    signStr = clientSecret + signStr + clientSecret;

    // 4. MD5加密并转大写
    return crypto.createHash('md5')
        .update(signStr, 'utf8')
        .digest('hex')
        .toUpperCase();
}
```

### Python 签名实现

```python
import hashlib

def generate_sign(params, client_secret):
    # 1. 按字母顺序排序
    sorted_keys = sorted(params.keys())

    # 2. 拼接参数
    sign_str = ''
    for key in sorted_keys:
        if key != 'sign':  # sign参数不参与签名
            sign_str += key + str(params[key])

    # 3. 首尾拼接client_secret
    sign_str = client_secret + sign_str + client_secret

    # 4. MD5加密并转大写
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
```

---

## API调用流程

### 1. 准备公共参数

所有API调用都必须包含以下公共参数：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| type | string | 是 | API接口名，如 `pdd.ddk.goods.search` |
| client_id | string | 是 | 应用标志 |
| timestamp | string | 是 | UNIX时间戳（秒） |
| data_type | string | 否 | 返回格式，默认JSON |
| sign | string | 是 | API请求签名 |

### 2. 构建请求参数

```javascript
// 公共参数
const publicParams = {
    type: "pdd.ddk.goods.search",
    client_id: "5b0526d2772944eb988ed13a7c5fcc9e",
    timestamp: Math.floor(Date.now() / 1000).toString(),
    data_type: "JSON"
};

// 业务参数
const businessParams = {
    keyword: "手机",
    page: 1,
    page_size: 10,
    pid: "44136818_314557112"
};

// 合并参数
const allParams = { ...publicParams, ...businessParams };
```

### 3. 生成签名

```javascript
const sign = generateSign(allParams, CLIENT_SECRET);

// 添加签名到请求参数
const requestBody = { ...allParams, sign };
```

### 4. 发送请求

```javascript
const https = require('https');

function callPddApi(requestBody) {
    return new Promise((resolve, reject) => {
        const url = "https://gw-api.pinduoduo.com/api/router";
        const jsonStr = JSON.stringify(requestBody);

        const options = {
            hostname: 'gw-api.pinduoduo.com',
            port: 443,
            path: '/api/router',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8',
                'Content-Length': Buffer.byteLength(jsonStr)
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    resolve(data);
                }
            });
        });

        req.on('error', reject);
        req.write(jsonStr);
        req.end();
    });
}
```

---

## 常用API示例

### 1. 获取商品类目

**API**: `pdd.goods.cats.get`

```javascript
const result = await callPddApi({
    type: "pdd.goods.cats.get",
    client_id: CLIENT_ID,
    timestamp: timestamp,
    data_type: "JSON",
    parent_cat_id: 0,  // 0表示获取一级类目
    sign: sign
});

// 响应示例
{
  "goods_cats_get_response": {
    "goods_cats_list": [
      { "cat_id": 5834, "cat_name": "手机", "level": 1, "parent_cat_id": 0 },
      { "cat_id": 6398, "cat_name": "零食/坚果/特产", "level": 1, "parent_cat_id": 0 }
    ]
  }
}
```

### 2. 获取商品标签

**API**: `pdd.goods.opt.get`

```javascript
const result = await callPddApi({
    type: "pdd.goods.opt.get",
    client_id: CLIENT_ID,
    timestamp: timestamp,
    data_type: "JSON",
    parent_opt_id: 0,  // 0表示获取一级标签
    sign: sign
});

// 响应示例
{
  "goods_opt_get_response": {
    "goods_opt_list": [
      { "opt_id": 1, "opt_name": "食品", "level": 1 },
      { "opt_id": 14, "opt_name": "女装", "level": 1 }
    ]
  }
}
```

### 3. 获取推广位列表

**API**: `pdd.ddk.goods.pid.query`

```javascript
const result = await callPddApi({
    type: "pdd.ddk.goods.pid.query",
    client_id: CLIENT_ID,
    timestamp: timestamp,
    data_type: "JSON",
    page: 1,
    page_size: 20,
    sign: sign
});

// 响应示例
{
  "p_id_query_response": {
    "p_id_list": [
      {
        "p_id": "44136818_314557112",
        "pid_name": "多多分享",
        "status": 0
      }
    ],
    "total_count": 1
  }
}
```

### 4. 商品搜索

**API**: `pdd.ddk.goods.search`

**注意**: 需要先在[多多进宝](https://jinbao.pinduoduo.com)完成推广位授权备案

```javascript
const result = await callPddApi({
    type: "pdd.ddk.goods.search",
    client_id: CLIENT_ID,
    timestamp: timestamp,
    data_type: "JSON",
    keyword: "手机",
    page: 1,
    page_size: 10,
    pid: "44136818_314557112",  // 必填：推广位ID
    sign: sign
});

// 响应示例
{
  "goods_search_response": {
    "goods_list": [
      {
        "goods_id": "462056403632",
        "goods_name": "Apple iPhone 15",
        "min_group_price": 599900,  // 单位：分
        "coupon_discount": 5000,    // 单位：分
        "promotion_amount": 3000,   // 单位：分
        "sales_tip": "已拼10万+件",
        "mall_name": " Apple官方旗舰店"
      }
    ],
    "total_count": 1500
  }
}
```

### 5. 商品详情

**API**: `pdd.ddk.goods.detail`

```javascript
const result = await callPddApi({
    type: "pdd.ddk.goods.detail",
    client_id: CLIENT_ID,
    timestamp: timestamp,
    data_type: "JSON",
    goods_sign: "c9r2omogKFFAc7WBwvbZU1ikIb16_J3CTa8HNN",  // 使用goods_sign
    sign: sign
});
```

---

## 错误处理

### 常见错误码

| 错误码 | 错误信息 | 解决方案 |
|--------|----------|----------|
| 20004 | 签名验证失败 | 检查签名算法是否正确 |
| 50001 | 业务服务错误 | 查看 sub_code 获取详细信息 |
| 60001 | 未授权备案 | 访问[授权备案页面](https://jinbao.pinduoduo.com/qa-system?questionId=204) |
| 10002 | 缺少必填参数 | 检查是否传入所有必填参数 |

### 错误响应示例

```json
{
  "error_response": {
    "error_code": 50001,
    "error_msg": "业务服务错误",
    "sub_code": "60001",
    "sub_msg": "未传入已经授权备案过的相关参数",
    "request_id": "17730603139080495"
  }
}
```

---

## 常见问题

### Q1: 签名验证失败怎么办？

1. 检查参数排序是否正确（按ASCII升序）
2. 确认首尾都拼接了 `client_secret`
3. 验证MD5加密后是否转大写
4. 检查 `sign` 参数本身是否参与签名（不应该）

### Q2: 商品搜索报错"未授权备案"？

这是正常现象，需要：

1. 登录 [多多进宝](https://jinbao.pinduoduo.com)
2. 完成「推广位授权备案」
3. 等待备案审核通过

### Q3: goods_id 提示为空？

`goods_id` 已废弃，请使用 `goods_sign` 参数。

### Q4: 如何获取推广位PID？

使用 `pdd.ddk.goods.pid.query` API 获取，格式为 `{duo_id}_{推广位ID}`。

---

## 完整示例代码

### Node.js 版本

```javascript
const crypto = require('crypto');
const https = require('https');
const url = require('url');

const CLIENT_ID = "your_client_id";
const CLIENT_SECRET = "your_client_secret";
const GATEWAY_URL = "https://gw-api.pinduoduo.com/api/router";

// 生成签名
function generateSign(params) {
    const sortedKeys = Object.keys(params).sort();
    let signStr = '';
    for (const key of sortedKeys) {
        if (key !== 'sign') {
            signStr += key + params[key];
        }
    }
    signStr = CLIENT_SECRET + signStr + CLIENT_SECRET;
    return crypto.createHash('md5').update(signStr, 'utf8').digest('hex').toUpperCase();
}

// 发送HTTPS POST请求
function httpsPost(urlStr, jsonData) {
    return new Promise((resolve, reject) => {
        const parsedUrl = url.parse(urlStr);
        const jsonStr = JSON.stringify(jsonData);

        const options = {
            hostname: parsedUrl.hostname,
            port: 443,
            path: parsedUrl.path,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8',
                'Content-Length': Buffer.byteLength(jsonStr)
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    resolve({ rawResponse: data, statusCode: res.statusCode });
                }
            });
        });

        req.on('error', reject);
        req.write(jsonStr);
        req.end();
    });
}

// 调用API
async function callPddApi(type, dataParams) {
    const timestamp = Math.floor(Date.now() / 1000).toString();

    const allParams = {
        type: type,
        client_id: CLIENT_ID,
        timestamp: timestamp,
        data_type: 'JSON',
        ...dataParams
    };

    const sign = generateSign(allParams);
    const requestBody = { ...allParams, sign };

    return await httpsPost(GATEWAY_URL, requestBody);
}

// 使用示例
async function main() {
    // 获取商品类目
    const result = await callPddApi('pdd.goods.cats.get', {
        parent_cat_id: 0
    });

    console.log(JSON.stringify(result, null, 2));
}

main().catch(console.error);
```

---

## 参考链接

- [拼多多开放平台](https://open.pinduoduo.com/)
- [多多进宝](https://jinbao.pinduoduo.com)
- [API文档](https://open.pinduoduo.com/application/document/browse?idStr=8EC06C399636041E)
- [授权备案说明](https://jinbao.pinduoduo.com/qa-system?questionId=204)
