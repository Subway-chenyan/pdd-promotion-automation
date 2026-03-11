"""
数据库操作
"""
import sqlite3
import json
from typing import List, Optional
from datetime import datetime
from models import GenerationResult, PromptTemplate
import os


class Database:
    """SQLite数据库操作"""

    def __init__(self, db_path: str = "data/pdd.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 历史记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keywords TEXT,
                goods_count INTEGER,
                result_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 提示词模板表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                template_name TEXT,
                system_prompt TEXT,
                user_prompt_template TEXT,
                is_default BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 商品缓存表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goods_cache (
                goods_sign TEXT PRIMARY KEY,
                goods_data TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 插入默认提示词模板
        cursor.execute("SELECT COUNT(*) as cnt FROM prompt_templates")
        if cursor.fetchone()["cnt"] == 0:
            self._insert_default_prompts(cursor)

        conn.commit()
        conn.close()

    def _insert_default_prompts(self, cursor):
        """插入默认提示词模板"""
        default_prompts = [
            {
                "agent_name": "selector",
                "template_name": "默认选品",
                "system_prompt": "你是一个专业的商品选品经理，擅长从拼多多平台筛选高性价比商品。你需要根据关键词搜索商品，并按照性价比、销量、优惠等标准筛选。",
                "user_prompt_template": "根据以下要求选品：\n关键词: {keywords}\n数量: {count}",
                "is_default": 1,
            },
            {
                "agent_name": "operator",
                "template_name": "默认操作员",
                "system_prompt": "你是商品信息处理专员，负责获取商品详情并生成推广链接。你需要整理商品信息，包括价格、优惠券、佣金、销量等关键数据。",
                "user_prompt_template": "处理以下商品列表，获取详情和推广链接",
                "is_default": 1,
            },
            {
                "agent_name": "copywriter",
                "template_name": "默认文案师",
                "system_prompt": "你是一位资深的电商文案策划，擅长创作吸引人的推广文案。你的文案风格包括：简洁直接、紧迫感、专业风、生活化。你需要根据商品类型自动选择最合适的风格，并在文案中适当使用emoji。",
                "user_prompt_template": "为以下商品生成推广文案\n商品信息：{goods_info}\n风格要求：{style}",
                "is_default": 1,
            },
        ]

        for prompt in default_prompts:
            cursor.execute("""
                INSERT INTO prompt_templates
                (agent_name, template_name, system_prompt, user_prompt_template, is_default)
                VALUES (?, ?, ?, ?, ?)
            """, (
                prompt["agent_name"],
                prompt["template_name"],
                prompt["system_prompt"],
                prompt["user_prompt_template"],
                prompt["is_default"],
            ))

    # 历史记录操作

    def save_history(self, keywords: List[str], count: int, result: dict) -> int:
        """保存生成历史"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO generation_history (keywords, goods_count, result_json)
            VALUES (?, ?, ?)
        """, (json.dumps(keywords), count, json.dumps(result, ensure_ascii=False)))

        row_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return row_id

    def get_history(self, limit: int = 20) -> List[dict]:
        """获取历史记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, keywords, goods_count, result_json, created_at
            FROM generation_history
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row["id"],
                "keywords": json.loads(row["keywords"]),
                "goods_count": row["goods_count"],
                "result": json.loads(row["result_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    # 提示词模板操作

    def get_prompt_templates(self, agent_name: Optional[str] = None) -> List[PromptTemplate]:
        """获取提示词模板"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if agent_name:
            cursor.execute("""
                SELECT id, agent_name, template_name, system_prompt, user_prompt_template, is_default, created_at
                FROM prompt_templates
                WHERE agent_name = ?
                ORDER BY is_default DESC, created_at DESC
            """, (agent_name,))
        else:
            cursor.execute("""
                SELECT id, agent_name, template_name, system_prompt, user_prompt_template, is_default, created_at
                FROM prompt_templates
                ORDER BY agent_name, is_default DESC, created_at DESC
            """)

        rows = cursor.fetchall()
        conn.close()

        return [
            PromptTemplate(
                id=row["id"],
                agent_name=row["agent_name"],
                template_name=row["template_name"],
                system_prompt=row["system_prompt"],
                user_prompt_template=row["user_prompt_template"],
                is_default=bool(row["is_default"]),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            )
            for row in rows
        ]

    def save_prompt_template(self, template: PromptTemplate) -> int:
        """保存提示词模板"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if template.id:
            # 更新
            cursor.execute("""
                UPDATE prompt_templates
                SET agent_name = ?, template_name = ?, system_prompt = ?, user_prompt_template = ?, is_default = ?
                WHERE id = ?
            """, (
                template.agent_name,
                template.template_name,
                template.system_prompt,
                template.user_prompt_template,
                template.is_default,
                template.id,
            ))
            row_id = template.id
        else:
            # 新建
            cursor.execute("""
                INSERT INTO prompt_templates (agent_name, template_name, system_prompt, user_prompt_template, is_default)
                VALUES (?, ?, ?, ?, ?)
            """, (
                template.agent_name,
                template.template_name,
                template.system_prompt,
                template.user_prompt_template,
                template.is_default,
            ))
            row_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return row_id

    def delete_prompt_template(self, template_id: int) -> bool:
        """删除提示词模板"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM prompt_templates WHERE id = ?", (template_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    # 商品缓存操作

    def cache_goods(self, goods_sign: str, goods_data: dict):
        """缓存商品数据"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO goods_cache (goods_sign, goods_data)
            VALUES (?, ?)
        """, (goods_sign, json.dumps(goods_data, ensure_ascii=False)))

        conn.commit()
        conn.close()

    def get_cached_goods(self, goods_sign: str) -> Optional[dict]:
        """获取缓存的商品数据"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT goods_data FROM goods_cache WHERE goods_sign = ?
        """, (goods_sign,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row["goods_data"])
        return None
