from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional

from config import DATABASE_PATH, ensure_directories


class ShopDatabase:
    """商品资产、分镜和生成任务的 SQLite 持久化。"""

    def __init__(self) -> None:
        ensure_directories()
        self._init_tables()

    def _connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_tables(self) -> None:
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    brand TEXT,
                    price TEXT,
                    specs_json TEXT NOT NULL DEFAULT '{}',
                    selling_points_json TEXT NOT NULL DEFAULT '[]',
                    prohibited_terms_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS product_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    asset_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    is_primary INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS storyboards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    final_video_url TEXT,
                    final_composition_status TEXT NOT NULL DEFAULT 'not_started',
                    final_composition_error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS storyboard_scenes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    storyboard_id INTEGER NOT NULL REFERENCES storyboards(id) ON DELETE CASCADE,
                    scene_no INTEGER NOT NULL,
                    scene_type TEXT NOT NULL,
                    target_duration REAL NOT NULL,
                    asset_id INTEGER REFERENCES product_assets(id),
                    generation_strategy TEXT NOT NULL,
                    motion_prompt TEXT NOT NULL DEFAULT '',
                    identity_constraints_json TEXT NOT NULL DEFAULT '[]',
                    postprocess_layers_json TEXT NOT NULL DEFAULT '[]',
                    postprocess_config_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(storyboard_id, scene_no)
                );

                CREATE TABLE IF NOT EXISTS generation_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    storyboard_id INTEGER NOT NULL REFERENCES storyboards(id) ON DELETE CASCADE,
                    scene_id INTEGER NOT NULL REFERENCES storyboard_scenes(id) ON DELETE CASCADE,
                    provider_task_id TEXT,
                    model TEXT,
                    image_url TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    status TEXT NOT NULL,
                    video_url TEXT,
                    cover_url TEXT,
                    composed_video_url TEXT,
                    composition_status TEXT NOT NULL DEFAULT 'not_started',
                    composition_error TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_assets_product ON product_assets(product_id);
                CREATE INDEX IF NOT EXISTS idx_scenes_storyboard ON storyboard_scenes(storyboard_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_storyboard ON generation_tasks(storyboard_id, status);
                """
            )
            # 兼容 P0 已创建的 SQLite 文件；新安装时上面的 CREATE TABLE 已包含这些字段。
            self._ensure_column(conn, "storyboards", "final_video_url", "TEXT")
            self._ensure_column(conn, "storyboards", "final_composition_status", "TEXT NOT NULL DEFAULT 'not_started'")
            self._ensure_column(conn, "storyboards", "final_composition_error", "TEXT")
            self._ensure_column(conn, "storyboard_scenes", "postprocess_config_json", "TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "generation_tasks", "composed_video_url", "TEXT")
            self._ensure_column(conn, "generation_tasks", "composition_status", "TEXT NOT NULL DEFAULT 'not_started'")
            self._ensure_column(conn, "generation_tasks", "composition_error", "TEXT")

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _decode(row: dict[str, Any], *fields: str) -> dict[str, Any]:
        result = dict(row)
        for field in fields:
            key = f"{field}_json"
            result[field] = json.loads(result.pop(key))
        return result

    def create_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._connection() as conn:
            cursor = conn.execute(
                """INSERT INTO products
                (name, brand, price, specs_json, selling_points_json, prohibited_terms_json)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    payload["name"], payload.get("brand"), payload.get("price"),
                    self._json(payload.get("specs", {})),
                    self._json(payload.get("selling_points", [])),
                    self._json(payload.get("prohibited_terms", [])),
                ),
            )
            return self.get_product(cursor.lastrowid, conn)

    def get_product(self, product_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[dict[str, Any]]:
        owns_connection = conn is None
        conn = conn or self._connection()
        try:
            row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            return self._decode(row, "specs", "selling_points", "prohibited_terms") if row else None
        finally:
            if owns_connection:
                conn.close()

    def list_assets(self, product_id: int) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM product_assets WHERE product_id = ? ORDER BY is_primary DESC, id ASC",
                (product_id,),
            ).fetchall()
            return [self._decode(row, "metadata") for row in rows]

    def get_asset(self, asset_id: int) -> Optional[dict[str, Any]]:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM product_assets WHERE id = ?", (asset_id,)).fetchone()
            return self._decode(row, "metadata") if row else None

    def create_asset(self, product_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        with self._connection() as conn:
            if payload.get("is_primary"):
                conn.execute("UPDATE product_assets SET is_primary = 0 WHERE product_id = ?", (product_id,))
            cursor = conn.execute(
                """INSERT INTO product_assets (product_id, asset_type, url, is_primary, metadata_json)
                VALUES (?, ?, ?, ?, ?)""",
                (product_id, payload["asset_type"], str(payload["url"]), int(payload.get("is_primary", False)), self._json(payload.get("metadata", {}))),
            )
            row = conn.execute("SELECT * FROM product_assets WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return self._decode(row, "metadata")

    def create_storyboard(self, product_id: int, title: str, scenes: list[dict[str, Any]]) -> dict[str, Any]:
        with self._connection() as conn:
            cursor = conn.execute(
                "INSERT INTO storyboards (product_id, title) VALUES (?, ?)", (product_id, title)
            )
            storyboard_id = cursor.lastrowid
            for scene in scenes:
                conn.execute(
                    """INSERT INTO storyboard_scenes
                    (storyboard_id, scene_no, scene_type, target_duration, asset_id,
                     generation_strategy, motion_prompt, identity_constraints_json, postprocess_layers_json,
                     postprocess_config_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        storyboard_id, scene["scene_no"], scene["scene_type"], scene["target_duration"],
                        scene.get("asset_id"), scene["generation_strategy"], scene.get("motion_prompt", ""),
                        self._json(scene.get("identity_constraints", [])), self._json(scene.get("postprocess_layers", [])),
                        self._json(scene.get("postprocess_config", {})),
                    ),
                )
            return self.get_storyboard(storyboard_id, conn)

    def get_storyboard(self, storyboard_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[dict[str, Any]]:
        owns_connection = conn is None
        conn = conn or self._connection()
        try:
            storyboard = conn.execute("SELECT * FROM storyboards WHERE id = ?", (storyboard_id,)).fetchone()
            if not storyboard:
                return None
            result = dict(storyboard)
            rows = conn.execute(
                """SELECT s.*, a.url AS asset_url, a.asset_type AS asset_type
                FROM storyboard_scenes s
                LEFT JOIN product_assets a ON a.id = s.asset_id
                WHERE s.storyboard_id = ? ORDER BY s.scene_no""",
                (storyboard_id,),
            ).fetchall()
            result["scenes"] = [
                self._decode(row, "identity_constraints", "postprocess_layers", "postprocess_config") for row in rows
            ]
            return result
        finally:
            if owns_connection:
                conn.close()

    def get_scene(self, scene_id: int) -> Optional[dict[str, Any]]:
        with self._connection() as conn:
            row = conn.execute(
                """SELECT s.*, b.product_id, a.url AS asset_url, a.asset_type AS asset_type
                FROM storyboard_scenes s
                JOIN storyboards b ON b.id = s.storyboard_id
                LEFT JOIN product_assets a ON a.id = s.asset_id
                WHERE s.id = ?""",
                (scene_id,),
            ).fetchone()
            return self._decode(row, "identity_constraints", "postprocess_layers", "postprocess_config") if row else None

    def update_scene(self, scene_id: int, values: dict[str, Any]) -> Optional[dict[str, Any]]:
        allowed = {
            "asset_id", "scene_type", "target_duration", "generation_strategy", "motion_prompt",
            "identity_constraints", "postprocess_layers", "postprocess_config",
        }
        update_values = {key: value for key, value in values.items() if key in allowed and value is not None}
        if not update_values:
            return self.get_scene(scene_id)
        assignments, params = [], []
        for key, value in update_values.items():
            column = f"{key}_json" if key in {"identity_constraints", "postprocess_layers", "postprocess_config"} else key
            assignments.append(f"{column} = ?")
            params.append(self._json(value) if column.endswith("_json") else value)
        params.append(scene_id)
        with self._connection() as conn:
            conn.execute(f"UPDATE storyboard_scenes SET {', '.join(assignments)} WHERE id = ?", params)
        return self.get_scene(scene_id)

    def queue_storyboard_tasks(self, storyboard_id: int, model: str) -> list[dict[str, Any]]:
        with self._connection() as conn:
            scenes = conn.execute(
                """SELECT s.*, a.url AS asset_url
                FROM storyboard_scenes s LEFT JOIN product_assets a ON a.id = s.asset_id
                WHERE s.storyboard_id = ? AND s.generation_strategy = 'image_to_video'
                ORDER BY s.scene_no""",
                (storyboard_id,),
            ).fetchall()
            queued = []
            for scene in scenes:
                existing = conn.execute(
                    "SELECT id FROM generation_tasks WHERE scene_id = ? AND status IN ('queued', 'submitted', 'processing')",
                    (scene["id"],),
                ).fetchone()
                if existing:
                    continue
                prompt = self._build_motion_prompt(scene)
                cursor = conn.execute(
                    """INSERT INTO generation_tasks
                    (storyboard_id, scene_id, model, image_url, prompt, status)
                    VALUES (?, ?, ?, ?, ?, 'queued')""",
                    (storyboard_id, scene["id"], model, scene["asset_url"] or "", prompt),
                )
                queued.append(self.get_generation_task(cursor.lastrowid, conn))
            return queued

    @staticmethod
    def _build_motion_prompt(scene: sqlite3.Row) -> str:
        constraints = json.loads(scene["identity_constraints_json"])
        constraint_text = "；".join(constraints)
        return f"{scene['motion_prompt']}。商品一致性要求：{constraint_text}".strip("。")

    def active_provider_task_count(self) -> int:
        """按 API Key 全局统计活跃任务，不能只限制单个分镜批次。"""
        with self._connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM generation_tasks WHERE status IN ('submitted', 'processing')"
            ).fetchone()[0]

    def get_next_queued_task(self, storyboard_id: int) -> Optional[dict[str, Any]]:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM generation_tasks WHERE storyboard_id = ? AND status = 'queued' ORDER BY id LIMIT 1",
                (storyboard_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_generation_tasks(self, storyboard_id: int) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT t.*, s.scene_no
                   FROM generation_tasks t
                   JOIN storyboard_scenes s ON s.id = t.scene_id
                   WHERE t.storyboard_id = ?
                   ORDER BY s.scene_no, t.id""",
                (storyboard_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def update_generation_task(self, task_id: int, **values: Any) -> Optional[dict[str, Any]]:
        if not values:
            return self.get_generation_task(task_id)
        assignments = [f"{key} = ?" for key in values]
        params = list(values.values()) + [task_id]
        with self._connection() as conn:
            conn.execute(
                f"UPDATE generation_tasks SET {', '.join(assignments)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                params,
            )
        return self.get_generation_task(task_id)

    def get_generation_task(self, task_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[dict[str, Any]]:
        owns_connection = conn is None
        conn = conn or self._connection()
        try:
            row = conn.execute("SELECT * FROM generation_tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(row) if row else None
        finally:
            if owns_connection:
                conn.close()

    def get_composition_context(self, task_id: int) -> Optional[dict[str, Any]]:
        """读取确定性合成所需的任务、分镜、商品事实和全部商品资产。"""
        with self._connection() as conn:
            row = conn.execute(
                """SELECT t.*, s.scene_no, s.target_duration, s.postprocess_layers_json,
                          s.postprocess_config_json, b.product_id, p.name AS product_name,
                          p.brand AS product_brand, p.price AS product_price,
                          p.selling_points_json
                   FROM generation_tasks t
                   JOIN storyboard_scenes s ON s.id = t.scene_id
                   JOIN storyboards b ON b.id = t.storyboard_id
                   JOIN products p ON p.id = b.product_id
                   WHERE t.id = ?""",
                (task_id,),
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            result["postprocess_layers"] = json.loads(result.pop("postprocess_layers_json"))
            result["postprocess_config"] = json.loads(result.pop("postprocess_config_json"))
            result["selling_points"] = json.loads(result.pop("selling_points_json"))
            assets = conn.execute(
                "SELECT * FROM product_assets WHERE product_id = ? ORDER BY is_primary DESC, id ASC",
                (result["product_id"],),
            ).fetchall()
            result["assets"] = [self._decode(asset, "metadata") for asset in assets]
            return result

    def list_storyboard_composed_tasks(self, storyboard_id: int) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT s.scene_no, s.id AS scene_id, t.id, t.composed_video_url,
                          t.composition_status, t.composition_error
                   FROM storyboard_scenes s
                   LEFT JOIN generation_tasks t ON t.id = (
                       SELECT latest.id FROM generation_tasks latest
                       WHERE latest.scene_id = s.id AND latest.composed_video_url IS NOT NULL
                       ORDER BY latest.id DESC LIMIT 1
                   )
                   WHERE s.storyboard_id = ? AND s.generation_strategy = 'image_to_video'
                   ORDER BY s.scene_no""",
                (storyboard_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def update_storyboard_final(self, storyboard_id: int, **values: Any) -> Optional[dict[str, Any]]:
        if not values:
            return self.get_storyboard(storyboard_id)
        assignments = [f"{key} = ?" for key in values]
        params = list(values.values()) + [storyboard_id]
        with self._connection() as conn:
            conn.execute(f"UPDATE storyboards SET {', '.join(assignments)} WHERE id = ?", params)
        return self.get_storyboard(storyboard_id)


db = ShopDatabase()
