import json
from flask import Blueprint, request, jsonify
from database import (
    delete_detection,
    delete_detections,
    get_detections,
    get_detections_count,
    get_detection_by_id,
)

history_bp = Blueprint('history', __name__)


@history_bp.route('/api/history', methods=['GET'])
def list_history():
    requested_limit = request.args.get('limit', 50, type=int) or 50
    requested_offset = request.args.get('offset', 0, type=int) or 0
    limit = min(max(requested_limit, 1), 100)
    offset = max(requested_offset, 0)
    model_name = request.args.get('model', '').strip() or None
    label = request.args.get('label', '').strip() or None
    source_type = request.args.get('source_type', '').strip() or None
    records = get_detections(
        limit=limit,
        offset=offset,
        model_name=model_name,
        label=label,
        source_type=source_type,
    )
    total = get_detections_count(
        model_name=model_name,
        label=label,
        source_type=source_type,
    )
    return jsonify({
        'success': True,
        'records': records,
        'total': total,
        'limit': limit,
        'offset': offset,
    })


@history_bp.route('/api/history/<int:detection_id>', methods=['GET'])
def get_history_detail(detection_id):
    record = get_detection_by_id(detection_id)
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    record['detections'] = json.loads(record['detections_json'])
    return jsonify({'success': True, 'record': record})


@history_bp.route('/api/history/batch', methods=['DELETE'])
def delete_history_records():
    payload = request.get_json(silent=True) or {}
    detection_ids = payload.get('ids')

    if not isinstance(detection_ids, list) or not detection_ids:
        return jsonify({'error': 'ids must be a non-empty array'}), 400
    if len(detection_ids) > 500:
        return jsonify({'error': 'A maximum of 500 records can be deleted at once'}), 400
    if any(type(detection_id) is not int or detection_id <= 0 for detection_id in detection_ids):
        return jsonify({'error': 'Every id must be a positive integer'}), 400

    deleted_ids = delete_detections(detection_ids)
    return jsonify({
        'success': True,
        'deleted_count': len(deleted_ids),
        'deleted_ids': deleted_ids,
    })


@history_bp.route('/api/history/<int:detection_id>', methods=['DELETE'])
def delete_history_record(detection_id):
    deleted = delete_detection(detection_id)
    if not deleted:
        return jsonify({'error': 'Record not found'}), 404
    return jsonify({'success': True})
