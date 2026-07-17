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
        # ===== 油罐车泄露现场 (leak) — 团风县城周边 5km 内 =====
        ("leak", "团风县消防救援大队",      30.6435, 114.8724),
        ("leak", "团风镇应急消防站",        30.6382, 114.8785),
        ("leak", "团风县城关消防备勤点",     30.6468, 114.8691),
        ("leak", "团风县团风大道消防站",     30.6360, 114.8840),

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
        # ===== 油罐车泄露现场 (leak) — 团风县城及周边5km内 =====
        # 医疗急救
        ("leak", "medical", "团风县人民医院",           30.6461, 114.8698),
        ("leak", "medical", "团风县中医医院",           30.6423, 114.8735),
        ("leak", "medical", "团风县妇幼保健院",         30.6400, 114.8760),
        # 消防灭火
        ("leak", "fire",    "团风县公安消防大队",       30.6426, 114.8751),
        ("leak", "fire",    "团风县城北消防站",         30.6480, 114.8700),
        ("leak", "fire",    "团风大道消防执勤点",       30.6360, 114.8840),
        # 公安交警
        ("leak", "police",  "团风县公安局交警大队",     30.6391, 114.8716),
        ("leak", "police",  "团风县团风水陆派出所",     30.6415, 114.8703),
        ("leak", "police",  "团风县城东派出所",         30.6440, 114.8680),
        # 防化部队
        ("leak", "hazmat",  "团风县消防特勤防化站",     30.6480, 114.8689),
        ("leak", "hazmat",  "团风县应急管理局",         30.6405, 114.8738),
        ("leak", "hazmat",  "团风县城南应急站",         30.6350, 114.8800),
        # 交通路政
        ("leak", "road",    "团风县路政管理大队",       30.6412, 114.8780),
        ("leak", "road",    "团风县交通运输局",         30.6389, 114.8745),
        ("leak", "road",    "团风大道公路管理站",       30.6330, 114.8820),

        # ===== 货车追尾现场 (crash) — 事故点(30.3855,113.1048)，9个镇/路口自然分布3-12km =====
        # 胡场镇S321(30.356,113.208)北10km | 三伏潭镇X023(30.328,113.201)东北11km
        # 杨林尾镇(30.310,113.099)南9km | 剅河镇(30.378,113.032)西7km | 陈场镇(30.283,113.048)西南12km
        # 仙桃西站(30.342,113.215)东10km | 张沟镇(30.300,113.170)东南12km | 郭河镇(30.320,113.100)南8km
        # 通海口镇(30.268,113.038)西南14km
        # 医疗急救（9个不同方向）
        ("crash", "medical", "胡场镇卫生院",          30.3560, 113.2090),
        ("crash", "medical", "杨林尾镇卫生院",        30.3100, 113.0990),
        ("crash", "medical", "剅河镇卫生院",          30.3780, 113.0330),
        # 消防灭火
        ("crash", "fire",    "三伏潭镇专职消防队",    30.3263, 113.2020),
        ("crash", "fire",    "剅河镇消防执勤点",      30.3780, 113.0310),
        ("crash", "fire",    "陈场镇消防站",          30.2830, 113.0490),
        # 公安交警
        ("crash", "police",  "仙桃市胡场派出所",      30.3556, 113.2100),
        ("crash", "police",  "仙桃市公安局三伏潭派出所", 30.3305, 113.2010),
        ("crash", "police",  "杨林尾镇派出所",        30.3110, 113.0980),
        # 防化部队
        ("crash", "hazmat",  "剅河镇安监站",          30.3780, 113.0320),
        ("crash", "hazmat",  "胡场镇安监站",          30.3558, 113.2110),
        ("crash", "hazmat",  "三伏潭镇应急管理站",    30.3281, 113.2030),
        # 交通路政
        ("crash", "road",    "仙桃市公路局三伏潭道班", 30.3254, 113.2000),
        ("crash", "road",    "胡场镇交通管理站",      30.3558, 113.2080),
        ("crash", "road",    "陈场镇道班",            30.2830, 113.0500),
    ]


if __name__ == "__main__":
    init_db()
