import json
from collections import Counter
from flask import Blueprint, jsonify
from database import (
    get_db,
    get_stats as db_get_stats,
    normalize_detection_label,
    normalize_model_name,
)

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/api/stats', methods=['GET'])
def get_statistics():
    base_stats = db_get_stats()

    conn = get_db()
    rows = conn.execute('SELECT model_name, detections_json FROM detections').fetchall()
    conn.close()

    class_counter = Counter()
    for row in rows:
        if not normalize_model_name(row['model_name']):
            continue
        try:
            dets = json.loads(row['detections_json'] or '[]')
        except (TypeError, json.JSONDecodeError):
            continue
        for d in dets:
            if not isinstance(d, dict):
                continue
            label = normalize_detection_label(d.get('class', ''))
            if label:
                class_counter[label] += 1

    base_stats['class_distribution'] = dict(class_counter)
    return jsonify({'success': True, 'stats': base_stats})
