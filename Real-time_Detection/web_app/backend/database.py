import hashlib
import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'detection_history.db'
UPLOAD_DIR = Path(__file__).resolve().parent / 'uploads'

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


LABEL_ALIASES = {
    'car_fire': ['car_fire', 'carFire'],
    'lkyw_fire': ['lkyw_fire', 'lkywFire'],
    'car_nofire': ['car_nofire', 'carNofire', 'car_normal', 'carNormal'],
    'lkyw_nofire': ['lkyw_nofire', 'lkywNofire', 'lkyw_normal', 'lkywNormal'],
}

LABEL_CANONICAL = {
    alias.lower().replace('-', '_').replace(' ', '_'): canonical
    for canonical, aliases in LABEL_ALIASES.items()
    for alias in aliases
}


def normalize_detection_label(label):
    raw_label = str(label or '').strip()
    if not raw_label:
        return ''
    normalized_key = raw_label.lower().replace('-', '_').replace(' ', '_')
    return LABEL_CANONICAL.get(normalized_key, raw_label)


def get_label_query_names(label):
    canonical_label = normalize_detection_label(label)
    aliases = LABEL_ALIASES.get(canonical_label, [canonical_label])
    names = []
    for alias in aliases + [canonical_label, str(label or '').strip()]:
        if alias and alias not in names:
            names.append(alias)
    return names


def normalize_model_name(model_name):
    display_name = MODEL_DISPLAY_NAMES.get(str(model_name or '').strip())
    return display_name if display_name in ACTIVE_MODEL_DISPLAY_NAMES else None


def get_model_query_names(model_name):
    normalized_name = normalize_model_name(model_name)
    if not normalized_name:
        return []
    names = [
        raw_name
        for raw_name, display_name in MODEL_DISPLAY_NAMES.items()
        if display_name == normalized_name
    ]
    if normalized_name not in names:
        names.append(normalized_name)
    return names


def normalize_detection_record(record):
    normalized_name = normalize_model_name(record.get('model_name'))
    if not normalized_name:
        return None
    normalized_record = dict(record)
    normalized_record['model_name'] = normalized_name
    return normalized_record



def extract_detection_labels(detections_json):
    import json

    try:
        detections = json.loads(detections_json or '[]')
    except (TypeError, json.JSONDecodeError):
        return []

    labels = []
    for item in detections:
        label = normalize_detection_label(item.get('class', ''))
        if label and label not in labels:
            labels.append(label)
    return labels


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn



def calculate_sha256(file_path):
    digest = hashlib.sha256()
    with open(file_path, 'rb') as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def backfill_image_hashes(conn):
    rows = conn.execute(
        "SELECT id, saved_filename FROM detections WHERE image_hash IS NULL OR image_hash = ''"
    ).fetchall()
    for row in rows:
        saved_filename = row['saved_filename']
        if not saved_filename:
            continue
        file_path = UPLOAD_DIR / saved_filename
        if not file_path.exists():
            continue
        try:
            image_hash = calculate_sha256(file_path)
        except OSError:
            continue
        conn.execute(
            'UPDATE detections SET image_hash = ? WHERE id = ?',
            (image_hash, row['id'])
        )


def deduplicate_detections(conn):
    duplicate_groups = conn.execute(
        """
        SELECT image_hash, model_name, conf_threshold, iou_threshold, COUNT(*) AS row_count
        FROM detections
        WHERE image_hash IS NOT NULL AND image_hash != ''
        GROUP BY image_hash, model_name, conf_threshold, iou_threshold
        HAVING row_count > 1
        """
    ).fetchall()

    for group in duplicate_groups:
        rows = conn.execute(
            """
            SELECT id, inference_time_s
            FROM detections
            WHERE image_hash = ?
              AND model_name = ?
              AND conf_threshold = ?
              AND iou_threshold = ?
            ORDER BY inference_time_s ASC, id DESC
            """,
            (
                group['image_hash'], group['model_name'],
                group['conf_threshold'], group['iou_threshold']
            )
        ).fetchall()
        if not rows:
            continue
        delete_ids = [row['id'] for row in rows[1:]]
        if delete_ids:
            placeholders = ','.join('?' for _ in delete_ids)
            conn.execute(f'DELETE FROM detections WHERE id IN ({placeholders})', delete_ids)


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            model_name TEXT NOT NULL,
            image_hash TEXT,
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
    if 'image_hash' not in cols:
        conn.execute('ALTER TABLE detections ADD COLUMN image_hash TEXT')

    backfill_image_hashes(conn)
    deduplicate_detections(conn)
    conn.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_detections_image_model_params
        ON detections (image_hash, model_name, conf_threshold, iou_threshold)
        WHERE image_hash IS NOT NULL AND image_hash != ''
    ''')
    conn.commit()
    conn.close()


def save_detection(timestamp, model_name, original_filename, saved_filename,
                   result_filename, detection_count, detections_json,
                   inference_time_s, conf_threshold, iou_threshold,
                   source_type='image', image_hash=None):
    conn = get_db()
    conf_threshold = round(float(conf_threshold), 6)
    iou_threshold = round(float(iou_threshold), 6)
    inference_time_s = round(float(inference_time_s), 3)

    existing = None
    if image_hash:
        existing = conn.execute(
            '''
            SELECT id, inference_time_s
            FROM detections
            WHERE image_hash = ?
              AND model_name = ?
              AND conf_threshold = ?
              AND iou_threshold = ?
            ''',
            (image_hash, model_name, conf_threshold, iou_threshold)
        ).fetchone()

    if existing:
        existing_time = existing['inference_time_s']
        if existing_time is None or inference_time_s < existing_time:
            conn.execute(
                '''
                UPDATE detections
                SET timestamp = ?,
                    original_filename = ?,
                    saved_filename = ?,
                    result_filename = ?,
                    detection_count = ?,
                    detections_json = ?,
                    inference_time_s = ?,
                    source_type = ?
                WHERE id = ?
                ''',
                (timestamp, original_filename, saved_filename, result_filename,
                 detection_count, detections_json, inference_time_s, source_type, existing['id'])
            )
        conn.commit()
        row_id = existing['id']
        conn.close()
        return row_id

    conn.execute('''
        INSERT INTO detections (timestamp, model_name, image_hash, original_filename,
            saved_filename, result_filename, detection_count, detections_json,
            inference_time_s, conf_threshold, iou_threshold, source_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, model_name, image_hash, original_filename, saved_filename,
          result_filename, detection_count, detections_json,
          inference_time_s, conf_threshold, iou_threshold, source_type))
    conn.commit()
    row_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    return row_id


def get_detections(limit=50, offset=0, model_name=None, label=None):
    conn = get_db()
    query = (
        'SELECT id, timestamp, model_name, original_filename, saved_filename, '
        'result_filename, detection_count, detections_json, inference_time_s, source_type '
        'FROM detections'
    )
    where_clauses = []
    params = []

    if model_name:
        model_query_names = get_model_query_names(model_name)
        if not model_query_names:
            conn.close()
            return []
        placeholders = ','.join('?' for _ in model_query_names)
        where_clauses.append(f'model_name IN ({placeholders})')
        params.extend(model_query_names)

    if label:
        label_query_names = get_label_query_names(label)
        label_clauses = []
        for label_name in label_query_names:
            label_clauses.append('detections_json LIKE ?')
            params.append(f'%"class": "{label_name}"%')
            label_clauses.append('detections_json LIKE ?')
            params.append(f'%"class":"{label_name}"%')
        where_clauses.append('(' + ' OR '.join(label_clauses) + ')')

    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)

    query += ' ORDER BY id DESC LIMIT ? OFFSET ?'
    params.extend((limit, offset))
    rows = conn.execute(query, params).fetchall()
    conn.close()

    records = []
    for row in rows:
        record = normalize_detection_record(dict(row))
        if not record:
            continue
        record['labels'] = extract_detection_labels(record.get('detections_json'))
        record.pop('detections_json', None)
        records.append(record)
    return records


def get_detection_by_id(detection_id):
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM detections WHERE id = ?', (detection_id,)
    ).fetchone()
    conn.close()
    return normalize_detection_record(dict(row)) if row else None


def delete_detection(detection_id):
    conn = get_db()
    row = conn.execute(
        'SELECT saved_filename, result_filename FROM detections WHERE id = ?',
        (detection_id,)
    ).fetchone()
    if not row:
        conn.close()
        return False

    conn.execute('DELETE FROM detections WHERE id = ?', (detection_id,))
    conn.commit()
    conn.close()
    return True


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
