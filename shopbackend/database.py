from __future__ import annotations

import json
import sqlite3
import uuid
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

                CREATE TABLE IF NOT EXISTS scene_references (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_id INTEGER NOT NULL REFERENCES storyboard_scenes(id) ON DELETE CASCADE,
                    asset_id INTEGER NOT NULL REFERENCES product_assets(id) ON DELETE RESTRICT,
                    role TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(scene_id, asset_id, role)
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
                    candidate_group_id TEXT,
                    candidate_index INTEGER NOT NULL DEFAULT 1,
                    selected INTEGER NOT NULL DEFAULT 0,
                    selected_at TEXT,
                    selection_reviewer TEXT,
                    selection_note TEXT,
                    reference_manifest_json TEXT NOT NULL DEFAULT '[]',
                    quality_status TEXT NOT NULL DEFAULT 'not_checked',
                    quality_decision TEXT,
                    source_type TEXT NOT NULL DEFAULT 'generated',
                    source_task_type TEXT,
                    source_provider_task_id TEXT,
                    submission_key TEXT,
                    dispatch_claimed_at TEXT,
                    dispatch_attempts INTEGER NOT NULL DEFAULT 0,
                    next_dispatch_at TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_assets_product ON product_assets(product_id);
                CREATE INDEX IF NOT EXISTS idx_scenes_storyboard ON storyboard_scenes(storyboard_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_storyboard ON generation_tasks(storyboard_id, status);
                CREATE INDEX IF NOT EXISTS idx_references_scene ON scene_references(scene_id, sort_order);

                CREATE TABLE IF NOT EXISTS quality_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL REFERENCES generation_tasks(id) ON DELETE CASCADE,
                    engine TEXT NOT NULL,
                    status TEXT NOT NULL,
                    product_similarity_score REAL,
                    logo_status TEXT NOT NULL DEFAULT 'not_applicable',
                    ocr_status TEXT NOT NULL DEFAULT 'not_applicable',
                    decision TEXT NOT NULL DEFAULT 'review',
                    summary TEXT,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    reviewer TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS trace_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
                    storyboard_id INTEGER REFERENCES storyboards(id) ON DELETE SET NULL,
                    scene_id INTEGER REFERENCES storyboard_scenes(id) ON DELETE SET NULL,
                    task_id INTEGER REFERENCES generation_tasks(id) ON DELETE SET NULL,
                    asset_id INTEGER REFERENCES product_assets(id) ON DELETE SET NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_trace_storyboard ON trace_events(storyboard_id, id DESC);
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
            self._ensure_column(conn, "generation_tasks", "candidate_group_id", "TEXT")
            self._ensure_column(conn, "generation_tasks", "candidate_index", "INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(conn, "generation_tasks", "selected", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "generation_tasks", "selected_at", "TEXT")
            self._ensure_column(conn, "generation_tasks", "selection_reviewer", "TEXT")
            self._ensure_column(conn, "generation_tasks", "selection_note", "TEXT")
            self._ensure_column(conn, "generation_tasks", "reference_manifest_json", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "generation_tasks", "quality_status", "TEXT NOT NULL DEFAULT 'not_checked'")
            self._ensure_column(conn, "generation_tasks", "quality_decision", "TEXT")
            self._ensure_column(conn, "generation_tasks", "source_type", "TEXT NOT NULL DEFAULT 'generated'")
            self._ensure_column(conn, "generation_tasks", "source_task_type", "TEXT")
            self._ensure_column(conn, "generation_tasks", "source_provider_task_id", "TEXT")
            self._ensure_column(conn, "generation_tasks", "submission_key", "TEXT")
            self._ensure_column(conn, "generation_tasks", "dispatch_claimed_at", "TEXT")
            self._ensure_column(conn, "generation_tasks", "dispatch_attempts", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "generation_tasks", "next_dispatch_at", "TEXT")
            # 索引在迁移字段补齐后创建，确保旧版数据库升级不会因缺列失败。
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_candidates ON generation_tasks(scene_id, candidate_group_id, selected)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_dispatch ON generation_tasks(status, next_dispatch_at, storyboard_id)"
            )

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

    def _add_trace_event(self, conn: sqlite3.Connection, event_type: str, payload: dict[str, Any], **scope: Any) -> None:
        conn.execute(
            """INSERT INTO trace_events
            (product_id, storyboard_id, scene_id, task_id, asset_id, event_type, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                scope.get("product_id"), scope.get("storyboard_id"), scope.get("scene_id"),
                scope.get("task_id"), scope.get("asset_id"), event_type, self._json(payload),
            ),
        )

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
            self._add_trace_event(conn, "product.created", {"name": payload["name"]}, product_id=cursor.lastrowid)
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
            self._add_trace_event(
                conn, "asset.created", {"asset_type": payload["asset_type"], "url": str(payload["url"])},
                product_id=product_id, asset_id=cursor.lastrowid,
            )
            return self._decode(row, "metadata")

    def save_asset_preflight(self, asset_id: int, result: dict[str, Any] | None, error: str | None = None) -> Optional[dict[str, Any]]:
        """将最新素材预检快照写回 metadata，并留下可追溯事件。"""
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM product_assets WHERE id = ?", (asset_id,)).fetchone()
            if not row:
                return None
            asset = self._decode(row, "metadata")
            metadata = asset["metadata"]
            metadata["preflight"] = {
                "status": "passed" if result else "failed",
                "result": result,
                "error": error,
            }
            conn.execute(
                "UPDATE product_assets SET metadata_json = ? WHERE id = ?", (self._json(metadata), asset_id)
            )
            self._add_trace_event(
                conn, "asset.preflight_passed" if result else "asset.preflight_failed",
                {"error": error, "result": result}, product_id=asset["product_id"], asset_id=asset_id,
            )
        return self.get_asset(asset_id)

    def create_storyboard(self, product_id: int, title: str, scenes: list[dict[str, Any]]) -> dict[str, Any]:
        with self._connection() as conn:
            cursor = conn.execute(
                "INSERT INTO storyboards (product_id, title) VALUES (?, ?)", (product_id, title)
            )
            storyboard_id = cursor.lastrowid
            self._add_trace_event(conn, "storyboard.created", {"title": title}, product_id=product_id, storyboard_id=storyboard_id)
            for scene in scenes:
                scene_cursor = conn.execute(
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
                scene_id = scene_cursor.lastrowid
                references = scene.get("reference_assets") or ([{"asset_id": scene.get("asset_id"), "role": "identity", "sort_order": 0}] if scene.get("asset_id") else [])
                for reference in references:
                    if reference.get("asset_id") is None:
                        continue
                    conn.execute(
                        """INSERT OR IGNORE INTO scene_references (scene_id, asset_id, role, sort_order)
                        VALUES (?, ?, ?, ?)""",
                        (scene_id, reference["asset_id"], reference.get("role", "identity"), reference.get("sort_order", 0)),
                    )
                self._add_trace_event(
                    conn, "scene.created", {"scene_no": scene["scene_no"], "reference_count": len(references)},
                    product_id=product_id, storyboard_id=storyboard_id, scene_id=scene_id,
                )
            return self.get_storyboard(storyboard_id, conn)

    def _list_scene_references(self, conn: sqlite3.Connection, scene_id: int) -> list[dict[str, Any]]:
        rows = conn.execute(
            """SELECT r.id, r.asset_id, r.role, r.sort_order, a.asset_type, a.url
               FROM scene_references r JOIN product_assets a ON a.id = r.asset_id
               WHERE r.scene_id = ? ORDER BY r.sort_order, r.id""",
            (scene_id,),
        ).fetchall()
        return [dict(row) for row in rows]

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
            result["scenes"] = []
            for row in rows:
                scene = self._decode(row, "identity_constraints", "postprocess_layers", "postprocess_config")
                scene["reference_assets"] = self._list_scene_references(conn, scene["id"])
                result["scenes"].append(scene)
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
            if not row:
                return None
            scene = self._decode(row, "identity_constraints", "postprocess_layers", "postprocess_config")
            scene["reference_assets"] = self._list_scene_references(conn, scene_id)
            return scene

    def update_scene(self, scene_id: int, values: dict[str, Any]) -> Optional[dict[str, Any]]:
        allowed = {
            "asset_id", "scene_type", "target_duration", "generation_strategy", "motion_prompt",
            "identity_constraints", "reference_assets", "postprocess_layers", "postprocess_config",
        }
        update_values = {key: value for key, value in values.items() if key in allowed and value is not None}
        if not update_values:
            return self.get_scene(scene_id)
        reference_assets = update_values.pop("reference_assets", None)
        assignments, params = [], []
        for key, value in update_values.items():
            column = f"{key}_json" if key in {"identity_constraints", "postprocess_layers", "postprocess_config"} else key
            assignments.append(f"{column} = ?")
            params.append(self._json(value) if column.endswith("_json") else value)
        params.append(scene_id)
        with self._connection() as conn:
            if assignments:
                conn.execute(f"UPDATE storyboard_scenes SET {', '.join(assignments)} WHERE id = ?", params)
            if reference_assets is not None:
                conn.execute("DELETE FROM scene_references WHERE scene_id = ?", (scene_id,))
                for reference in reference_assets:
                    conn.execute(
                        """INSERT INTO scene_references (scene_id, asset_id, role, sort_order)
                        VALUES (?, ?, ?, ?)""",
                        (scene_id, reference["asset_id"], reference.get("role", "identity"), reference.get("sort_order", 0)),
                    )
        return self.get_scene(scene_id)

    def queue_storyboard_tasks(
        self, storyboard_id: int, model: str, candidate_count: int = 1, force_new: bool = False,
    ) -> list[dict[str, Any]]:
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
                active_task = conn.execute(
                    "SELECT id FROM generation_tasks WHERE scene_id = ? AND status IN ('queued', 'submitting', 'submitted', 'processing')",
                    (scene["id"],),
                ).fetchone()
                existing_task = conn.execute(
                    "SELECT id FROM generation_tasks WHERE scene_id = ? LIMIT 1", (scene["id"],)
                ).fetchone()
                # 默认 P0 行为是不重复建单；P2 显式候选生成或 force_new 才创建新候选组。
                if active_task or (candidate_count == 1 and existing_task and not force_new):
                    continue
                references = self._list_scene_references(conn, scene["id"])
                if not references and scene["asset_url"]:
                    references = [{"asset_id": scene["asset_id"], "role": "identity", "sort_order": 0, "url": scene["asset_url"]}]
                prompt = self._build_motion_prompt(scene, references)
                candidate_group_id = uuid.uuid4().hex
                for candidate_index in range(1, candidate_count + 1):
                    cursor = conn.execute(
                        """INSERT INTO generation_tasks
                        (storyboard_id, scene_id, model, image_url, prompt, status, candidate_group_id,
                         candidate_index, reference_manifest_json)
                        VALUES (?, ?, ?, ?, ?, 'queued', ?, ?, ?)""",
                        (
                            storyboard_id, scene["id"], model, scene["asset_url"] or "", prompt,
                            candidate_group_id, candidate_index, self._json(references),
                        ),
                    )
                    self._add_trace_event(
                        conn, "generation.candidate_queued",
                        {"candidate_group_id": candidate_group_id, "candidate_index": candidate_index, "reference_count": len(references)},
                        storyboard_id=storyboard_id, scene_id=scene["id"], task_id=cursor.lastrowid,
                    )
                    queued.append(self.get_generation_task(cursor.lastrowid, conn))
            return queued

    def import_kling_library_video(self, scene_id: int, library_item: dict[str, Any]) -> Optional[dict[str, Any]]:
        """将当前可灵账号的已完成历史视频登记为本分镜候选，不复制或信任前端传入 URL。"""
        with self._connection() as conn:
            scene = conn.execute(
                """SELECT s.*, b.product_id FROM storyboard_scenes s
                   JOIN storyboards b ON b.id = s.storyboard_id WHERE s.id = ?""", (scene_id,)
            ).fetchone()
            if not scene:
                return None
            existing = conn.execute(
                """SELECT id FROM generation_tasks
                   WHERE scene_id = ? AND source_type = 'kling_library'
                     AND source_provider_task_id = ? AND source_task_type = ?""",
                (scene_id, library_item["task_id"], library_item["task_type"]),
            ).fetchone()
            if existing:
                return self.get_generation_task(existing["id"], conn)
            main_asset = conn.execute("SELECT url FROM product_assets WHERE id = ?", (scene["asset_id"],)).fetchone()
            references = self._list_scene_references(conn, scene_id)
            next_index = conn.execute(
                "SELECT COALESCE(MAX(candidate_index), 0) + 1 FROM generation_tasks WHERE scene_id = ?", (scene_id,)
            ).fetchone()[0]
            cursor = conn.execute(
                """INSERT INTO generation_tasks
                (storyboard_id, scene_id, provider_task_id, model, image_url, prompt, status, video_url, cover_url,
                 candidate_group_id, candidate_index, reference_manifest_json, source_type, source_task_type, source_provider_task_id)
                VALUES (?, ?, ?, 'kling-library', ?, ?, ?, ?, ?, ?, ?, ?, 'kling_library', ?, ?)""",
                (
                    scene["storyboard_id"], scene_id, library_item["task_id"], main_asset["url"] if main_asset else "",
                    "从可灵视频库导入的候选片段", library_item["status"], library_item["video_url"], library_item.get("cover_url"),
                    f"library-{library_item['task_id']}", next_index, self._json(references),
                    library_item["task_type"], library_item["task_id"],
                ),
            )
            self._add_trace_event(
                conn, "kling_library.imported",
                {"source_task_id": library_item["task_id"], "source_task_type": library_item["task_type"], "video_url": library_item["video_url"]},
                product_id=scene["product_id"], storyboard_id=scene["storyboard_id"], scene_id=scene_id, task_id=cursor.lastrowid,
            )
            return self.get_generation_task(cursor.lastrowid, conn)

    @staticmethod
    def _build_motion_prompt(scene: sqlite3.Row, references: list[dict[str, Any]]) -> str:
        constraints = json.loads(scene["identity_constraints_json"])
        constraint_text = "；".join(constraints)
        reference_text = "；".join(f"{item.get('role', 'identity')}参考图" for item in references)
        return f"{scene['motion_prompt']}。商品一致性要求：{constraint_text}。参考资产：{reference_text}".strip("。")

    def active_provider_task_count(self) -> int:
        """按 API Key 全局统计活跃任务，不能只限制单个分镜批次。"""
        with self._connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM generation_tasks WHERE status IN ('submitting', 'submitted', 'processing')"
            ).fetchone()[0]

    def recover_stale_submission_claims(self, lease_seconds: int) -> int:
        """回收进程崩溃遗留的提交租约；保留 submission_key 以保证重试仍然幂等。"""
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT id, storyboard_id, scene_id FROM generation_tasks
                   WHERE status = 'submitting'
                     AND dispatch_claimed_at <= datetime('now', ?)""",
                (f"-{lease_seconds} seconds",),
            ).fetchall()
            if not rows:
                return 0
            conn.execute(
                """UPDATE generation_tasks
                   SET status = 'queued', dispatch_claimed_at = NULL,
                       next_dispatch_at = CURRENT_TIMESTAMP,
                       error = '提交租约超时，已由 Worker 回收', updated_at = CURRENT_TIMESTAMP
                   WHERE status = 'submitting' AND dispatch_claimed_at <= datetime('now', ?)""",
                (f"-{lease_seconds} seconds",),
            )
            for row in rows:
                self._add_trace_event(
                    conn, "generation.dispatch_recovered", {"lease_seconds": lease_seconds},
                    storyboard_id=row["storyboard_id"], scene_id=row["scene_id"], task_id=row["id"],
                )
            return len(rows)

    def claim_next_queued_task(
        self, max_provider_parallel: int, storyboard_id: int | None = None,
    ) -> Optional[dict[str, Any]]:
        """在一个 SQLite 写事务内检查并发配额并将一条 queued 任务原子改为 submitting。"""
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            active_count = conn.execute(
                "SELECT COUNT(*) FROM generation_tasks WHERE status IN ('submitting', 'submitted', 'processing')"
            ).fetchone()[0]
            if active_count >= max_provider_parallel:
                return None
            scope_sql, params = "", []
            if storyboard_id is not None:
                scope_sql, params = " AND storyboard_id = ?", [storyboard_id]
            row = conn.execute(
                """SELECT * FROM generation_tasks
                   WHERE status = 'queued' AND (next_dispatch_at IS NULL OR next_dispatch_at <= CURRENT_TIMESTAMP)"""
                + scope_sql + " ORDER BY storyboard_id, scene_id, candidate_group_id, candidate_index, id LIMIT 1",
                params,
            ).fetchone()
            if not row:
                return None
            submission_key = row["submission_key"] or uuid.uuid4().hex
            updated = conn.execute(
                """UPDATE generation_tasks
                   SET status = 'submitting', submission_key = ?, dispatch_claimed_at = CURRENT_TIMESTAMP,
                       dispatch_attempts = dispatch_attempts + 1, next_dispatch_at = NULL,
                       error = NULL, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ? AND status = 'queued'""",
                (submission_key, row["id"]),
            )
            if updated.rowcount != 1:
                return None
            task = conn.execute("SELECT * FROM generation_tasks WHERE id = ?", (row["id"],)).fetchone()
            self._add_trace_event(
                conn, "generation.dispatch_claimed",
                {"attempt": task["dispatch_attempts"]},
                storyboard_id=task["storyboard_id"], scene_id=task["scene_id"], task_id=task["id"],
            )
            return self._task_result(task)

    def complete_submission_claim(self, task_id: int, submission_key: str, result: dict[str, Any]) -> Optional[dict[str, Any]]:
        """只有仍持有同一租约的 Worker 才能写入供应商任务号。"""
        with self._connection() as conn:
            task = conn.execute("SELECT storyboard_id, scene_id FROM generation_tasks WHERE id = ?", (task_id,)).fetchone()
            updated = conn.execute(
                """UPDATE generation_tasks
                   SET provider_task_id = ?, status = ?, dispatch_claimed_at = NULL, error = NULL,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ? AND status = 'submitting' AND submission_key = ?""",
                (result["provider_task_id"], result["status"], task_id, submission_key),
            )
            if updated.rowcount != 1:
                return None
            if task:
                self._add_trace_event(
                    conn, "generation.submitted", {"provider_task_id": result["provider_task_id"]},
                    storyboard_id=task["storyboard_id"], scene_id=task["scene_id"], task_id=task_id,
                )
        return self.get_generation_task(task_id)

    def release_submission_claim(self, task_id: int, submission_key: str, error: str) -> Optional[dict[str, Any]]:
        """失败后按有限退避回队；submission_key 不变，下一次请求仍使用同一个幂等键。"""
        with self._connection() as conn:
            task = conn.execute(
                "SELECT storyboard_id, scene_id, dispatch_attempts FROM generation_tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if not task:
                return None
            delay_seconds = min(300, 2 ** min(task["dispatch_attempts"], 8))
            updated = conn.execute(
                """UPDATE generation_tasks
                   SET status = 'queued', dispatch_claimed_at = NULL,
                       next_dispatch_at = datetime('now', ?), error = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ? AND status = 'submitting' AND submission_key = ?""",
                (f"+{delay_seconds} seconds", error[:2000], task_id, submission_key),
            )
            if updated.rowcount != 1:
                return None
            self._add_trace_event(
                conn, "generation.dispatch_retry_scheduled", {"delay_seconds": delay_seconds, "error": error[:500]},
                storyboard_id=task["storyboard_id"], scene_id=task["scene_id"], task_id=task_id,
            )
        return self.get_generation_task(task_id)

    def list_tasks_to_refresh(self) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT * FROM generation_tasks
                   WHERE provider_task_id IS NOT NULL AND status IN ('submitted', 'processing')
                   ORDER BY updated_at ASC, id ASC"""
            ).fetchall()
            return [self._task_result(row) for row in rows]

    @staticmethod
    def _task_result(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        manifest = result.get("reference_manifest_json")
        if manifest is not None:
            result["reference_manifest"] = json.loads(result.pop("reference_manifest_json"))
        return result

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
            return [self._task_result(row) for row in rows]

    def update_generation_task(self, task_id: int, **values: Any) -> Optional[dict[str, Any]]:
        if not values:
            return self.get_generation_task(task_id)
        assignments = [f"{key} = ?" for key in values]
        params = list(values.values()) + [task_id]
        with self._connection() as conn:
            task = conn.execute("SELECT storyboard_id, scene_id FROM generation_tasks WHERE id = ?", (task_id,)).fetchone()
            conn.execute(
                f"UPDATE generation_tasks SET {', '.join(assignments)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                params,
            )
            if task:
                self._add_trace_event(
                    conn, "generation.updated", values,
                    storyboard_id=task["storyboard_id"], scene_id=task["scene_id"], task_id=task_id,
                )
        return self.get_generation_task(task_id)

    def get_generation_task(self, task_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[dict[str, Any]]:
        owns_connection = conn is None
        conn = conn or self._connection()
        try:
            row = conn.execute("SELECT * FROM generation_tasks WHERE id = ?", (task_id,)).fetchone()
            return self._task_result(row) if row else None
        finally:
            if owns_connection:
                conn.close()

    def select_candidate(self, task_id: int, reviewer: str | None, note: str | None) -> Optional[dict[str, Any]]:
        with self._connection() as conn:
            task = conn.execute("SELECT * FROM generation_tasks WHERE id = ?", (task_id,)).fetchone()
            if not task:
                return None
            conn.execute("UPDATE generation_tasks SET selected = 0 WHERE scene_id = ?", (task["scene_id"],))
            conn.execute(
                """UPDATE generation_tasks
                   SET selected = 1, selected_at = CURRENT_TIMESTAMP, selection_reviewer = ?, selection_note = ?
                   WHERE id = ?""",
                (reviewer, note, task_id),
            )
            self._add_trace_event(
                conn, "candidate.selected", {"reviewer": reviewer, "note": note},
                storyboard_id=task["storyboard_id"], scene_id=task["scene_id"], task_id=task_id,
            )
        return self.get_generation_task(task_id)

    def save_quality_check(self, task_id: int, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        with self._connection() as conn:
            task = conn.execute("SELECT * FROM generation_tasks WHERE id = ?", (task_id,)).fetchone()
            if not task:
                return None
            cursor = conn.execute(
                """INSERT INTO quality_checks
                (task_id, engine, status, product_similarity_score, logo_status, ocr_status, decision, summary, details_json, reviewer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id, payload["engine"], payload["status"], payload.get("product_similarity_score"),
                    payload.get("logo_status", "not_applicable"), payload.get("ocr_status", "not_applicable"),
                    payload.get("decision", "review"), payload.get("summary"), self._json(payload.get("details", {})), payload.get("reviewer"),
                ),
            )
            conn.execute(
                "UPDATE generation_tasks SET quality_status = ?, quality_decision = ? WHERE id = ?",
                (payload["status"], payload.get("decision", "review"), task_id),
            )
            self._add_trace_event(
                conn, "quality.checked", {"quality_check_id": cursor.lastrowid, "engine": payload["engine"], "decision": payload.get("decision", "review")},
                storyboard_id=task["storyboard_id"], scene_id=task["scene_id"], task_id=task_id,
            )
        return self.get_generation_task(task_id)

    def get_quality_context(self, task_id: int) -> Optional[dict[str, Any]]:
        with self._connection() as conn:
            task = conn.execute(
                """SELECT t.*, p.name AS product_name, p.brand AS product_brand, p.price AS product_price
                   FROM generation_tasks t
                   JOIN storyboards b ON b.id = t.storyboard_id
                   JOIN products p ON p.id = b.product_id
                   WHERE t.id = ?""",
                (task_id,),
            ).fetchone()
            if not task:
                return None
            result = self._task_result(task)
            result["quality_checks"] = []
            rows = conn.execute(
                "SELECT * FROM quality_checks WHERE task_id = ? ORDER BY id DESC", (task_id,)
            ).fetchall()
            for row in rows:
                check = dict(row)
                check["details"] = json.loads(check.pop("details_json"))
                result["quality_checks"].append(check)
            return result

    def get_storyboard_trace(self, storyboard_id: int) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT * FROM trace_events
                   WHERE storyboard_id = ? OR (
                       product_id = (SELECT product_id FROM storyboards WHERE id = ?)
                       AND storyboard_id IS NULL
                   )
                   ORDER BY id DESC LIMIT 300""", (storyboard_id, storyboard_id)
            ).fetchall()
            events = []
            for row in rows:
                event = dict(row)
                event["payload"] = json.loads(event.pop("payload_json"))
                events.append(event)
            return events

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
                """SELECT s.scene_no, s.target_duration, s.id AS scene_id, t.id, t.composed_video_url,
                          t.composition_status, t.composition_error
                   FROM storyboard_scenes s
                   LEFT JOIN generation_tasks t ON t.id = (
                       SELECT latest.id FROM generation_tasks latest
                       WHERE latest.scene_id = s.id AND latest.composed_video_url IS NOT NULL
                       ORDER BY latest.selected DESC, latest.id DESC LIMIT 1
                   )
                   WHERE s.storyboard_id = ? AND s.generation_strategy = 'image_to_video'
                   ORDER BY s.scene_no""",
                (storyboard_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_unselected_candidate_scenes(self, storyboard_id: int) -> list[int]:
        """存在多个候选时，P2 发布前必须由人工明确选择一个候选。"""
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT s.scene_no
                   FROM storyboard_scenes s
                   JOIN generation_tasks t ON t.scene_id = s.id
                   WHERE s.storyboard_id = ?
                   GROUP BY s.id, s.scene_no
                   HAVING COUNT(t.id) > 1 AND MAX(t.selected) = 0
                   ORDER BY s.scene_no""",
                (storyboard_id,),
            ).fetchall()
            return [row["scene_no"] for row in rows]

    def update_storyboard_final(self, storyboard_id: int, **values: Any) -> Optional[dict[str, Any]]:
        if not values:
            return self.get_storyboard(storyboard_id)
        assignments = [f"{key} = ?" for key in values]
        params = list(values.values()) + [storyboard_id]
        with self._connection() as conn:
            conn.execute(f"UPDATE storyboards SET {', '.join(assignments)} WHERE id = ?", params)
            storyboard = conn.execute("SELECT product_id FROM storyboards WHERE id = ?", (storyboard_id,)).fetchone()
            if storyboard:
                self._add_trace_event(
                    conn, "storyboard.final_updated", values,
                    product_id=storyboard["product_id"], storyboard_id=storyboard_id,
                )
        return self.get_storyboard(storyboard_id)


db = ShopDatabase()
