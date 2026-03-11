"""
Streamlit 前端
"""
import streamlit as st
import os
import asyncio
from typing import List, Dict
from dotenv import load_dotenv
import datetime

from coordinator import Coordinator
from models import CopyResult

load_dotenv()

# 页面配置
st.set_page_config(
    page_title="拼多多商品推广自动化系统",
    page_icon="🛒",
    layout="wide",
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .result-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        background: #fafafa;
    }
    .copy-text {
        background: #f0f0f0;
        padding: 1rem;
        border-radius: 5px;
        white-space: pre-wrap;
        font-family: monospace;
        user-select: all;
    }
    .product-image {
        max-width: 200px;
        max-height: 200px;
        object-fit: contain;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    .image-container {
        text-align: center;
        padding: 1rem;
    }
    .copy-all-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ==================== 初始化 ====================

@st.cache_resource
def get_coordinator():
    """获取协调器实例"""
    return Coordinator()


def init_session_state():
    """初始化session state"""
    if "results" not in st.session_state:
        st.session_state.results = []
    if "show_prompts" not in st.session_state:
        st.session_state.show_prompts = False
    if "custom_prompts" not in st.session_state:
        st.session_state.custom_prompts = {}


init_session_state()
coordinator = get_coordinator()


# ==================== 辅助函数 ====================

def format_single_result(result: CopyResult) -> str:
    """格式化单条结果为文本"""
    image_note = f"📷 图片: {result.image_url}" if result.image_url else ""
    return f"""🔥 {result.goods_name}
{image_note}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 价格: ¥{result.price} | 优惠券: ¥{result.coupon} | 券后价: ¥{result.final_price} | 销量: {result.sales}

📝 推广文案:
{result.copy_text}

🔗 推广链接:
{result.short_url or '暂无短链接'}

"""


def format_all_results(results: List[CopyResult]) -> str:
    """格式化所有结果为文本"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = f"拼多多推广文案生成结果\n生成时间: {timestamp}\n{'='*50}\n\n"

    for i, result in enumerate(results, 1):
        output += f"[{i}] {format_single_result(result)}\n"

    return output


def display_copy_result(result: CopyResult, index: int):
    """显示单条文案结果（含图片）"""
    with st.container():
        st.markdown(f"""
        <div class="result-card">
            <h3>🔥 {result.goods_name}</h3>
            <hr>
        </div>
        """, unsafe_allow_html=True)

        # 图片和指标并排显示
        col_image, col_metrics = st.columns([1, 3])

        with col_image:
            # 显示商品图片
            if result.image_url:
                st.markdown('<div class="image-container">', unsafe_allow_html=True)
                st.image(result.image_url, width=200, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("暂无图片")

        with col_metrics:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("价格", f"¥{result.price}")
            with col2:
                st.metric("优惠券", f"¥{result.coupon}")
            with col3:
                st.metric("券后价", f"¥{result.final_price}")
            with col4:
                st.metric("销量", result.sales)

        st.markdown("**📝 推广文案:**")
        formatted_text = format_single_result(result)
        st.text_area(
            "",
            value=result.copy_text,
            height=100,
            key=f"copy_text_area_{index}",
            label_visibility="collapsed",
            help="点击文本框右侧的复制按钮"
        )

        st.markdown("**🔗 推广链接:**")
        st.code(result.short_url or "暂无短链接", language="")

        # 图片链接
        if result.image_url:
            with st.expander("📷 查看图片链接", expanded=False):
                st.code(result.image_url, language="")

        # 下载单条
        st.download_button(
            label="📥 下载此条",
            data=formatted_text,
            file_name=f"推广文案_{index+1}.txt",
            mime="text/plain",
            key=f"download_{index}"
        )


def display_copy_all_section():
    """显示一键全部复制/下载区域"""
    if not st.session_state.results:
        return

    st.markdown("---")
    st.markdown("""
    <div class="copy-all-section">
        <h2 style="color: white; text-align: center;">📋 一键获取所有结果</h2>
    </div>
    """, unsafe_allow_html=True)

    # 生成所有结果的文本
    all_text = format_all_results(st.session_state.results)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📝 所有文案（可复制）")
        st.text_area(
            "",
            value=all_text,
            height=200,
            key="all_results_text",
            label_visibility="collapsed",
            help="选中全部文本后 Ctrl+C 复制"
        )

    with col2:
        st.markdown("### 📥 下载全部")
        st.download_button(
            label="⬇️ 下载所有文案为TXT文件",
            data=all_text,
            file_name=f"推广文案_全部_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )

        st.markdown("---")

        # 也提供Markdown格式下载
        md_text = format_all_results_as_markdown(st.session_state.results)
        st.download_button(
            label="⬇️ 下载为Markdown格式",
            data=md_text,
            file_name=f"推广文案_全部_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True
        )

    st.markdown("---")
    st.info("💡 **提示**: 点击上方文本框后按 Ctrl+A 全选，再按 Ctrl+C 即可复制全部内容！")


def format_all_results_as_markdown(results: List[CopyResult]) -> str:
    """格式化为Markdown"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = f"# 拼多多推广文案\n\n**生成时间**: {timestamp}\n\n---\n\n"

    for i, result in enumerate(results, 1):
        # 添加图片
        image_md = ""
        if result.image_url:
            image_md = f"\n![商品图片]({result.image_url})\n"

        output += f"""## {i}. {result.goods_name}
{image_md}
| 项目 | 内容 |
|------|------|
| 价格 | ¥{result.price} |
| 优惠券 | ¥{result.coupon} |
| 券后价 | ¥{result.final_price} |
| 销量 | {result.sales} |

### 推广文案

```
{result.copy_text}
```

### 推广链接

{result.short_url or '暂无短链接'}

---
"""

    return output


def format_history_results(history_item: dict) -> str:
    """格式化历史记录为文本"""
    keywords = history_item.get('keywords', [])
    count = history_item.get('goods_count', 0)
    results = history_item.get('result', {}).get('results', [])
    created_at = history_item.get('created_at', '')

    output = f"拼多多推广文案 - 历史记录\n"
    output += f"关键词: {' | '.join(keywords)}\n"
    output += f"生成时间: {created_at}\n"
    output += f"{'='*50}\n\n"

    for i, result in enumerate(results, 1):
        output += f"[{i}] 🔥 {result.get('goods_name', '未知商品')}\n"
        output += f"💰 价格: ¥{result.get('price', '0')} | 优惠券: ¥{result.get('coupon', '0')} | 券后价: ¥{result.get('final_price', '0')}\n\n"
        output += f"📝 文案:\n{result.get('copy_text', '')}\n\n"
        output += f"🔗 链接: {result.get('short_url', '无')}\n"
        output += f"{'-'*30}\n\n"

    return output


def display_history():
    """显示历史记录（含复制/下载功能）"""
    st.markdown("### 📊 历史记录")

    history = coordinator.get_history(limit=10)

    if not history:
        st.info("暂无历史记录")
        return

    for item in history:
        # 提取结果信息
        keywords = item.get('keywords', [])
        count = item.get('goods_count', 0)
        created_at = item.get('created_at', '')
        results = item.get('result', {}).get('results', [])

        # 标题栏
        title = f"{' | '.join(keywords)} - {count}个商品 - {created_at}"

        # 展开内容
        with st.expander(title, expanded=False):
            # 显示简要信息
            for r in results[:3]:
                goods_name = r.get('goods_name', '未知')
                copy_text = r.get('copy_text', '')
                preview = copy_text[:50] + "..." if len(copy_text) > 50 else copy_text
                st.markdown(f"- **{goods_name}**: {preview}")

            # 操作按钮
            col1, col2, col3 = st.columns(3)

            with col1:
                # 查看详情
                if st.button(f"👀 查看详情", key=f"view_{item.get('id')}"):
                    st.session_state[f"history_detail_{item.get('id')}"] = True

            with col2:
                # 下载此条历史
                history_text = format_history_results(item)
                st.download_button(
                    label="📥 下载",
                    data=history_text,
                    file_name=f"历史记录_{'_'.join(keywords)}_{created_at.replace(':', '-')}.txt",
                    mime="text/plain",
                    key=f"download_history_{item.get('id')}"
                )

            with col3:
                # 复制文本（用文本框）
                if results:
                    # 只显示第一个结果作为可复制文本
                    first_result = results[0]
                    copy_text = f"{first_result.get('goods_name', '')}\n\n{first_result.get('copy_text', '')}\n\n{first_result.get('short_url', '')}"
                    st.text_area(
                        "",
                        value=copy_text,
                        height=80,
                        key=f"history_copy_{item.get('id')}",
                        label_visibility="collapsed"
                    )

            # 详情查看
            if st.session_state.get(f"history_detail_{item.get('id')}", False):
                st.markdown("---")
                st.markdown(f"### 📋 完整内容")

                # 复制全部
                all_history_text = format_history_results(item)
                st.text_area(
                    "全部内容（可复制）",
                    value=all_history_text,
                    height=200,
                    key=f"history_all_{item.get('id')}",
                    label_visibility="collapsed"
                )

                # 显示所有结果详情
                for i, r in enumerate(results):
                    st.markdown(f"""
                    <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; margin: 0.5rem 0;">
                        <h4>{i+1}. {r.get('goods_name', '未知商品')}</h4>
                        <p>💰 价格: ¥{r.get('price', '0')} | 优惠券: ¥{r.get('coupon', '0')} | 券后价: ¥{r.get('final_price', '0')}</p>
                        <p>📝 <strong>文案:</strong></p>
                        <pre>{r.get('copy_text', '')}</pre>
                        <p>🔗 <strong>链接:</strong> {r.get('short_url', '无')}</p>
                    </div>
                    """, unsafe_allow_html=True)

                # 关闭详情按钮
                if st.button(f"关闭详情", key=f"close_{item.get('id')}"):
                    st.session_state[f"history_detail_{item.get('id')}"] = False
                    st.rerun()


def display_prompts_editor():
    """显示提示词编辑器"""
    st.markdown("### ✏️ 提示词编辑器")

    # 获取当前提示词
    prompts = coordinator.get_prompt_templates()

    # AI-1 选品经理
    with st.expander("🤖 AI-1 选品经理", expanded=False):
        selector_prompts = prompts["selector"]
        current_system = coordinator.selector.system_prompt
        current_user = coordinator.selector.user_prompt_template

        new_system = st.text_area(
            "系统提示词",
            value=current_system,
            key="selector_system",
            height=100,
        )
        new_user = st.text_area(
            "用户提示词模板",
            value=current_user,
            key="selector_user",
            height=100,
        )

        if st.button("应用选品经理提示词", key="apply_selector"):
            coordinator.selector.update_prompts(new_system, new_user)
            st.success("✅ 提示词已更新！")

    # AI-2 操作员
    with st.expander("🤖 AI-2 操作员", expanded=False):
        current_system = coordinator.operator.system_prompt
        current_user = coordinator.operator.user_prompt_template

        new_system = st.text_area(
            "系统提示词",
            value=current_system,
            key="operator_system",
            height=100,
        )
        new_user = st.text_area(
            "用户提示词模板",
            value=current_user,
            key="operator_user",
            height=100,
        )

        if st.button("应用操作员提示词", key="apply_operator"):
            coordinator.operator.update_prompts(new_system, new_user)
            st.success("✅ 提示词已更新！")

    # AI-3 文案师
    with st.expander("🤖 AI-3 文案师", expanded=False):
        current_system = coordinator.copywriter.system_prompt
        current_user = coordinator.copywriter.user_prompt_template

        new_system = st.text_area(
            "系统提示词",
            value=current_system,
            key="copywriter_system",
            height=100,
        )
        new_user = st.text_area(
            "用户提示词模板",
            value=current_user,
            key="copywriter_user",
            height=100,
        )

        if st.button("应用文案师提示词", key="apply_copywriter"):
            coordinator.copywriter.update_prompts(new_system, new_user)
            st.success("✅ 提示词已更新！")


# ==================== 主界面 ====================

def main():
    """主界面"""
    # 标题
    st.markdown("""
    <div class="main-header">
        <h1>🛒 拼多多商品推广自动化系统</h1>
        <p>基于 LangChain Deep Agents 的智能选品与文案生成</p>
    </div>
    """, unsafe_allow_html=True)

    # 两列布局
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("### 📝 输入区域")

        # 关键词输入
        keywords_input = st.text_area(
            "关键词 (每行一个)",
            placeholder="蓝牙耳机\n充电宝\n数据线",
            height=120,
        )

        # 选品数量和排序方式
        col1, col2, col3 = st.columns(3)
        with col1:
            count = st.number_input("每个关键词选品个数", min_value=1, max_value=20, value=3)
        with col2:
            sort_type = st.selectbox(
                "选品排序",
                options=list(coordinator.get_available_sort_types().keys()),
                format_func=lambda x: coordinator.get_available_sort_types()[x],
                index=0,
            )
        with col3:
            style_hint = st.selectbox(
                "文案风格",
                options=["自动生成", "简洁", "紧迫", "专业", "生活"],
                index=0,
            )

        # 生成按钮
        if st.button("🚀 生成推广文案", type="primary", use_container_width=True):
            if not keywords_input.strip():
                st.error("请输入至少一个关键词")
                return

            keywords = [k.strip() for k in keywords_input.strip().split("\n") if k.strip()]

            # 显示进度
            with st.spinner("正在处理..."):
                try:
                    # 创建新的事件循环
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    results = loop.run_until_complete(
                        coordinator.process(
                            keywords=keywords,
                            count=count,
                            style_hint=style_hint,
                            sort_type=sort_type,
                        )
                    )

                    loop.close()

                    st.session_state.results = results

                    if results:
                        st.success(f"✅ 成功生成 {len(results)} 条推广文案！")
                    else:
                        st.warning("⚠️ 未找到符合条件的商品，请尝试其他关键词")

                except Exception as e:
                    st.error(f"❌ 处理失败: {str(e)}")

        # 显示结果
        if st.session_state.results:
            # 一键全部复制/下载区域
            display_copy_all_section()

            st.markdown(f"### 📤 输出区域 ({len(st.session_state.results)} 条)")

            for i, result in enumerate(st.session_state.results):
                display_copy_result(result, i)

    with col_right:
        # 提示词编辑器
        if st.checkbox("📝 显示提示词编辑器", key="show_prompts"):
            display_prompts_editor()

        st.markdown("---")

        # 历史记录
        display_history()


if __name__ == "__main__":
    main()
