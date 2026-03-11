#!/usr/bin/env node
/**
 * 拼多多API完整测试脚本
 *
 * 测试所有API功能：
 * 1. 获取商品类目
 * 2. 获取推广位列表
 * 3. 创建推广位
 * 4. 搜索商品（多种筛选条件）
 * 5. 获取商品详情
 * 6. 生成推广链接
 */

const CLIENT_ID = "5b0526d2772944eb988ed13a7c5fcc9e";
const CLIENT_SECRET = "abe6000acb95ace679578392afe3d05653a5c275";
const GATEWAY_URL = "https://gw-api.pinduoduo.com/api/router";

const crypto = require('crypto');

/**
 * 生成签名
 */
function generateSign(params, clientSecret) {
    const sortedKeys = Object.keys(params).sort();
    let signStr = '';
    for (const key of sortedKeys) {
        if (key !== 'sign') {
            signStr += key + params[key];
        }
    }
    signStr = clientSecret + signStr + clientSecret;
    return crypto.createHash('md5').update(signStr, 'utf8').digest('hex').toUpperCase();
}

/**
 * 发送API请求
 */
async function callApi(type, dataParams = {}) {
    const timestamp = Math.floor(Date.now() / 1000).toString();

    const allParams = {
        type: type,
        client_id: CLIENT_ID,
        timestamp: timestamp,
        data_type: 'JSON',
        ...dataParams
    };

    allParams.sign = generateSign(allParams, CLIENT_SECRET);

    console.log(`\n📡 调用API: ${type}`);
    if (Object.keys(dataParams).length > 0) {
        console.log('参数:', JSON.stringify(dataParams, null, 2));
    }

    try {
        const response = await fetch(GATEWAY_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8',
            },
            body: JSON.stringify(allParams)
        });

        const result = await response.json();

        if (result.error_response) {
            console.error(`❌ API错误: ${result.error_response.error_msg}`);
            if (result.error_response.sub_code) {
                console.error(`   错误码: ${result.error_response.sub_code}`);
                console.error(`   错误信息: ${result.error_response.sub_msg}`);
            }
            return null;
        }

        console.log('✅ 调用成功');
        return result;
    } catch (error) {
        console.error(`❌ 请求失败: ${error.message}`);
        return null;
    }
}

/**
 * 分转元
 */
function fenToYuan(fen) {
    return (fen / 100).toFixed(2);
}

/**
 * 格式化销量
 */
function formatSales(sales) {
    if (!sales) return '0';
    if (sales >= 10000) {
        return `${(sales / 10000).toFixed(1)}万+`;
    } else if (sales >= 1000) {
        return `${(sales / 1000).toFixed(1)}千+`;
    }
    return sales.toString();
}

// ==================== 测试函数 ====================

/**
 * 测试1: 获取商品类目
 */
async function test1_GetCategories() {
    console.log('\n' + '='.repeat(60));
    console.log('测试1: 获取商品类目 (pdd.goods.cats.get)');
    console.log('='.repeat(60));

    const result = await callApi('pdd.goods.cats.get', {
        parent_cat_id: 0
    });

    if (result) {
        const cats = result.goods_cats_get_response?.goods_cats_list || [];
        console.log(`\n✅ 获取到 ${cats.length} 个一级类目\n`);

        const catMap = {
            15: '百货', 4: '母婴', 1: '食品', 14: '女装', 18: '电器',
            1281: '鞋包', 1282: '内衣', 16: '美妆', 743: '男装', 13: '水果',
            818: '家纺', 2478: '文具', 1451: '运动', 590: '虚拟', 2048: '汽车',
            1917: '家装', 2974: '家具', 3279: '医药'
        };

        console.log('📋 类目映射:');
        for (const [id, name] of Object.entries(catMap)) {
            console.log(`   ID ${id}: ${name}`);
        }

        return cats;
    }
    return [];
}

/**
 * 测试2: 获取推广位列表
 */
async function test2_GetPidList() {
    console.log('\n' + '='.repeat(60));
    console.log('测试2: 获取推广位列表 (pdd.ddk.goods.pid.query)');
    console.log('='.repeat(60));

    const result = await callApi('pdd.ddk.goods.pid.query', {
        page: 1,
        page_size: 20
    });

    if (result) {
        const pidList = result.p_id_query_response?.p_id_list || [];
        console.log(`\n✅ 获取到 ${pidList.length} 个推广位\n`);

        if (pidList.length > 0) {
            console.log('📋 推广位列表:');
            pidList.forEach((pid, i) => {
                console.log(`   ${i + 1}. PID: ${pid.p_id}`);
                console.log(`      名称: ${pid.pid_name || '未命名'}`);
                console.log(`      状态: ${pid.status === 0 ? '✅正常' : '❌异常'}`);
                console.log(`      媒体ID: ${pid.media_id || '无'}`);
            });

            return pidList[0]?.p_id; // 返回第一个PID供后续使用
        } else {
            console.log('⚠️  没有可用的推广位');
        }
    }
    return null;
}

/**
 * 测试3: 创建推广位
 */
async function test3_CreatePid() {
    console.log('\n' + '='.repeat(60));
    console.log('测试3: 创建推广位 (pdd.ddk.goods.pid.generate)');
    console.log('='.repeat(60));

    const result = await callApi('pdd.ddk.goods.pid.generate', {
        number: 3,
        p_id_name_list: JSON.stringify(['测试位A', '测试位B', '测试位C'])
    });

    if (result) {
        const response = result.p_id_generate_response;
        const pidList = response?.p_id_list || [];
        console.log(`\n✅ 成功创建 ${pidList.length} 个推广位\n`);

        console.log('📋 新创建的推广位:');
        pidList.forEach((pid, i) => {
            console.log(`   ${i + 1}. PID: ${pid.p_id}`);
            console.log(`      名称: ${pid.pid_name}`);
            console.log(`      创建时间: ${new Date(pid.create_time * 1000).toLocaleString()}`);
        });

        console.log(`\n剩余可用数量: ${response?.remain_pid_count || 0}`);

        return pidList[0]?.p_id;
    }
    return null;
}

/**
 * 测试4: 搜索商品 - 基础搜索
 */
async function test4_SearchBasic(pid) {
    console.log('\n' + '='.repeat(60));
    console.log('测试4: 搜索商品 - 基础搜索 (pdd.ddk.goods.search)');
    console.log('='.repeat(60));

    const result = await callApi('pdd.ddk.goods.search', {
        keyword: '蓝牙耳机',
        pid: pid,
        page: 1,
        page_size: 10
    });

    if (result) {
        const response = result.goods_search_response;
        const goodsList = response?.goods_list || [];
        console.log(`\n✅ 找到 ${response?.total || 0} 个商品，显示前 ${goodsList.length} 个\n`);

        goodsList.forEach((item, i) => {
            console.log(`${i + 1}. ${item.goods_name}`);
            console.log(`   价格: ¥${fenToYuan(item.min_group_price)}`);
            console.log(`   优惠券: ¥${fenToYuan(item.coupon_discount || 0)}`);
            console.log(`   佣金: ¥${fenToYuan(item.promotion_amount || 0)}`);
            console.log(`   销量: ${formatSales(item.sales || 0)}`);
            console.log(`   goods_sign: ${item.goods_sign}\n`);
        });

        return goodsList[0]?.goods_sign;
    }
    return null;
}

/**
 * 测试5: 搜索商品 - 高级筛选
 */
async function test5_SearchAdvanced(pid) {
    console.log('\n' + '='.repeat(60));
    console.log('测试5: 搜索商品 - 高级筛选');
    console.log('='.repeat(60));

    const result = await callApi('pdd.ddk.goods.search', {
        keyword: '充电宝',
        cat_id: 18,
        pid: pid,
        min_price: 5000,      // 50元
        max_price: 20000,     // 200元
        with_coupon: 'true',
        sort_type: 6,         // 按销量降序
        is_brand_goods: 'true',
        page_size: 10
    });

    if (result) {
        const response = result.goods_search_response;
        const goodsList = response?.goods_list || [];
        console.log(`\n✅ 筛选结果: ${goodsList.length} 个商品\n`);

        goodsList.forEach((item, i) => {
            console.log(`${i + 1}. ${item.goods_name}`);
            console.log(`   券后价: ¥${fenToYuan(item.min_group_price - (item.coupon_discount || 0))}`);
            console.log(`   销量: ${formatSales(item.sales || 0)}`);
            console.log(`   店铺: ${item.mall_name || '未知'}`);
        });
    }
}

/**
 * 测试6: 搜索商品 - 佣金筛选
 */
async function test6_SearchByCommission(pid) {
    console.log('\n' + '='.repeat(60));
    console.log('测试6: 搜索商品 - 按佣金比例筛选');
    console.log('='.repeat(60));

    const result = await callApi('pdd.ddk.goods.search', {
        keyword: '手机壳',
        cat_id: 18,
        pid: pid,
        range_list: JSON.stringify([
            {
                range_id: 2,       // 2=佣金比例
                range_from: 500,   // 5%
                range_to: 2000     // 20%
            }
        ]),
        sort_type: 2,         // 按佣金比例降序
        page_size: 10
    });

    if (result) {
        const response = result.goods_search_response;
        const goodsList = response?.goods_list || [];
        console.log(`\n✅ 找到 ${goodsList.length} 个高佣金商品\n`);

        goodsList.forEach((item, i) => {
            const commissionRate = ((item.commission_rate || 0) / 100).toFixed(2);
            console.log(`${i + 1}. ${item.goods_name}`);
            console.log(`   佣金比例: ${commissionRate}%`);
            console.log(`   佣金金额: ¥${fenToYuan(item.promotion_amount || 0)}`);
            console.log(`   销量: ${formatSales(item.sales || 0)}`);
        });
    }
}

/**
 * 测试7: 获取商品详情
 */
async function test7_GetDetail(goodsSign, pid) {
    console.log('\n' + '='.repeat(60));
    console.log('测试7: 获取商品详情 (pdd.ddk.goods.detail)');
    console.log('='.repeat(60));

    if (!goodsSign) {
        console.log('⚠️  跳过: 没有goods_sign');
        return null;
    }

    const result = await callApi('pdd.ddk.goods.detail', {
        goods_sign: goodsSign,
        pid: pid
    });

    if (result) {
        const detail = result.goods_detail_response?.goods_details?.[0];
        if (detail) {
            console.log('\n📦 商品详情:\n');
            console.log(`商品名称: ${detail.goods_name}`);
            console.log(`商品描述: ${detail.goods_desc?.substring(0, 100)}...`);
            console.log(`价格区间: ¥${fenToYuan(detail.min_group_price)} - ¥${fenToYuan(detail.max_group_price)}`);
            console.log(`优惠券: ¥${fenToYuan(detail.coupon_discount || 0)}`);
            console.log(`券后价: ¥${fenToYuan(detail.min_group_price - (detail.coupon_discount || 0))}`);
            console.log(`佣金比例: ${((detail.commission_rate || 0) / 100).toFixed(2)}%`);
            console.log(`佣金金额: ¥${fenToYuan(detail.commission_amount || 0)}`);
            console.log(`已售数量: ${detail.sold_quantity || '0'}`);
            console.log(`品牌: ${detail.brand_name || '无'}`);
            console.log(`店铺: ${detail.mall_name}`);
            console.log(`店铺类型: ${detail.merchant_type === 3 ? '旗舰店' : '其他'}`);
            console.log(`\n图片数量: ${detail.goods_image_urls?.length || 0} 张`);
            console.log(`轮播图: ${detail.goods_gallery_urls?.length || 0} 张`);
            console.log(`SKU数量: ${detail.sku_list?.length || 0}`);

            return detail;
        }
    }
    return null;
}

/**
 * 测试8: 生成推广链接 - 基础
 */
async function test8_GenerateUrlBasic(goodsSign, pid) {
    console.log('\n' + '='.repeat(60));
    console.log('测试8: 生成推广链接 - 基础');
    console.log('='.repeat(60));

    if (!goodsSign || !pid) {
        console.log('⚠️  跳过: 缺少参数');
        return;
    }

    const result = await callApi('pdd.ddk.goods.promotion.url.generate', {
        p_id: pid,
        goods_sign_list: JSON.stringify([goodsSign]),
        generate_short_url: 'true',
        multi_group: 'false'
    });

    if (result) {
        const urlList = result.goods_promotion_url_generate_response?.goods_promotion_url_list || [];
        console.log(`\n✅ 成功生成 ${urlList.length} 个推广链接\n`);

        urlList.forEach((item, i) => {
            console.log(`链接 ${i + 1}:`);
            console.log(`   普通链接: ${item.url}`);
            console.log(`   短链接: ${item.short_url}`);
            console.log(`   移动端链接: ${item.mobile_url}`);
            console.log(`   Schema链接: ${item.schema_url || '无'}`);
        });
    }
}

/**
 * 测试9: 生成推广链接 - 微信小程序
 */
async function test9_GenerateUrlWechat(goodsSign, pid) {
    console.log('\n' + '='.repeat(60));
    console.log('测试9: 生成推广链接 - 微信小程序');
    console.log('='.repeat(60));

    if (!goodsSign || !pid) {
        console.log('⚠️  跳过: 缺少参数');
        return;
    }

    const result = await callApi('pdd.ddk.goods.promotion.url.generate', {
        p_id: pid,
        goods_sign_list: JSON.stringify([goodsSign]),
        generate_we_app: 'true',
        generate_short_link: 'true',
        custom_parameters: JSON.stringify({
            uid: 'test_user_123',
            channel: 'test_channel'
        })
    });

    if (result) {
        const urlList = result.goods_promotion_url_generate_response?.goods_promotion_url_list || [];
        console.log(`\n✅ 成功生成微信小程序推广\n`);

        urlList.forEach((item, i) => {
            const weapp = item.we_app_info;
            console.log(`商品 ${i + 1}:`);
            console.log(`   小程序AppID: ${weapp?.app_id || '无'}`);
            console.log(`   小程序路径: ${weapp?.page_path || '无'}`);
            console.log(`   小程序标题: ${weapp?.title || '无'}`);
            console.log(`   小程序码: ${item.weixin_code || '无'}`);
            console.log(`   小程序短链: ${item.weixin_short_link || '无'}`);
        });
    }
}

/**
 * 测试10: 查询推广位备案状态
 */
async function test10_QueryAuthorityStatus(pid) {
    console.log('\n' + '='.repeat(60));
    console.log('测试10: 查询推广位备案状态 (pdd.ddk.member.authority.query)');
    console.log('='.repeat(60));

    if (!pid) {
        console.log('⚠️  跳过: 没有推广位PID');
        return false;
    }

    const result = await callApi('pdd.ddk.member.authority.query', {
        pid: pid
    });

    if (result) {
        console.log('\n📋 备案状态查询结果:\n');

        // 检查响应结构
        const response = result.authority_query_response || result.member_authority_query_response;

        if (response) {
            const bind = response.bind;

            console.log(`推广位PID: ${pid}`);
            console.log(`bind值: ${bind}`);

            if (bind === 1) {
                console.log(`备案状态: ✅ 已备案`);
                if (response.time) {
                    console.log(`备案时间: ${new Date(response.time * 1000).toLocaleString()}`);
                }
                return true;
            } else if (bind === 0) {
                console.log(`备案状态: ❌ 未备案`);
                console.log(`\n提示: 需要完成授权备案才能使用商品搜索等API`);
                return false;
            }
        }

        console.log('响应:', JSON.stringify(result, null, 2));
    }
    console.log('❌ 无法确定备案状态，默认为未备案');
    return false;
}

/**
 * 测试11: 生成授权备案链接
 */
async function test11_GenerateAuthorityUrl(pid) {
    console.log('\n' + '='.repeat(60));
    console.log('测试11: 生成授权备案链接');
    console.log('='.repeat(60));

    if (!pid) {
        console.log('⚠️  跳过: 没有推广位PID');
        return;
    }

    // 使用pdd.ddk.rp.prom.url.generate (channel_type=10)
    console.log('\n使用API: pdd.ddk.rp.prom.url.generate (channel_type=10)\n');

    const result = await callApi('pdd.ddk.rp.prom.url.generate', {
        p_id_list: JSON.stringify([pid]),
        channel_type: 10,
        generate_short_url: 'true'
    });

    if (result && !result.error_response) {
        console.log('✅ API调用成功\n');

        // 响应字段可能是 rp_promotion_url_generate_response 或 rp_prom_url_generate_response
        const response = result.rp_promotion_url_generate_response || result.rp_prom_url_generate_response;
        if (response) {
            // 检查各种可能的字段
            if (response.url_list && response.url_list.length > 0) {
                const urlInfo = response.url_list[0];
                const url = urlInfo.url || urlInfo.short_url || urlInfo.we_app_webview_url || urlInfo.mobile_url;

                if (url) {
                    console.log(`\n📱 授权备案链接:`);
                    console.log(`   普通链接: ${urlInfo.url || '无'}`);
                    console.log(`   短链接: ${urlInfo.short_url || '无'}`);
                    console.log(`   移动端短链接: ${urlInfo.mobile_short_url || '无'}`);
                    console.log(`\n💡 推荐使用短链接，复制以下链接在微信中打开:\n`);
                    console.log(`   ${urlInfo.short_url || urlInfo.url}`);
                    console.log(`\n完成授权后，商品搜索等API将可正常使用！`);
                    return;
                }
            }

            if (response.url) {
                console.log(`\n📱 授权备案链接: ${response.url}`);
                return;
            }
        }

        // 调试：显示完整响应
        console.log('响应结构:', JSON.stringify(result, null, 2));
    }

    // 如果无法生成链接，提供手动操作的指引
    console.log('\n❌ 无法通过API生成授权链接');
    console.log('\n请按以下步骤手动完成授权备案:\n');
    console.log('1. 访问多多进宝: https://jinbao.pinduoduo.com/');
    console.log('2. 登录拼多多账号');
    console.log('3. 进入「推广管理」→「推广位管理」');
    console.log('4. 选择推广位完成授权备案');
    console.log('\n或查看授权备案说明:');
    console.log('https://jinbao.pinduoduo.com/qa-system?questionId=204');
}

/**
 * 测试12: 获取商品标签
 */
async function test12_GetGoodsOpt() {
    console.log('\n' + '='.repeat(60));
    console.log('测试12: 获取商品标签 (pdd.goods.opt.get)');
    console.log('='.repeat(60));

    const result = await callApi('pdd.goods.opt.get', {
        parent_opt_id: 0
    });

    if (result) {
        const optList = result.goods_opt_get_response?.goods_opt_list || [];
        console.log(`\n✅ 获取到 ${optList.length} 个一级标签\n`);

        console.log('📋 商品标签列表 (前10个):');
        optList.slice(0, 10).forEach((opt, i) => {
            console.log(`   ${i + 1}. opt_id: ${opt.opt_id}, 名称: ${opt.opt_name}`);
        });
    }
}

/**
 * 主测试函数
 */
async function runAllTests() {
    console.log('\n╔════════════════════════════════════════════════════════════╗');
    console.log('║              拼多多API完整测试                                 ║');
    console.log('╚════════════════════════════════════════════════════════════╝');

    // 使用用户授权过的推广位PID
    const AUTHORIZED_PID = '44136818_314571462';  // 这个PID用户已授权
    console.log(`\n📝 配置信息:`);
    console.log(`   Client ID: ${CLIENT_ID}`);
    console.log(`   网关地址: ${GATEWAY_URL}`);
    console.log(`   使用已授权PID: ${AUTHORIZED_PID}`);

    console.log(`\n📝 配置信息:`);
    console.log(`   Client ID: ${CLIENT_ID}`);
    console.log(`   网关地址: ${GATEWAY_URL}`);

    // 存储测试数据供后续使用
    let pid = AUTHORIZED_PID;  // 使用已授权的PID
    let goodsSign = null;

    try {
        // 测试1: 获取类目
        await test1_GetCategories();

        // 等待一下避免限流
        await new Promise(r => setTimeout(r, 1000));

        // 测试2: 获取推广位列表
        await test2_GetPidList();

        await new Promise(r => setTimeout(r, 1000));

        // 测试3: 跳过创建新推广位，使用已授权的
        console.log('\n⏭️  跳过创建新推广位，使用已授权的推广位进行测试');

        await new Promise(r => setTimeout(r, 1000));

        // 测试4: 基础搜索（使用已授权PID）
        goodsSign = await test4_SearchBasic(pid);

        await new Promise(r => setTimeout(r, 1000));

        // 测试5: 高级筛选
        await test5_SearchAdvanced(pid);

        await new Promise(r => setTimeout(r, 1000));

        // 测试6: 佣金筛选
        await test6_SearchByCommission(pid);

        await new Promise(r => setTimeout(r, 1000));

        // 测试7: 商品详情
        await test7_GetDetail(goodsSign, pid);

        await new Promise(r => setTimeout(r, 1000));

        // 测试8: 生成基础推广链接
        await test8_GenerateUrlBasic(goodsSign, pid);

        await new Promise(r => setTimeout(r, 1000));

        // 测试9: 生成微信小程序推广
        await test9_GenerateUrlWechat(goodsSign, pid);

        await new Promise(r => setTimeout(r, 1000));

        // 测试10: 查询备案状态（使用已授权PID）
        console.log('\n📌 检查已授权推广位的状态...');
        const isAuthorized = await test10_QueryAuthorityStatus(AUTHORIZED_PID);

        if (!isAuthorized) {
            await new Promise(r => setTimeout(r, 1000));
            // 测试11: 生成授权链接
            await test11_GenerateAuthorityUrl(pid);
        }

        await new Promise(r => setTimeout(r, 1000));

        // 测试12: 获取商品标签
        await test12_GetGoodsOpt();

        // 测试总结
        console.log('\n' + '='.repeat(60));
        console.log('📊 测试总结');
        console.log('='.repeat(60));
        console.log('✅ 全部测试完成！');
        console.log('\n注意事项:');
        console.log('1. 商品搜索API需要推广位授权备案');
        console.log('2. 如遇60001错误，请访问: https://jinbao.pinduoduo.com/qa-system?questionId=204');
        console.log('3. 建议API调用频率不超过50次/分钟');
        console.log('='.repeat(60));

    } catch (error) {
        console.error('\n❌ 测试失败:', error);
    }
}

// 运行测试
runAllTests().catch(console.error);
