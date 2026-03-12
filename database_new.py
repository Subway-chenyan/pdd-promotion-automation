"""
数据库操作 - SQLAlchemy + PostgreSQL
"""
import os
import json
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from models import GenerationResult, PromptTemplate


def _get_database_url(default: str = "sqlite:///data/pdd.db") -> str:
    """获取数据库 URL（懒加载）"""
    from config import get_database_url
    return get_database_url(default)

Base = declarative_base()


# ORM 模型定义
class GenerationHistory(Base):
    """历史记录表"""
    __tablename__ = 'generation_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    keywords = Column(Text, nullable=False)
    goods_count = Column(Integer, nullable=False)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))


class PromptTemplateDB(Base):
    """提示词模板表"""
    __tablename__ = 'prompt_templates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(50), nullable=False)
    template_name = Column(String(100), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))


class GoodsCache(Base):
    """商品缓存表"""
    __tablename__ = 'goods_cache'

    goods_sign = Column(String(100), primary_key=True)
    goods_data = Column(Text, nullable=False)
    cached_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))


class Database:
    """PostgreSQL 数据库操作"""

    def __init__(self, database_url: str = None):
        if database_url is None:
            database_url = _get_database_url()

        # 打印数据库连接信息（隐藏敏感信息）
        print(f"[Database] Connecting to: {self._mask_url(database_url)}")

        # PostgreSQL 连接参数
        if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
            # 添加 SSL 模式（Supabase 需要）
            if "sslmode" not in database_url:
                database_url += "?sslmode=require"

        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._init_db()

    @staticmethod
    def _mask_url(url: str) -> str:
        """隐藏数据库 URL 中的敏感信息"""
        if "://" not in url:
            return url
        # 隐藏密码部分
        parts = url.split("://")
        if len(parts) == 2:
            scheme, rest = parts
            if "@" in rest:
                auth, host = rest.split("@", 1)
                if ":" in auth:
                    user, _ = auth.split(":", 1)
                    return f"{scheme}://{user}:***@{host}"
            return f"{scheme}://***@{rest.split('@')[1] if '@' in rest else rest}"
        return url[:20] + "..."

    def _get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    def _init_db(self):
        """初始化数据库表"""
        # 检查是否是 PostgreSQL
        is_postgresql = 'postgres' in str(self.engine.url)

        if is_postgresql:
            # PostgreSQL: 使用 SERIAL 实现自增
            Base.metadata.create_all(self.engine)
        else:
            # SQLite: 使用 INTEGER PRIMARY KEY AUTOINCREMENT
            Base.metadata.create_all(self.engine)

        # 插入默认提示词模板
        session = self._get_session()
        try:
            existing_count = session.query(PromptTemplateDB).count()
            if existing_count == 0:
                self._insert_default_prompts(session)
            session.commit()
        finally:
            session.close()

    def _insert_default_prompts(self, session: Session):
        """插入默认提示词模板"""
        default_prompts = [
            {
                "agent_name": "selector",
                "template_name": "默认选品",
                "system_prompt": "你是一个专业的商品选品经理，擅长从拼多多平台筛选高性价比商品。你需要根据关键词搜索商品，并按照性价比、销量、优惠等标准筛选。",
                "user_prompt_template": "根据以下要求选品：\n关键词: {keywords}\n数量: {count}",
                "is_default": True,
            },
            {
                "agent_name": "operator",
                "template_name": "默认操作员",
                "system_prompt": "你是商品信息处理专员，负责获取商品详情并生成推广链接。你需要整理商品信息，包括价格、优惠券、佣金、销量等关键数据。",
                "user_prompt_template": "处理以下商品列表，获取详情和推广链接",
                "is_default": True,
            },
            {
                "agent_name": "copywriter",
                "template_name": "默认文案师",
                "system_prompt": "你是一位资深的电商文案策划，擅长创作吸引人的推广文案。你的文案风格包括：简洁直接、紧迫感、专业风、生活化。你需要根据商品类型自动选择最合适的风格，并在文案中适当使用emoji。",
                "user_prompt_template": "为以下商品生成推广文案\n商品信息：{goods_info}\n风格要求：{style}",
                "is_default": True,
            },
        ]

        for prompt in default_prompts:
            db_prompt = PromptTemplateDB(**prompt)
            session.add(db_prompt)

    # 历史记录操作

    def save_history(self, keywords: List[str], count: int, result: dict) -> int:
        """保存生成历史"""
        session = self._get_session()
        try:
            history = GenerationHistory(
                keywords=json.dumps(keywords),
                goods_count=count,
                result_json=json.dumps(result, ensure_ascii=False)
            )
            session.add(history)
            session.commit()
            session.refresh(history)
            return history.id
        finally:
            session.close()

    def get_history(self, limit: int = 20) -> List[dict]:
        """获取历史记录"""
        session = self._get_session()
        try:
            records = session.query(GenerationHistory).order_by(
                GenerationHistory.created_at.desc()
            ).limit(limit).all()

            return [
                {
                    "id": r.id,
                    "keywords": json.loads(r.keywords),
                    "goods_count": r.goods_count,
                    "result": json.loads(r.result_json),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        finally:
            session.close()

    # 提示词模板操作

    def get_prompt_templates(self, agent_name: Optional[str] = None) -> List[PromptTemplate]:
        """获取提示词模板"""
        session = self._get_session()
        try:
            query = session.query(PromptTemplateDB)
            if agent_name:
                query = query.filter(PromptTemplateDB.agent_name == agent_name)
                query = query.order_by(PromptTemplateDB.is_default.desc(), PromptTemplateDB.created_at.desc())
            else:
                query = query.order_by(PromptTemplateDB.agent_name, PromptTemplateDB.is_default.desc(), PromptTemplateDB.created_at.desc())

            records = query.all()

            return [
                PromptTemplate(
                    id=r.id,
                    agent_name=r.agent_name,
                    template_name=r.template_name,
                    system_prompt=r.system_prompt,
                    user_prompt_template=r.user_prompt_template,
                    is_default=bool(r.is_default),
                    created_at=r.created_at,
                )
                for r in records
            ]
        finally:
            session.close()

    def save_prompt_template(self, template: PromptTemplate) -> int:
        """保存提示词模板"""
        session = self._get_session()
        try:
            if template.id:
                # 更新
                record = session.query(PromptTemplateDB).filter(PromptTemplateDB.id == template.id).first()
                if record:
                    record.agent_name = template.agent_name
                    record.template_name = template.template_name
                    record.system_prompt = template.system_prompt
                    record.user_prompt_template = template.user_prompt_template
                    record.is_default = template.is_default
                    session.commit()
                    return template.id
            else:
                # 新建
                record = PromptTemplateDB(
                    agent_name=template.agent_name,
                    template_name=template.template_name,
                    system_prompt=template.system_prompt,
                    user_prompt_template=template.user_prompt_template,
                    is_default=template.is_default,
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                return record.id
        finally:
            session.close()

    def delete_prompt_template(self, template_id: int) -> bool:
        """删除提示词模板"""
        session = self._get_session()
        try:
            record = session.query(PromptTemplateDB).filter(PromptTemplateDB.id == template_id).first()
            if record:
                session.delete(record)
                session.commit()
                return True
            return False
        finally:
            session.close()

    # 商品缓存操作

    def cache_goods(self, goods_sign: str, goods_data: dict):
        """缓存商品数据"""
        session = self._get_session()
        try:
            # 使用 merge 实现 upsert
            record = GoodsCache(
                goods_sign=goods_sign,
                goods_data=json.dumps(goods_data, ensure_ascii=False)
            )
            session.merge(record)
            session.commit()
        finally:
            session.close()

    def get_cached_goods(self, goods_sign: str) -> Optional[dict]:
        """获取缓存的商品数据"""
        session = self._get_session()
        try:
            record = session.query(GoodsCache).filter(GoodsCache.goods_sign == goods_sign).first()
            if record:
                return json.loads(record.goods_data)
            return None
        finally:
            session.close()
