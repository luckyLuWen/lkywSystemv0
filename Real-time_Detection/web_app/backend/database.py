import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'detection_history.db'


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            model_name TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            saved_filename TEXT NOT NULL,
            result_filename TEXT NOT NULL,
            detection_count INTEGER NOT NULL,
            detections_json TEXT NOT NULL,
            inference_time_s REAL NOT NULL,
            conf_threshold REAL NOT NULL,
            iou_threshold REAL NOT NULL,
            source_type TEXT DEFAULT 'image'
        )
    ''')
    # Migrate old column name if exists
    cols = [r[1] for r in conn.execute('PRAGMA table_info(detections)').fetchall()]
    if 'inference_time_ms' in cols and 'inference_time_s' not in cols:
        conn.execute('ALTER TABLE detections RENAME COLUMN inference_time_ms TO inference_time_s')
    conn.commit()
    conn.close()


def save_detection(timestamp, model_name, original_filename, saved_filename,
                   result_filename, detection_count, detections_json,
                   inference_time_s, conf_threshold, iou_threshold,
                   source_type='image'):
    conn = get_db()
    conn.execute('''
        INSERT INTO detections (timestamp, model_name, original_filename,
            saved_filename, result_filename, detection_count, detections_json,
            inference_time_s, conf_threshold, iou_threshold, source_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, model_name, original_filename, saved_filename,
          result_filename, detection_count, detections_json,
          inference_time_s, conf_threshold, iou_threshold, source_type))
    conn.commit()
    row_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    return row_id


def get_detections(limit=50, offset=0):
    conn = get_db()
    rows = conn.execute(
        'SELECT id, timestamp, model_name, original_filename, saved_filename, '
        'result_filename, detection_count, inference_time_s, source_type '
        'FROM detections ORDER BY id DESC LIMIT ? OFFSET ?',
        (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_detection_by_id(detection_id):
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM detections WHERE id = ?', (detection_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_stats():
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) FROM detections').fetchone()[0]
    today_count = conn.execute(
        "SELECT COUNT(*) FROM detections WHERE date(timestamp) = date('now')"
    ).fetchone()[0]
    avg_time = conn.execute(
        'SELECT AVG(inference_time_s) FROM detections'
    ).fetchone()[0]
    model_usage_rows = conn.execute(
        'SELECT model_name, COUNT(*) as cnt FROM detections GROUP BY model_name ORDER BY cnt DESC'
    ).fetchall()
    daily_rows = conn.execute(
        "SELECT date(timestamp) as date, COUNT(*) as cnt "
        "FROM detections WHERE timestamp >= date('now', '-30 days') "
        "GROUP BY date(timestamp) ORDER BY date"
    ).fetchall()
    conn.close()

    return {
        'total_detections': total or 0,
        'today_detections': today_count or 0,
        'avg_inference_time_s': round(avg_time, 3) if avg_time else 0,
        'model_usage': {r['model_name']: r['cnt'] for r in model_usage_rows},
        'daily_counts': [{'date': r['date'], 'count': r['cnt']} for r in daily_rows],
    }


init_db()
