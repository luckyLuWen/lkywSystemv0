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


def _agent_poi_seed() -> list[tuple]:
    """五类救援智能体 POI 种子数据（每类型2-3个真实站点）。"""
    return [
        # ===== 油罐车泄流现场 (leak) — 团风及黄州地区，精确定位在路旁建筑上 =====
        # 医疗急救
        ("leak", "medical", "团风县人民医院",           30.6456, 114.8722),
        ("leak", "medical", "淋山河镇中心卫生院",       30.6778, 114.8442),
        ("leak", "medical", "马曹庙镇卫生院",           30.6515, 114.9325),
        # 消防灭火
        ("leak", "fire",    "团风县公安消防大队",       30.6435, 114.8735),
        ("leak", "fire",    "江北工业园专职消防队",     30.6185, 114.8885),
        ("leak", "fire",    "回龙山镇消防备勤点",       30.6215, 114.9432),
        # 公安交警
        ("leak", "police",  "团风县公安局交警大队",     30.6395, 114.8690),
        ("leak", "police",  "方高坪镇派出所",           30.6820, 114.8745),
        ("leak", "police",  "总路咀镇交警中队",         30.6085, 114.9302),
        # 防化部队
        ("leak", "hazmat",  "团风县消防特勤防化站",     30.6510, 114.8650),
        ("leak", "hazmat",  "黄州区防化增援大队",       30.4552, 114.8798),
        ("leak", "hazmat",  "团风港区危化应急站",       30.6356, 114.8624),
        # 交通路政
        ("leak", "road",    "团风县路政管理大队",       30.6420, 114.8785),
        ("leak", "road",    "上巴河镇道班",             30.6682, 114.9535),
        ("leak", "road",    "大桥收费站管理处",         30.6305, 114.8655),

        # ===== 货车追尾现场 (crash) — 事故点(30.3855,113.1048)，均匀合理的分布于主干道旁的房屋区域 =====
        # 医疗急救
        ("crash", "medical", "剅河镇卫生院",          30.3745, 113.0410),
        ("crash", "medical", "三伏潭镇卫生院分院",    30.3295, 113.2025),
        ("crash", "medical", "胡场镇卫生院",          30.3502, 113.2085),
        # 消防灭火
        ("crash", "fire",    "剅河镇应急消防救援站",    30.3765, 113.0420),
        ("crash", "fire",    "三伏潭镇专职消防队",      30.3265, 113.2030),
        ("crash", "fire",    "胡场镇消防支队",          30.3496, 113.2135),
        # 公安交警
        ("crash", "police",  "剅河镇派出所",            30.3735, 113.0405),
        ("crash", "police",  "三伏潭镇交警中队",        30.3312, 113.1985),
        ("crash", "police",  "胡场镇公安局派出所",      30.3505, 113.2065),
        # 防化部队
        ("crash", "hazmat",  "剅河镇应急安全中心",      30.3808, 113.0475),
        ("crash", "hazmat",  "三伏潭镇危化品监管站",    30.3250, 113.2055),
        ("crash", "hazmat",  "胡场镇环保局监察站",      30.3499, 113.2120),
        # 交通路政
        ("crash", "road",    "剅河镇路政管理所",        30.3725, 113.0400),
        ("crash", "road",    "三伏潭镇公路段道班",      30.3275, 113.1960),
        ("crash", "road",    "胡场镇路政中队",          30.3510, 113.2020),
    ]


if __name__ == "__main__":
    init_db()
