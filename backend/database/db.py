"""
数据库模块 - SQLite 数据持久化

提供历史记录和模板库的存储功能
"""
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class Database:
    """SQLite 数据库管理类"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径，默认为 ./data/history.db
        """
        if db_path is None:
            # 创建 data 目录
            data_dir = Path("./data")
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "history.db"

        self.db_path = str(db_path)
        self._init_tables()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 历史记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS script_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    product_name TEXT,
                    brand TEXT,
                    keywords TEXT,
                    style TEXT,
                    duration INTEGER,
                    platform TEXT,
                    script_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_favorite BOOLEAN DEFAULT 0
                )
            """)

            # 视频生成历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS video_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    history_id INTEGER,
                    task_id TEXT,
                    model TEXT,
                    aspect_ratio TEXT,
                    status TEXT,
                    video_url TEXT,
                    cover_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (history_id) REFERENCES script_history (id) ON DELETE CASCADE
                )
            """)

            # 批量视频历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_video_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    history_id INTEGER,
                    batch_id TEXT,
                    segments_count INTEGER,
                    status TEXT,
                    merged_video_url TEXT,
                    merged_cover_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (history_id) REFERENCES script_history (id) ON DELETE CASCADE
                )
            """)

            # 模板库表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    product_name TEXT,
                    keywords TEXT,
                    style TEXT,
                    duration INTEGER,
                    platform TEXT,
                    script_data TEXT NOT NULL,
                    is_system BOOLEAN DEFAULT 0,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    UNIQUE(name, category)
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_created ON script_history(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_template_category ON templates(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_template_system ON templates(is_system)")

            conn.commit()
            logger.info(f"数据库初始化完成: {self.db_path}")

    # ==================== 历史记录相关方法 ====================

    def save_script_history(
        self,
        title: str,
        script_data: Dict[str, Any],
        product_info: Dict[str, Any],
        style: str,
        duration: int,
        platform: str,
        is_favorite: bool = False
    ) -> int:
        """
        保存脚本历史记录

        Args:
            title: 标题
            script_data: 脚本数据（JSON）
            product_info: 产品信息
            style: 风格
            duration: 时长
            platform: 平台
            is_favorite: 是否收藏

        Returns:
            历史记录 ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO script_history
                (title, product_name, brand, keywords, style, duration, platform, script_data, is_favorite)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                product_info.get('name', ''),
                product_info.get('brand', ''),
                json.dumps(product_info.get('keywords', []), ensure_ascii=False),
                style,
                duration,
                platform,
                json.dumps(script_data, ensure_ascii=False),
                is_favorite
            ))
            conn.commit()
            return cursor.lastrowid

    def get_script_history(
        self,
        limit: int = 20,
        offset: int = 0,
        favorite_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取脚本历史记录

        Args:
            limit: 返回数量
            offset: 偏移量
            favorite_only: 只返回收藏的

        Returns:
            历史记录列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, title, product_name, brand, keywords, style, duration,
                       platform, created_at, is_favorite
                FROM script_history
            """
            params = []

            if favorite_only:
                query += " WHERE is_favorite = 1"

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    'id': row['id'],
                    'title': row['title'],
                    'product_name': row['product_name'],
                    'brand': row['brand'],
                    'keywords': json.loads(row['keywords']) if row['keywords'] else [],
                    'style': row['style'],
                    'duration': row['duration'],
                    'platform': row['platform'],
                    'created_at': row['created_at'],
                    'is_favorite': bool(row['is_favorite'])
                })

            return results

    def get_script_detail(self, history_id: int) -> Optional[Dict[str, Any]]:
        """
        获取脚本详情

        Args:
            history_id: 历史记录 ID

        Returns:
            脚本详情，如果不存在返回 None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, product_name, brand, keywords, style, duration,
                       platform, script_data, created_at, is_favorite
                FROM script_history
                WHERE id = ?
            """, (history_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'id': row['id'],
                'title': row['title'],
                'product_name': row['product_name'],
                'brand': row['brand'],
                'keywords': json.loads(row['keywords']) if row['keywords'] else [],
                'style': row['style'],
                'duration': row['duration'],
                'platform': row['platform'],
                'script_data': json.loads(row['script_data']),
                'created_at': row['created_at'],
                'is_favorite': bool(row['is_favorite'])
            }

    def update_favorite(self, history_id: int, is_favorite: bool) -> bool:
        """
        更新收藏状态

        Args:
            history_id: 历史记录 ID
            is_favorite: 是否收藏

        Returns:
            是否成功
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE script_history SET is_favorite = ? WHERE id = ?
            """, (is_favorite, history_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_script_history(self, history_id: int) -> bool:
        """
        删除脚本历史记录

        Args:
            history_id: 历史记录 ID

        Returns:
            是否成功
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM script_history WHERE id = ?", (history_id,))
            conn.commit()
            return cursor.rowcount > 0

    def search_history(
        self,
        keyword: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索历史记录

        Args:
            keyword: 搜索关键词
            limit: 返回数量

        Returns:
            历史记录列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, product_name, brand, keywords, style, duration,
                       platform, created_at, is_favorite
                FROM script_history
                WHERE title LIKE ? OR product_name LIKE ? OR keywords LIKE ?
                ORDER BY created_at DESC LIMIT ?
            """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', limit))

            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    'id': row['id'],
                    'title': row['title'],
                    'product_name': row['product_name'],
                    'brand': row['brand'],
                    'keywords': json.loads(row['keywords']) if row['keywords'] else [],
                    'style': row['style'],
                    'duration': row['duration'],
                    'platform': row['platform'],
                    'created_at': row['created_at'],
                    'is_favorite': bool(row['is_favorite'])
                })

            return results

    def get_history_stats(self) -> Dict[str, Any]:
        """
        获取历史记录统计信息

        Returns:
            统计信息
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as total FROM script_history")
            total = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as favorite_count FROM script_history WHERE is_favorite = 1")
            favorite_count = cursor.fetchone()['favorite_count']

            cursor.execute("SELECT style, COUNT(*) as count FROM script_history GROUP BY style")
            style_stats = {row['style']: row['count'] for row in cursor.fetchall()}

            cursor.execute("SELECT platform, COUNT(*) as count FROM script_history GROUP BY platform")
            platform_stats = {row['platform']: row['count'] for row in cursor.fetchall()}

            return {
                'total': total,
                'favorite_count': favorite_count,
                'style_stats': style_stats,
                'platform_stats': platform_stats
            }

    # ==================== 视频历史记录相关方法 ====================

    def save_video_history(
        self,
        history_id: int,
        task_id: str,
        model: str,
        aspect_ratio: str,
        status: str,
        video_url: Optional[str] = None,
        cover_url: Optional[str] = None
    ) -> int:
        """
        保存视频生成历史

        Args:
            history_id: 脚本历史记录 ID
            task_id: 任务 ID
            model: 模型
            aspect_ratio: 宽高比
            status: 状态
            video_url: 视频地址
            cover_url: 封面地址

        Returns:
            记录 ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO video_history
                (history_id, task_id, model, aspect_ratio, status, video_url, cover_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (history_id, task_id, model, aspect_ratio, status, video_url, cover_url))
            conn.commit()
            return cursor.lastrowid

    # ==================== 模板库相关方法 ====================

    def save_template(
        self,
        name: str,
        category: str,
        description: str,
        product_info: Dict[str, Any],
        script_data: Dict[str, Any],
        is_system: bool = False,
        created_by: str = None
    ) -> int:
        """
        保存模板

        Args:
            name: 模板名称
            category: 分类
            description: 描述
            product_info: 产品信息
            script_data: 脚本数据
            is_system: 是否系统模板
            created_by: 创建者

        Returns:
            模板 ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO templates
                (name, category, description, product_name, keywords, style, duration, platform,
                 script_data, is_system, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                category,
                description,
                product_info.get('name', ''),
                json.dumps(product_info.get('keywords', []), ensure_ascii=False),
                product_info.get('style', '活力'),
                product_info.get('duration', 30),
                product_info.get('platform', '抖音'),
                json.dumps(script_data, ensure_ascii=False),
                is_system,
                created_by
            ))
            conn.commit()
            return cursor.lastrowid

    def get_templates(
        self,
        category: Optional[str] = None,
        is_system: Optional[bool] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取模板列表

        Args:
            category: 分类筛选
            is_system: 是否只返回系统模板
            limit: 返回数量

        Returns:
            模板列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, name, category, description, product_name, keywords,
                       style, duration, platform, is_system, created_by,
                       created_at, usage_count
                FROM templates
            """
            params = []

            conditions = []
            if category:
                conditions.append("category = ?")
                params.append(category)
            if is_system is not None:
                conditions.append("is_system = ?")
                params.append(is_system)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY is_system DESC, usage_count DESC, created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'category': row['category'],
                    'description': row['description'],
                    'product_name': row['product_name'],
                    'keywords': json.loads(row['keywords']) if row['keywords'] else [],
                    'style': row['style'],
                    'duration': row['duration'],
                    'platform': row['platform'],
                    'is_system': bool(row['is_system']),
                    'created_by': row['created_by'],
                    'created_at': row['created_at'],
                    'usage_count': row['usage_count']
                })

            return results

    def get_template_detail(self, template_id: int) -> Optional[Dict[str, Any]]:
        """
        获取模板详情

        Args:
            template_id: 模板 ID

        Returns:
            模板详情，如果不存在返回 None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, category, description, product_name, keywords,
                       style, duration, platform, script_data, is_system, created_by,
                       created_at, usage_count
                FROM templates
                WHERE id = ?
            """, (template_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'id': row['id'],
                'name': row['name'],
                'category': row['category'],
                'description': row['description'],
                'product_name': row['product_name'],
                'keywords': json.loads(row['keywords']) if row['keywords'] else [],
                'style': row['style'],
                'duration': row['duration'],
                'platform': row['platform'],
                'script_data': json.loads(row['script_data']),
                'is_system': bool(row['is_system']),
                'created_by': row['created_by'],
                'created_at': row['created_at'],
                'usage_count': row['usage_count']
            }

    def use_template(self, template_id: int) -> bool:
        """
        使用模板（增加使用计数）

        Args:
            template_id: 模板 ID

        Returns:
            是否成功
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE templates SET usage_count = usage_count + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (template_id,))
            conn.commit()
            return cursor.rowcount > 0

    def update_template(
        self,
        template_id: int,
        name: str = None,
        description: str = None,
        script_data: Dict[str, Any] = None
    ) -> bool:
        """
        更新模板

        Args:
            template_id: 模板 ID
            name: 新名称
            description: 新描述
            script_data: 新脚本数据

        Returns:
            是否成功
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if script_data is not None:
                updates.append("script_data = ?")
                params.append(json.dumps(script_data, ensure_ascii=False))

            updates.append("updated_at = CURRENT_TIMESTAMP")

            if not updates:
                return False

            params.append(template_id)

            query = f"UPDATE templates SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_template(self, template_id: int) -> bool:
        """
        删除模板（仅用户模板，系统模板不可删除）

        Args:
            template_id: 模板 ID

        Returns:
            是否成功
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM templates WHERE id = ? AND is_system = 0", (template_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_template_categories(self) -> List[str]:
        """
        获取所有模板分类

        Returns:
            分类列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM templates ORDER BY category")
            return [row['category'] for row in cursor.fetchall()]

    def search_templates(
        self,
        keyword: str,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索模板

        Args:
            keyword: 搜索关键词
            category: 分类筛选
            limit: 返回数量

        Returns:
            模板列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, name, category, description, product_name, keywords,
                       style, duration, platform, is_system, created_by,
                       created_at, usage_count
                FROM templates
                WHERE (name LIKE ? OR description LIKE ? OR product_name LIKE ?)
            """
            params = [f'%{keyword}%', f'%{keyword}%', f'%{keyword}%']

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " ORDER BY is_system DESC, usage_count DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'category': row['category'],
                    'description': row['description'],
                    'product_name': row['product_name'],
                    'keywords': json.loads(row['keywords']) if row['keywords'] else [],
                    'style': row['style'],
                    'duration': row['duration'],
                    'platform': row['platform'],
                    'is_system': bool(row['is_system']),
                    'created_by': row['created_by'],
                    'created_at': row['created_at'],
                    'usage_count': row['usage_count']
                })

            return results

    # ==================== 初始化系统模板 ====================

    def init_system_templates(self):
        """初始化系统预设模板"""
        # 检查是否已有系统模板
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM templates WHERE is_system = 1")
            count = cursor.fetchone()['count']

            if count > 0:
                logger.info("系统模板已存在，跳过初始化")
                return

        # 系统模板列表
        system_templates = [
            {
                'name': '抖音爆款产品展示',
                'category': '产品展示',
                'description': '适用于抖音平台的爆款产品展示视频脚本模板，突出产品特点和卖点',
                'product_info': {
                    'name': '您的产品',
                    'keywords': ['爆款', '产品展示', '抖音'],
                    'style': '活力',
                    'duration': 15,
                    'platform': '抖音'
                },
                'script_data': {
                    'title': '抖音爆款产品展示',
                    'total_duration': 15,
                    'style': '活力',
                    'scenes': [
                        {
                            'scene_no': 1,
                            'duration': 3,
                            'visual': '产品特写镜头，从不同角度展示产品外观',
                            'narration': '看这里！这款产品真的太赞了！',
                            'subtitle': '新品上市'
                        },
                        {
                            'scene_no': 2,
                            'duration': 5,
                            'visual': '产品功能演示，展示核心卖点',
                            'narration': '它有超多功能，满足你的各种需求',
                            'subtitle': '功能强大'
                        },
                        {
                            'scene_no': 3,
                            'duration': 4,
                            'visual': '用户使用场景，产品实际应用效果',
                            'narration': '看看大家都在用它，效果太棒了！',
                            'subtitle': '用户好评'
                        },
                        {
                            'scene_no': 4,
                            'duration': 3,
                            'visual': '产品包装和价格信息，行动号召',
                            'narration': '现在下单还有优惠，赶紧来试试吧！',
                            'subtitle': '限时优惠'
                        }
                    ],
                    'full_prompt': '抖音爆款产品展示视频，活力风格'
                }
            },
            {
                'name': '小红书生活分享',
                'category': '生活分享',
                'description': '适用于小红书平台的生活分享视频脚本模板，温馨治愈的风格',
                'product_info': {
                    'name': '生活用品',
                    'keywords': ['生活分享', '小红书', '治愈'],
                    'style': '温情',
                    'duration': 30,
                    'platform': '小红书'
                },
                'script_data': {
                    'title': '小红书生活分享',
                    'total_duration': 30,
                    'style': '温情',
                    'scenes': [
                        {
                            'scene_no': 1,
                            'duration': 5,
                            'visual': '温馨的家居环境，柔和的光线',
                            'narration': '分享一个让我心动的小发现',
                            'subtitle': '生活小确幸'
                        },
                        {
                            'scene_no': 2,
                            'duration': 8,
                            'visual': '产品细节展示，柔和的色彩搭配',
                            'narration': '每天用它的时刻，都让我觉得生活更美好',
                            'subtitle': '美好时刻'
                        },
                        {
                            'scene_no': 3,
                            'duration': 8,
                            'visual': '日常使用场景，自然的光线',
                            'narration': '它不仅好用，还让我的生活更有仪式感',
                            'subtitle': '仪式感'
                        },
                        {
                            'scene_no': 4,
                            'duration': 5,
                            'visual': '产品与生活场景的和谐画面',
                            'narration': '希望它也能给你带来同样的幸福感',
                            'subtitle': '分享美好'
                        },
                        {
                            'scene_no': 5,
                            'duration': 4,
                            'visual': '温柔的结尾画面,品牌logo',
                            'narration': '评论区告诉我你最喜欢它哪里',
                            'subtitle': '等你分享'
                        }
                    ],
                    'full_prompt': '小红书生活分享视频，温情治愈风格'
                }
            },
            {
                'name': '企业品牌宣传',
                'category': '品牌宣传',
                'description': '适用于企业品牌宣传的专业视频脚本模板，展现品牌实力',
                'product_info': {
                    'name': '企业品牌',
                    'keywords': ['品牌', '宣传', '专业'],
                    'style': '专业',
                    'duration': 60,
                    'platform': '企业官网'
                },
                'script_data': {
                    'title': '企业品牌宣传',
                    'total_duration': 60,
                    'style': '专业',
                    'scenes': [
                        {
                            'scene_no': 1,
                            'duration': 10,
                            'visual': '品牌标志性建筑或总部大楼，稳重大气',
                            'narration': '自创立以来，我们始终坚持品质第一',
                            'subtitle': '匠心传承'
                        },
                        {
                            'scene_no': 2,
                            'duration': 15,
                            'visual': '生产车间或办公环境，展现专业实力',
                            'narration': '每一道工序都经过严格把控，确保产品品质',
                            'subtitle': '专业制造'
                        },
                        {
                            'scene_no': 3,
                            'duration': 15,
                            'visual': '研发团队工作场景，展现创新能力',
                            'narration': '持续创新，是我们不断进步的动力',
                            'subtitle': '创新驱动'
                        },
                        {
                            'scene_no': 4,
                            'duration': 10,
                            'visual': '客户服务场景，展现服务理念',
                            'narration': '以客户为中心，提供贴心服务',
                            'subtitle': '客户至上'
                        },
                        {
                            'scene_no': 5,
                            'duration': 10,
                            'visual': '品牌Logo和企业愿景，大气结尾',
                            'narration': '选择我们，选择品质与信任',
                            'subtitle': '品牌承诺'
                        }
                    ],
                    'full_prompt': '企业品牌宣传视频，专业稳重的风格'
                }
            },
            {
                'name': '电商促销活动',
                'category': '电商营销',
                'description': '适用于电商促销活动的搞笑视频脚本模板，吸引眼球',
                'product_info': {
                    'name': '促销商品',
                    'keywords': ['促销', '电商', '搞笑'],
                    'style': '搞笑',
                    'duration': 30,
                    'platform': '淘宝'
                },
                'script_data': {
                    'title': '电商促销活动',
                    'total_duration': 30,
                    'style': '搞笑',
                    'scenes': [
                        {
                            'scene_no': 1,
                            'duration': 5,
                            'visual': '夸张的开场，主角用夸张的表情展示产品',
                            'narration': '天呐！这个价格我都不敢相信！',
                            'subtitle': '震惊表情'
                        },
                        {
                            'scene_no': 2,
                            'duration': 8,
                            'visual': '幽默的对比场景，展示产品性价比',
                            'narration': '平时卖这个价格，今天只要三分之一！',
                            'subtitle': '超值对比'
                        },
                        {
                            'scene_no': 3,
                            'duration': 8,
                            'visual': '搞笑的使用场景，突出产品效果',
                            'narration': '我用了之后，朋友们都问我链接在哪买！',
                            'subtitle': '真实效果'
                        },
                        {
                            'scene_no': 4,
                            'duration': 5,
                            'visual': '倒计时动画，紧迫感',
                            'narration': '只有今天，错过再等一年！',
                            'subtitle': '限时特惠'
                        },
                        {
                            'scene_no': 5,
                            'duration': 4,
                            'visual': '产品特写和购买按钮指引',
                            'narration': '赶紧点击下方链接，手慢无！',
                            'subtitle': '立即抢购'
                        }
                    ],
                    'full_prompt': '电商促销活动视频，搞笑吸引眼球'
                }
            },
    {
        'name': '美妆产品展示',
        'category': '美妆时尚',
        'description': '适用于美妆产品的专业展示视频脚本模板，突出产品效果',
        'product_info': {
            'name': '美妆产品',
            'keywords': ['美妆', '化妆品', '展示'],
            'style': '活力',
            'duration': 30,
            'platform': '抖音'
        },
        'script_data': {
            'title': '美妆产品展示',
            'total_duration': 30,
            'style': '活力',
            'scenes': [
                {
                    'scene_no': 1,
                    'duration': 5,
                    'visual': '产品包装特写，精致的质感',
                    'narration': '姐妹们，发现了一个宝藏产品！',
                    'subtitle': '宝藏发现'
                },
                {
                    'scene_no': 2,
                    'duration': 8,
                    'visual': '产品质地展示，细腻的质感',
                    'narration': '看这个质地，超级细腻，上脸绝了！',
                    'subtitle': '质感出众'
                },
                {
                    'scene_no': 3,
                    'duration': 10,
                    'visual': '使用前后的对比效果',
                    'narration': '看看这个效果，真的让人惊艳！',
                    'subtitle': '惊艳效果'
                },
                {
                    'scene_no': 4,
                    'duration': 4,
                    'visual': '产品整体展示，品牌logo',
                    'narration': '赶紧试试，绝对不会后悔！',
                    'subtitle': '值得拥有'
                },
                {
                    'scene_no': 5,
                    'duration': 3,
                    'visual': '购买链接和限时优惠',
                    'narration': '现在下单还有赠品哦！',
                    'subtitle': '限时赠送'
                }
            ],
            'full_prompt': '美妆产品展示视频，活力时尚风格'
        }
    }
        ]

        # 插入系统模板
        for template in system_templates:
            try:
                self.save_template(
                    name=template['name'],
                    category=template['category'],
                    description=template['description'],
                    product_info=template['product_info'],
                    script_data=template['script_data'],
                    is_system=True,
                    created_by='system'
                )
            except sqlite3.IntegrityError:
                # 模板已存在，跳过
                pass

        logger.info(f"系统模板初始化完成，共 {len(system_templates)} 个模板")


# 全局数据库实例
db = Database()
db.init_system_templates()