import json
from flask import Blueprint, request, jsonify
from database import delete_detection, get_detections, get_detection_by_id

history_bp = Blueprint('history', __name__)


@history_bp.route('/api/history', methods=['GET'])
def list_history():
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    model_name = request.args.get('model', '').strip() or None
    label = request.args.get('label', '').strip() or None
    records = get_detections(limit=limit, offset=offset, model_name=model_name, label=label)
    return jsonify({'success': True, 'records': records})


@history_bp.route('/api/history/<int:detection_id>', methods=['GET'])
def get_history_detail(detection_id):
    record = get_detection_by_id(detection_id)
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    record['detections'] = json.loads(record['detections_json'])
    return jsonify({'success': True, 'record': record})


@history_bp.route('/api/history/<int:detection_id>', methods=['DELETE'])
def delete_history_record(detection_id):
    deleted = delete_detection(detection_id)
    if not deleted:
        return jsonify({'error': 'Record not found'}), 404
    return jsonify({'success': True})
