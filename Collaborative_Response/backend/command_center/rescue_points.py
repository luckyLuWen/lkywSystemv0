"""
救援点数据库管理模块。
SQLite 数据库存储各事故场景周边的救援站点（消防队），
供路径规划引擎自动选取最优起点。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

AGENT_CONFIG = {
    "medical": {"label": "医疗急救", "color": "#22c55e", "icon": "plus"},
    "fire":    {"label": "消防灭火", "color": "#f97316", "icon": "fire"},
    "police":  {"label": "公安交警", "color": "#3b82f6", "icon": "flag"},
    "hazmat":  {"label": "防化部队", "color": "#a855f7", "icon": "flash"},
    "road":    {"label": "交通路政", "color": "#94a3b8", "icon": "wrench"},
}

DB_PATH = Path(__file__).resolve().parent / "rescue_points.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    
    # 自动检测关键表是否存在，如果不存在则自动初始化数据库，防止 OperationalError
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rescue_points'")
        if not cursor.fetchone():
            _initialize_db_with_connection(conn)
    except sqlite3.Error:
        pass
        
    return conn


def _initialize_db_with_connection(conn: sqlite3.Connection) -> None:
    """使用已有连接初始化表结构并填入种子数据"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rescue_points (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario   TEXT    NOT NULL,
            name       TEXT    NOT NULL,
            lat        REAL    NOT NULL,
            lon        REAL    NOT NULL,
            is_active  INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_pois (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario   TEXT    NOT NULL,
            agent_key  TEXT    NOT NULL,
            name       TEXT    NOT NULL,
            lat        REAL    NOT NULL,
            lon        REAL    NOT NULL,
            is_active  INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS selection_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario    TEXT    NOT NULL,
            point_id    INTEGER NOT NULL,
            reason      TEXT,
            selected_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (point_id) REFERENCES rescue_points(id)
        )
    """)

    # 清空并重新导入种子数据
    conn.execute("DELETE FROM rescue_points")
    seed_data = _seed_data()
    conn.executemany(
        "INSERT INTO rescue_points (scenario, name, lat, lon) VALUES (?, ?, ?, ?)",
        seed_data,
    )
    # 五类救援智能体 POI 数据
    conn.execute("DELETE FROM agent_pois")
    agent_seed = _agent_poi_seed()
    conn.executemany(
        "INSERT INTO agent_pois (scenario, agent_key, name, lat, lon) VALUES (?, ?, ?, ?, ?)",
        agent_seed,
    )
    conn.commit()
    print(f"[救援点DB] 数据库已自动初始化，共 {len(seed_data)} 条救援点 + {len(agent_seed)} 条智能体POI记录")


def init_db() -> None:
    """手动创建/刷新数据库和初始数据。"""
    conn = get_connection()
    _initialize_db_with_connection(conn)
    conn.close()


def get_rescue_points(scenario: str) -> list[dict]:
    """获取指定场景的所有活跃救援点。"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, lat, lon FROM rescue_points WHERE scenario = ? AND is_active = 1",
        (scenario,),
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "name": r["name"], "lat": r["lat"], "lon": r["lon"]} for r in rows]


def log_selection(scenario: str, point_id: int, reason: str = "") -> None:
    """记录某次最优起点的选择结果。"""
    conn = get_connection()
    conn.execute(
        "INSERT INTO selection_log (scenario, point_id, reason) VALUES (?, ?, ?)",
        (scenario, point_id, reason),
    )
    conn.commit()
    conn.close()


def _seed_data() -> list[tuple]:
    """种子数据：各事故场景周边 4-5 个消防站点（真实名称 + 近似坐标）。"""
    return [
        # ===== 油罐车泄露现场 (leak) — 团风县城周边 5km 内 =====
        ("leak", "团风县消防救援大队",      30.6450, 114.8710),
        ("leak", "团风镇应急消防站",        30.6382, 114.8785),
        ("leak", "团风县城关消防备勤点",     30.6468, 114.8691),
        ("leak", "团风县团风大道消防站",     30.6360, 114.8840),

        # ===== 货车追尾现场 (crash) — 仙桃地区 =====
        ("crash", "仙桃市毛嘴镇专职消防站",   30.3354, 113.0475),
        ("crash", "仙桃市三伏潭镇专职消防队", 30.3282, 113.2010),
        ("crash", "仙桃市消防救援大队",      30.3623, 113.4541),
        ("crash", "仙桃市剅河镇专职消防队",   30.3752, 113.0425),
        ("crash", "仙桃市胡场镇专职消防队",   30.3500, 113.2110),
    ]


def get_agent_pois(scenario: str) -> list[dict]:
    """获取指定场景所有五类救援智能体 POI。"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, agent_key, name, lat, lon FROM agent_pois WHERE scenario = ? AND is_active = 1",
        (scenario,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "agent_key": r["agent_key"],
            "name": r["name"],
            "lat": r["lat"],
            "lon": r["lon"],
            "label": AGENT_CONFIG.get(r["agent_key"], {}).get("label", r["agent_key"]),
            "color": AGENT_CONFIG.get(r["agent_key"], {}).get("color", "#888"),
            "icon": AGENT_CONFIG.get(r["agent_key"], {}).get("icon", "flag"),
        }
        for r in rows
    ]


def get_all_pois_full(scenario: str) -> list[dict]:
    """获取指定场景的所有救援点和五类智能体 POI 的全量信息。"""
    conn = get_connection()
    agent_rows = conn.execute(
        "SELECT id, agent_key, name, lat, lon FROM agent_pois WHERE scenario = ? AND is_active = 1",
        (scenario,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "agent_key": r["agent_key"],
            "name": r["name"],
            "lat": r["lat"],
            "lon": r["lon"],
            "label": AGENT_CONFIG.get(r["agent_key"], {}).get("label", r["agent_key"]),
            "color": AGENT_CONFIG.get(r["agent_key"], {}).get("color", "#888"),
        }
        for r in agent_rows
    ]



def update_poi_locations(scenario: str, poi_list: list[dict]) -> None:
    """更新指定场景的 POI 经纬度位置（同步更新 agent_pois 与 rescue_points 表）。"""
    conn = get_connection()
    cursor = conn.cursor()
    for item in poi_list:
        name = item.get("name")
        lat = item.get("lat")
        lon = item.get("lon")
        if not name or lat is None or lon is None:
            continue
        cursor.execute(
            "UPDATE agent_pois SET lat = ?, lon = ? WHERE scenario = ? AND name = ?",
            (float(lat), float(lon), scenario, name),
        )
        cursor.execute(
            "UPDATE rescue_points SET lat = ?, lon = ? WHERE scenario = ? AND name = ?",
            (float(lat), float(lon), scenario, name),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()

