import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'detection_history.db'

MODEL_DISPLAY_NAMES = {
    'SFGA-YOLO26M': 'SFGA-YOLO26M',
    'yolo26M': 'YOLO26M',
    'yolo11M': 'YOLO11M',
    'yolo26m_BestPt_1': 'YOLO26M',
    'yolo11m_BestPt_0': 'YOLO11M',
    'SFGA-YOLO26M（改进模型）': 'SFGA-YOLO26M',
    'YOLO26M': 'YOLO26M',
    'YOLO11M': 'YOLO11M',
}

ACTIVE_MODEL_DISPLAY_NAMES = {'SFGA-YOLO26M', 'YOLO26M', 'YOLO11M'}


def normalize_model_name(model_name):
    display_name = MODEL_DISPLAY_NAMES.get(str(model_name or '').strip())
    return display_name if display_name in ACTIVE_MODEL_DISPLAY_NAMES else None


def normalize_detection_record(record):
    normalized_name = normalize_model_name(record.get('model_name'))
    if not normalized_name:
        return None
    normalized_record = dict(record)
    normalized_record['model_name'] = normalized_name
    return normalized_record


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
    records = (normalize_detection_record(dict(r)) for r in rows)
    return [record for record in records if record]


def get_detection_by_id(detection_id):
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM detections WHERE id = ?', (detection_id,)
    ).fetchone()
    conn.close()
    return normalize_detection_record(dict(row)) if row else None


def get_stats():
    conn = get_db()
    rows = conn.execute(
        'SELECT timestamp, model_name, inference_time_s FROM detections ORDER BY timestamp'
    ).fetchall()
    conn.close()

    records = []
    for row in rows:
        normalized_name = normalize_model_name(row['model_name'])
        if not normalized_name:
            continue
        records.append({
            'timestamp': row['timestamp'],
            'model_name': normalized_name,
            'inference_time_s': row['inference_time_s'] or 0,
        })

    model_usage = {}
    daily_usage = {}
    total_time = 0
    timed_count = 0

    for record in records:
        model_name = record['model_name']
        model_usage[model_name] = model_usage.get(model_name, 0) + 1

        day = str(record['timestamp'] or '')[:10]
        if day:
            daily_usage[day] = daily_usage.get(day, 0) + 1

        inference_time = record['inference_time_s']
        if inference_time:
            total_time += inference_time
            timed_count += 1

    today = date.today().isoformat()
    daily_counts = [
        {'date': date_key, 'count': daily_usage[date_key]}
        for date_key in sorted(daily_usage)
    ][-30:]

    return {
        'total_detections': len(records),
        'today_detections': daily_usage.get(today, 0),
        'avg_inference_time_s': round(total_time / timed_count, 3) if timed_count else 0,
        'model_usage': model_usage,
        'daily_counts': daily_counts,
    }


init_db()
