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
    section: Optional[str] = None,
    key: str,
    default: Optional[Any] = None,
) -> Optional[Any]:
    """
    获取配置值，支持 Streamlit Cloud Secrets 和 .env 文件

    Args:
        section: 配置节名称 (如 "llm", "pdd", "database")，用于嵌套格式
        key: 配置键名 (如 "api_key", "client_id")
        default: 默认值

    Returns:
        配置值，如果未找到则返回默认值

    Examples:
        # 嵌套格式: [llm] api_key = "sk-..."
        get_config("llm", "api_key") -> "sk-..."

        # 扁平格式: LLM_API_KEY=sk-...
        get_config(key="api_key", env_prefix="LLM_") -> "sk-..."
    """
    try:
        import streamlit as st
    except ImportError:
        st = None

    # 1. 尝试从 Streamlit Secrets 读取 (嵌套格式)
    if st is not None and hasattr(st, 'secrets'):
        secrets = st.secrets

        # 尝试嵌套访问: secrets.llm.api_key
        if section and section in secrets:
            section_data = secrets[section]
            if key in section_data:
                return section_data[key]

        # 尝试扁平访问: secrets.LLM_API_KEY
        env_key = f"{section.upper()}_{key.upper()}" if section else key.upper()
        if env_key in secrets:
            return secrets[env_key]

    # 2. 回退到环境变量 (扁平格式)
    env_key = f"{section.upper()}_{key.upper()}" if section else key.upper()
    value = os.getenv(env_key, default)

    return value


# LLM 配置快捷方法
def get_llm_config() -> dict:
    """获取 LLM 配置"""
    return {
        "api_key": get_config("llm", "api_key", ""),
        "base_url": get_config("llm", "base_url", ""),
        "model": get_config("llm", "model", "gpt-4o-mini"),
    }


# PDD 配置快捷方法
def get_pdd_config() -> dict:
    """获取拼多多 API 配置"""
    return {
        "client_id": get_config("pdd", "client_id", ""),
        "client_secret": get_config("pdd", "client_secret", ""),
        "pid": get_config("pdd", "pid", ""),
    }


# 数据库配置快捷方法
def get_database_url(default: str = "sqlite:///data/pdd.db") -> str:
    """获取数据库 URL"""
    return get_config("database", "url", default)
