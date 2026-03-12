"""
配置加载 - 支持 Streamlit Cloud Secrets 和本地 .env 文件

Streamlit Cloud Secrets 格式 (嵌套):
    [llm]
    api_key = "sk-..."
    base_url = "http://..."
    model = "qwen3-max"

本地 .env 格式 (扁平):
    LLM_API_KEY=sk-...
    LLM_BASE_URL=http://...
    LLM_MODEL=qwen3-max
"""
import os
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()


def get_config(
    key: str,
    section: Optional[str] = None,
    default: Optional[Any] = None,
) -> Optional[Any]:
    """
    获取配置值，支持 Streamlit Cloud Secrets 和 .env 文件

    Args:
        key: 配置键名 (如 "api_key", "client_id")
        section: 配置节名称 (如 "llm", "pdd", "database")，用于嵌套格式
        default: 默认值

    Returns:
        配置值，如果未找到则返回默认值

    Examples:
        # 嵌套格式: [llm] api_key = "sk-..."
        get_config("api_key", "llm") -> "sk-..."

        # 扁平格式: LLM_API_KEY=sk-...
        get_config("api_key", "LLM") -> "sk-..."
    """
    try:
        import streamlit as st
    except ImportError:
        st = None

    # 1. 首先尝试环境变量 (最高优先级，用于本地开发和覆盖)
    env_key = f"{section.upper()}_{key.upper()}" if section else key.upper()
    env_value = os.getenv(env_key)
    if env_value is not None:
        return env_value

    # 2. 尝试从 Streamlit Secrets 读取
    if st is not None and hasattr(st, 'secrets'):
        secrets = st.secrets

        # 尝试嵌套访问: secrets.llm.api_key
        if section and section in secrets:
            section_data = secrets[section]
            if key in section_data:
                return section_data[key]

        # 尝试扁平访问: secrets.LLM_API_KEY
        if env_key in secrets:
            return secrets[env_key]

        # 尝试直接用 section.key 格式访问
        if section:
            direct_key = f"{section}.{key}"
            if direct_key in secrets:
                return secrets[direct_key]

    # 3. 返回默认值
    return default


# LLM 配置快捷方法
def get_llm_config() -> dict:
    """获取 LLM 配置"""
    return {
        "api_key": get_config("api_key", "llm", ""),
        "base_url": get_config("base_url", "llm", ""),
        "model": get_config("model", "llm", "gpt-4o-mini"),
    }


# PDD 配置快捷方法
def get_pdd_config() -> dict:
    """获取拼多多 API 配置"""
    return {
        "client_id": get_config("client_id", "pdd", ""),
        "client_secret": get_config("client_secret", "pdd", ""),
        "pid": get_config("pid", "pdd", ""),
    }


# 数据库配置快捷方法
def get_database_url(default: str = "sqlite:///data/pdd.db") -> str:
    """获取数据库 URL"""
    url = get_config("url", "database", default)

    # 调试：打印数据库 URL（在 Streamlit Cloud 中会显示在日志中）
    print(f"[DEBUG] Database URL: {url[:20]}...{url[-10:] if len(url) > 30 else url}")

    return url
