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
    return conn


def init_db() -> None:
    """创建数据库和初始数据。"""
    conn = get_connection()
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
    conn.close()
    print(f"[救援点DB] 数据库已初始化，共 {len(seed_data)} 条救援点 + {len(agent_seed)} 条智能体POI记录")


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
        # ===== 油罐车泄露现场 (leak) — 黄冈地区 =====
        ("leak", "团风县消防救援大队",      30.6435, 114.8724),
        ("leak", "黄冈市黄州区路口镇专职消防队", 30.5158, 114.9238),
        ("leak", "黄冈市消防救援支队特勤站",  30.4536, 114.8785),
        ("leak", "黄冈市黄州区体育路消防站",  30.4472, 114.8813),

        # ===== 货车追尾现场 (crash) — 仙桃地区 =====
        ("crash", "仙桃市毛嘴镇专职消防站",   30.3354, 113.4275),
        ("crash", "仙桃市三伏潭镇专职消防队", 30.3268, 113.2020),
        ("crash", "仙桃市消防救援大队",      30.3623, 113.4541),
        ("crash", "天门市消防救援支队",      30.6654, 113.1682),
        ("crash", "潜江市园林消防救援站",     30.4025, 112.8961),
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


def _agent_poi_seed() -> list[tuple]:
    """五类救援智能体 POI 种子数据（每类型2-3个真实站点）。"""
    return [
        # ===== 油罐车泄露现场 (leak) — 团风/黄冈地区 =====
        # 医疗急救
        ("leak", "medical", "团风县人民医院",           30.6461, 114.8698),
        ("leak", "medical", "团风县中医医院",           30.6423, 114.8735),
        ("leak", "medical", "黄冈市黄州区人民医院",     30.4512, 114.8768),
        # 消防灭火
        ("leak", "fire",    "团风县公安消防大队",       30.6426, 114.8751),
        ("leak", "fire",    "黄冈市黄州区路口镇专职消防队", 30.5158, 114.9238),
        ("leak", "fire",    "黄冈市消防救援支队特勤站", 30.4536, 114.8785),
        # 公安交警
        ("leak", "police",  "团风县公安局交警大队",     30.6391, 114.8716),
        ("leak", "police",  "团风县团风水陆派出所",     30.6415, 114.8703),
        ("leak", "police",  "黄冈市公安局黄州分局",     30.4498, 114.8792),
        # 防化部队
        ("leak", "hazmat",  "团风县消防特勤防化站",     30.6480, 114.8689),
        ("leak", "hazmat",  "团风县应急管理局",         30.6405, 114.8738),
        ("leak", "hazmat",  "黄冈市应急管理局",         30.4523, 114.8761),
        # 交通路政
        ("leak", "road",    "团风县路政管理大队",       30.6412, 114.8780),
        ("leak", "road",    "团风县交通运输局",         30.6389, 114.8745),
        ("leak", "road",    "黄冈市公路管理局",         30.4506, 114.8801),

        # ===== 货车追尾现场 (crash) — 高速沿线 + 三伏潭/胡场镇 =====
        # 医疗急救（高速急救点 + 乡镇卫生院）
        ("crash", "medical", "仙桃西高速急救站",      30.3826, 113.1118),
        ("crash", "medical", "三伏潭镇卫生院",        30.3272, 113.2018),
        ("crash", "medical", "胡场镇卫生院",          30.3581, 113.2103),
        # 消防灭火（高速消防执勤点 + 乡镇消防队）
        ("crash", "fire",    "仙桃西高速消防执勤点",  30.3815, 113.1095),
        ("crash", "fire",    "胡场镇消防执勤点",      30.3558, 113.2120),
        ("crash", "fire",    "三伏潭镇专职消防队",    30.3263, 113.2041),
        # 公安交警（高速巡逻车 + 高速中队 + 本地派出所）
        ("crash", "police",  "仙桃高速交警巡逻车",    30.3802, 113.1153),
        ("crash", "police",  "仙桃市交警高速大队三伏潭中队", 30.3582, 113.1984),
        ("crash", "police",  "仙桃市胡场派出所",      30.3556, 113.2082),
        # 防化部队（高速应急物资点 + 乡镇安监站）
        ("crash", "hazmat",  "仙桃西应急物资储备点",  30.3835, 113.1078),
        ("crash", "hazmat",  "胡场镇安全生产监督管理站", 30.3568, 113.2091),
        ("crash", "hazmat",  "三伏潭镇应急管理站",    30.3281, 113.2012),
        # 交通路政（高速路政执勤点 + 道班）
        ("crash", "road",    "沪渝高速仙桃段路政执勤点", 30.3813, 113.1112),
        ("crash", "road",    "湖北高速路政仙桃西支队", 30.3563, 113.1952),
        ("crash", "road",    "仙桃市公路局三伏潭道班", 30.3254, 113.1988),
    ]


if __name__ == "__main__":
    init_db()
