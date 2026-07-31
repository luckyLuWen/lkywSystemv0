from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import sys
import time
import threading

# 必须在导入 torch 之前设置环境变量
os.environ['TORCH_LOAD_WEIGHTS_ONLY'] = '0'

import cv2
import numpy as np
import torch
from sfga_compat import register_sfga_modules
from lca_compat import register_lca_modules

register_sfga_modules()
register_lca_modules()

from ultralytics import YOLO
from datetime import datetime
import base64
import json
from pathlib import Path
import warnings
from rtsp_detector import RTSPDetector
from database import calculate_sha256, save_detection
from history_routes import history_bp
from stats_routes import stats_bp



# 设置 torch.load 的 weights_only 参数为 False 以兼容旧模型
# 添加 ultralytics 相关类到安全全局列表
try:
    from ultralytics.nn.tasks import DetectionModel
    torch.serialization.add_safe_globals([DetectionModel])
except:
    pass

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', message='.*weights_only.*')
warnings.filterwarnings('ignore', message='.*Unsupported.*')

app = Flask(__name__)
CORS(app)
app.register_blueprint(history_bp)
app.register_blueprint(stats_bp)

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[2]
INTEGRATION_CLIENT_DIR = REPO_ROOT / "Integration_Hub"
if str(INTEGRATION_CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_CLIENT_DIR))

try:
    from event_client import (
        IntegrationCommandClient,
        IntegrationEventPublisher,
        build_command_status_payload,
    )
except Exception:
    class IntegrationEventPublisher:
        def __init__(self, *args, **kwargs):
            pass

        def publish(self, *args, **kwargs):
            return False

    class IntegrationCommandClient:
        def __init__(self, *args, **kwargs):
            pass

        def poll(self, *args, **kwargs):
            return []

    def build_command_status_payload(command, status, **kwargs):
        return {'commandId': command.get('commandId', ''), 'status': status, **kwargs}

INTEGRATION_SOURCE_ID = os.getenv("INTEGRATION_SOURCE_ID", "real-time-detection")
EVENT_PUBLISHER = IntegrationEventPublisher(source=INTEGRATION_SOURCE_ID)
COMMAND_CLIENT = IntegrationCommandClient(
    target=INTEGRATION_SOURCE_ID,
    targets=[
        INTEGRATION_SOURCE_ID,
        "realtime-detection",
        "real-time-detection",
        "detection",
    ],
)
DETECTION_EVENT_COOLDOWN_SECONDS = float(os.getenv("DETECTION_EVENT_COOLDOWN_SECONDS", "10"))
last_detection_event_at = {}

# Configuration
UPLOAD_FOLDER = str(BASE_DIR / 'uploads')
RESULT_FOLDER = str(BASE_DIR / 'results')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'webp', 'mp4', 'avi', 'mov'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# Load YOLO model
MODELS = {}

WEIGHTS_DIR = Path('../../LKYWDataset_weights')
PRIMARY_MODEL_NAME = 'SFGA-YOLO26M'
HAZMAT_PRIMARY_MODEL_NAME = 'LCA-YOLO26N'

MODEL_TASKS = {
    'collision': '货车追尾现场',
    'hazmat': '油罐车泄露现场',
}

MODEL_DISPLAY_NAMES = {
    PRIMARY_MODEL_NAME: 'SFGA-YOLO26M',
    'yolo26M': 'YOLO26M',
    'yolo11M': 'YOLO11M',
    HAZMAT_PRIMARY_MODEL_NAME: 'LCA-YOLO26N',
    'yolo26N': 'YOLO26N',
    'yolo11N': 'YOLO11N',
}

MODEL_TASK_TYPES = {
    PRIMARY_MODEL_NAME: 'collision',
    'yolo26M': 'collision',
    'yolo11M': 'collision',
    HAZMAT_PRIMARY_MODEL_NAME: 'hazmat',
    'yolo26N': 'hazmat',
    'yolo11N': 'hazmat',
}

MODEL_PERFORMANCE = {
    PRIMARY_MODEL_NAME: {
        'model_name': 'SFGA-YOLO26M',
        'map50': 0.9168,
        'map50_95': 0.5922,
        'recall': 0.8675,
        'precision': 0.8944,
        'test_set': 'LKYWDetection Test set',
    },
    'yolo26M': {
        'model_name': 'YOLO26M',
        'map50': 0.9044,
        'map50_95': 0.5651,
        'recall': 0.8415,
        'precision': 0.8552,
        'test_set': 'LKYWDetection Test set',
    },
    'yolo11M': {
        'model_name': 'YOLO11M',
        'map50': 0.9052,
        'map50_95': 0.5813,
        'recall': 0.8433,
        'precision': 0.8745,
        'test_set': 'LKYWDetection Test set',
    },
    HAZMAT_PRIMARY_MODEL_NAME: {
        'model_name': 'LCA-YOLO26N',
        'map50': 0.87568,
        'map50_95': 0.55490,
        'recall': 0.83146,
        'precision': 0.88100,
        'test_set': 'TankTruckLeak Test set',
    },
    'yolo26N': {
        'model_name': 'YOLO26N',
        'map50': 0.85038,
        'map50_95': 0.50797,
        'recall': 0.79832,
        'precision': 0.88877,
        'test_set': 'TankTruckLeak Test set',
    },
    'yolo11N': {
        'model_name': 'YOLO11N',
        'map50': 0.83507,
        'map50_95': 0.53197,
        'recall': 0.76058,
        'precision': 0.87308,
        'test_set': 'TankTruckLeak Test set',
    },
}

ALLOWED_MODEL_NAMES = set(MODEL_DISPLAY_NAMES)
COMPOSITE_MODEL_NAMES = [PRIMARY_MODEL_NAME, HAZMAT_PRIMARY_MODEL_NAME]

MODEL_WEIGHT_FOLDERS = {
    PRIMARY_MODEL_NAME: 'yolo26m_BestPt_1',
    'yolo26M': PRIMARY_MODEL_NAME,
    'yolo11M': 'yolo11m_BestPt_0',
    HAZMAT_PRIMARY_MODEL_NAME: HAZMAT_PRIMARY_MODEL_NAME,
    'yolo26N': 'yolo26n_BestPt_0',
    'yolo11N': 'yolo11n_BestPt_0',
}


def get_model_display_name(model_name):
    if model_name in MODEL_DISPLAY_NAMES:
        return MODEL_DISPLAY_NAMES[model_name]
    return model_name.split('_')[0]


def get_model_sort_key(model_name):
    task_rank = 0 if MODEL_TASK_TYPES.get(model_name) == 'collision' else 10
    if model_name in (PRIMARY_MODEL_NAME, HAZMAT_PRIMARY_MODEL_NAME):
        return (task_rank, 0, model_name.lower())
    if model_name.lower().startswith('yolo26'):
        return (task_rank, 1, model_name.lower())
    if model_name.lower().startswith('yolo11'):
        return (task_rank, 2, model_name.lower())
    return (task_rank, 3, model_name.lower())


def get_available_models():
    models_config = {}
    model_names = sorted(ALLOWED_MODEL_NAMES, key=get_model_sort_key)
    for model_name in model_names:
        weight_folder_name = MODEL_WEIGHT_FOLDERS.get(model_name, model_name)
        relative_weight_file = WEIGHTS_DIR / weight_folder_name / 'best.pt'
        weight_file = (BASE_DIR / relative_weight_file).resolve()
        if weight_file.exists():
            models_config[model_name] = relative_weight_file.as_posix()
    return models_config

MODEL_PATHS = get_available_models()
# Ensure at least one default model key exists for frontend compatibility
if not MODEL_PATHS:
    MODEL_PATHS = {'default': '../../runs/detect/lkyw_fire_detection/weights/best.pt'}

for name in MODEL_PATHS:
    MODELS[name] = None

# 类别颜色映射 (BGR格式，OpenCV使用BGR而非RGB)
CLASS_COLORS = {
    'car_fire': (53, 57, 229),       # 红色 - 普通车辆火灾
    'lkyw_fire': (91, 24, 194),      # 紫红色 - 两客一危火灾
    'car_nofire': (53, 216, 253),    # 金黄色 - 普通车辆无火
    'lkyw_nofire': (0, 140, 251),    # 橙色 - 两客一危无火
    'car_normal': (53, 216, 253),
    'lkyw_normal': (0, 140, 251),
    'normal': (233, 165, 14),         # 蓝色 - 油罐车正常/未泄露
    'accident': (46, 67, 168),        # 红褐色 - 油罐车泄露事故
    'hazmat_leak': (233, 165, 14),    # 蓝色 - 油罐车泄露相关
    'tank_leak': (46, 67, 168),       # 红褐色 - 油罐车泄露相关
}


def get_class_color(class_name):
    """Return an OpenCV BGR color for a detection class."""
    raw_name = str(class_name or "").strip()
    normalized_name = raw_name.lower().replace("-", "_").replace(" ", "_")

    if raw_name in CLASS_COLORS:
        return CLASS_COLORS[raw_name]
    if normalized_name in CLASS_COLORS:
        return CLASS_COLORS[normalized_name]

    leak_markers = ("leak", "hazmat", "tank", "泄露", "泄漏", "危化")
    nofire_markers = ("nofire", "no_fire", "non_fire", "normal", "无火", "未起火", "正常")
    fire_markers = ("fire", "起火", "火灾", "着火")

    if any(marker in normalized_name for marker in leak_markers):
        return (178, 145, 8)
    if any(marker in normalized_name for marker in nofire_markers):
        return (53, 216, 253)
    if any(marker in normalized_name for marker in fire_markers):
        return (53, 57, 229)

    return (160, 160, 160)


def is_fire_class(class_name):
    normalized_name = str(class_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    leak_markers = ("leak", "hazmat", "tank", "泄露", "泄漏", "危化")
    nofire_markers = ("nofire", "no_fire", "non_fire", "normal", "无火", "未起火", "正常")
    fire_markers = ("fire", "起火", "火灾", "着火")

    if any(marker in normalized_name for marker in leak_markers):
        return False
    if any(marker in normalized_name for marker in nofire_markers):
        return False
    return any(marker in normalized_name for marker in fire_markers)


# RTSP检测器管理
rtsp_detectors = {}
command_worker_started = False
command_worker_lock = threading.Lock()


def publish_detection_event(event_type, subject, payload, severity='info'):
    EVENT_PUBLISHER.publish(
        event_type,
        subject=subject,
        severity=severity,
        payload=payload,
    )


def publish_command_status(command, status, message='', result=None, error_message=''):
    command_id = command.get('commandId', '')
    severity = 'error' if status == 'failed' else 'info'
    EVENT_PUBLISHER.publish(
        f'command.{status}',
        subject=command_id,
        severity=severity,
        correlation_id=command_id,
        payload=build_command_status_payload(
            command,
            status,
            message=message,
            result=result or {},
            error_message=error_message,
        ),
    )


def should_publish_detection_event(event_key):
    now = time.time()
    last_at = last_detection_event_at.get(event_key, 0)
    if now - last_at < DETECTION_EVENT_COOLDOWN_SECONDS:
        return False
    last_detection_event_at[event_key] = now
    return True


def on_rtsp_detection_event(detection, stats):
    stream_id = detection.get('camera_id') or stats.get('camera_id') or 'rtsp_cam_01'
    detections = detection.get('detections') or []
    fire_detections = [
        item for item in detections
        if is_fire_class(item.get('class', ''))
    ]

    if not fire_detections:
        return

    payload = {
        'streamId': stream_id,
        'rtspUrl': stats.get('rtsp_url'),
        'detection': detection,
        'stats': stats,
        'fireDetections': fire_detections,
    }

    if should_publish_detection_event(f'{stream_id}:fire'):
        publish_detection_event('detection.fire.detected', stream_id, payload, severity='warn')

    if should_publish_detection_event(f'{stream_id}:accident'):
        publish_detection_event('detection.accident.confirmed', stream_id, payload, severity='critical')


def resolve_path(path_value):
    path_obj = Path(path_value)
    if path_obj.is_absolute():
        return path_obj
    return (BASE_DIR / path_obj).resolve()


def get_model_status():
    items = []
    for name, raw_path in MODEL_PATHS.items():
        resolved_path = resolve_path(raw_path)
        items.append({
            'name': name,
            'configured_path': raw_path,
            'resolved_path': str(resolved_path),
            'exists': resolved_path.exists(),
            'loaded': MODELS.get(name) is not None,
        })
    return items


def load_rtsp_stream_config():
    config_path = BASE_DIR / 'rtsp_config.json'
    if not config_path.exists():
        return []

    with open(config_path, 'r', encoding='utf-8') as file_obj:
        config = json.load(file_obj)

    return config.get('rtsp_streams', [])


def get_default_stream(stream_id=None):
    streams = load_rtsp_stream_config()
    if stream_id:
        for item in streams:
            if item.get('id') == stream_id:
                return item

    for item in streams:
        if item.get('enabled', True):
            return item

    return streams[0] if streams else None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def build_safe_upload_name(filename):
    original_path = Path(filename or '')
    suffix = original_path.suffix.lower()
    normalized_stem = secure_filename(original_path.stem)

    if not normalized_stem:
        normalized_stem = 'upload'

    if suffix.lstrip('.') not in ALLOWED_EXTENSIONS:
        suffix = ''

    return f"{normalized_stem}{suffix}"

def load_model(model_name):
    """Lazy load model when needed"""
    if model_name not in MODELS:
        available_models = list(MODEL_PATHS.keys())
        model_name = available_models[0] if available_models else None
        
    if model_name is None:
        raise ValueError("No models available")

    if MODELS[model_name] is None:
        model_path = resolve_path(MODEL_PATHS[model_name])
        if model_path.exists():
            print(f"Loading model: {model_name} from {model_path}")
            try:
                # 尝试使用标准方式加载
                MODELS[model_name] = YOLO(str(model_path))
            except Exception as e:
                print(f"Standard loading failed: {e}")
                print("Trying alternative loading method...")
                # 使用替代方法：直接修改 torch.load 的默认行为
                import torch.serialization
                original_load = torch.load
                def patched_load(*args, **kwargs):
                    kwargs['weights_only'] = False
                    return original_load(*args, **kwargs)
                torch.load = patched_load
                MODELS[model_name] = YOLO(str(model_path))
                torch.load = original_load
            print(f"✓ Model loaded successfully: {model_name}")
        else:
            raise FileNotFoundError(f"Model file not found: {model_path}")
    return MODELS[model_name]

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get available models"""
    available_models = []
    for name, raw_path in MODEL_PATHS.items():
        model_path = resolve_path(raw_path)
        if model_path.exists():
            available_models.append({
                'name': name,
                'display_name': get_model_display_name(name),
                'path': raw_path,
                'size': model_path.stat().st_size / (1024 * 1024),  # Size in MB
                'is_primary': name in (PRIMARY_MODEL_NAME, HAZMAT_PRIMARY_MODEL_NAME),
                'task_type': MODEL_TASK_TYPES.get(name, 'collision'),
                'task_label': MODEL_TASKS.get(MODEL_TASK_TYPES.get(name, 'collision'), '货车追尾现场'),
                'performance': MODEL_PERFORMANCE.get(name),
            })
    return jsonify({'models': available_models})

def run_image_detection_for_model(model_name, filepath, img, conf_threshold, iou_threshold):
    import time

    model = load_model(model_name)
    start_time = time.time()
    results = model.predict(
        source=filepath,
        conf=conf_threshold,
        iou=iou_threshold,
        save=False
    )
    inference_time = time.time() - start_time

    result = results[0]
    detections = []
    task_type = MODEL_TASK_TYPES.get(model_name, 'collision')
    task_label = MODEL_TASKS.get(task_type, '货车追尾现场')
    model_display_name = get_model_display_name(model_name)

    for box in result.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        cls = int(box.cls[0])
        class_name = result.names[cls]
        detections.append({
            'class': class_name,
            'confidence': conf,
            'bbox': [x1, y1, x2, y2],
            'model': model_name,
            'model_display_name': model_display_name,
            'task_type': task_type,
            'task_label': task_label
        })

    return {
        'model': model_name,
        'model_display_name': model_display_name,
        'task_type': task_type,
        'task_label': task_label,
        'detections': detections,
        'count': len(detections),
        'inference_time': round(inference_time, 3)
    }


def run_frame_detection_for_model(model_name, frame, conf_threshold, iou_threshold):
    import time

    model = load_model(model_name)
    start_time = time.time()
    results = model.predict(
        source=frame,
        conf=conf_threshold,
        iou=iou_threshold,
        save=False,
        verbose=False
    )
    inference_time = time.time() - start_time

    result = results[0]
    detections = []
    task_type = MODEL_TASK_TYPES.get(model_name, 'collision')
    task_label = MODEL_TASKS.get(task_type, '货车追尾现场')
    model_display_name = get_model_display_name(model_name)

    for box in result.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        cls = int(box.cls[0])
        class_name = result.names[cls]

        detections.append({
            'class': class_name,
            'confidence': conf,
            'bbox': [x1, y1, x2, y2],
            'model': model_name,
            'model_display_name': model_display_name,
            'task_type': task_type,
            'task_label': task_label
        })

    return {
        'model': model_name,
        'model_display_name': model_display_name,
        'task_type': task_type,
        'task_label': task_label,
        'detections': detections,
        'count': len(detections),
        'inference_time': round(inference_time, 3)
    }


def bbox_area(bbox):
    x1, y1, x2, y2 = bbox
    return max(0, x2 - x1) * max(0, y2 - y1)


def bbox_overlap_score(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_w = max(0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0, min(ay2, by2) - max(ay1, by1))
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0

    area_a = bbox_area(box_a)
    area_b = bbox_area(box_b)
    if area_a <= 0 or area_b <= 0:
        return 0.0

    union = area_a + area_b - inter_area
    iou = inter_area / union if union > 0 else 0.0
    cover = inter_area / min(area_a, area_b)
    return max(iou, cover)


def detection_label_entry(det):
    return {
        'class': det.get('class', ''),
        'confidence': float(det.get('confidence', 0.0) or 0.0),
        'model': det.get('model', ''),
        'model_display_name': det.get('model_display_name', ''),
        'task_type': det.get('task_type', ''),
        'task_label': det.get('task_label', ''),
    }


def ensure_merged_labels(det):
    if 'merged_labels' not in det or not det['merged_labels']:
        det['merged_labels'] = [detection_label_entry(det)]
    return det['merged_labels']


def add_merged_labels(target, source):
    target_labels = ensure_merged_labels(target)
    source_labels = source.get('merged_labels') or [detection_label_entry(source)]
    seen = {(item.get('class'), item.get('model')) for item in target_labels}

    for item in source_labels:
        key = (item.get('class'), item.get('model'))
        if key not in seen:
            target_labels.append(item)
            seen.add(key)


def merge_detections(detections, threshold=0.8, same_class_only=True, prefer='confidence'):
    if not detections:
        return []

    def sort_key(det):
        area = bbox_area(det['bbox'])
        confidence = float(det.get('confidence', 0.0) or 0.0)
        return (-confidence, -area) if prefer == 'confidence' else (-area, -confidence)

    ordered = sorted((dict(det) for det in detections), key=sort_key)
    kept = []

    for det in ordered:
        matched = False
        for existing in kept:
            if same_class_only and det.get('class') != existing.get('class'):
                continue
            if bbox_overlap_score(det['bbox'], existing['bbox']) >= threshold:
                matched = True
                if not same_class_only:
                    add_merged_labels(existing, det)
                break
        if not matched:
            kept.append(det)

    return kept


def draw_detections_on_image(image, detections):
    for det in detections:
        x1, y1, x2, y2 = map(int, det['bbox'])
        class_name = det.get('class', '')
        color = get_class_color(class_name)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

        labels = det.get('merged_labels') or [detection_label_entry(det)]
        label_y = y1 - 10
        if label_y - (len(labels) - 1) * 18 < 12:
            label_y = y1 + 18

        for index, item in enumerate(labels):
            label_class = item.get('class', '')
            conf = float(item.get('confidence', 0.0) or 0.0)
            label = f"{label_class} {conf:.2f}"
            y = label_y + index * 18
            cv2.putText(image, label, (x1, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, get_class_color(label_class), 2)


@app.route('/api/detect/image', methods=['POST'])
def detect_image():
    """Detect objects in uploaded image."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        available_models = list(MODEL_PATHS.keys())
        default_model = available_models[0] if available_models else 'yolo11n'
        detection_mode = request.form.get('detection_mode', 'single')
        model_name = request.form.get('model', default_model)

        if model_name not in MODEL_PATHS:
            model_name = default_model
        conf_threshold = float(request.form.get('conf', 0.25))
        iou_threshold = float(request.form.get('iou', 0.45))

        filename = build_safe_upload_name(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        image_hash = calculate_sha256(filepath)

        img = cv2.imread(filepath)
        if img is None:
            return jsonify({'error': 'Failed to read uploaded image'}), 400

        selected_models = [model_name]
        if detection_mode == 'composite':
            selected_models = [name for name in COMPOSITE_MODEL_NAMES if name in MODEL_PATHS]
            if not selected_models:
                selected_models = [model_name]

        model_results = []
        all_detections = []
        total_inference_time = 0.0
        for current_model_name in selected_models:
            model_result = run_image_detection_for_model(
                current_model_name,
                filepath,
                img,
                conf_threshold,
                iou_threshold
            )
            model_results.append(model_result)
            all_detections.extend(model_result['detections'])
            total_inference_time += model_result['inference_time']

        if detection_mode == 'composite':
            final_detections = merge_detections(all_detections, threshold=0.7, same_class_only=False, prefer='area')
        else:
            final_detections = merge_detections(all_detections, threshold=0.8, same_class_only=True, prefer='confidence')
        draw_detections_on_image(img, final_detections)

        result_filename = f"result_{unique_filename}"
        result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        cv2.imwrite(result_path, img)

        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        history_model_name = model_name if detection_mode != 'composite' else '+'.join(selected_models)
        try:
            save_detection(
                timestamp=datetime.now().isoformat(),
                model_name=history_model_name,
                original_filename=filename,
                saved_filename=unique_filename,
                result_filename=result_filename,
                detection_count=len(final_detections),
                detections_json=json.dumps(final_detections),
                inference_time_s=round(total_inference_time, 3),
                conf_threshold=conf_threshold,
                iou_threshold=iou_threshold,
                source_type='image',
                image_hash=image_hash
            )
        except Exception as e:
            print(f"Failed to save detection history: {e}")

        return jsonify({
            'success': True,
            'detection_mode': detection_mode,
            'models': model_results,
            'detections': final_detections,
            'count': len(final_detections),
            'image': f"data:image/jpeg;base64,{img_base64}",
            'result_file': result_filename,
            'inference_time': round(total_inference_time, 3),
            'model': history_model_name
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/detect/batch', methods=['POST'])
def detect_batch():
    """Detect objects in multiple uploaded images"""
    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files provided'}), 400

        available_models = list(MODEL_PATHS.keys())
        default_model = available_models[0] if available_models else 'yolo11n'
        model_name = request.form.get('model', default_model)
        if model_name not in MODEL_PATHS:
            model_name = default_model
        conf_threshold = float(request.form.get('conf', 0.25))
        iou_threshold = float(request.form.get('iou', 0.45))

        model = load_model(model_name)
        import time
        total_start = time.time()
        results_list = []

        for file in files:
            if file.filename == '' or not allowed_file(file.filename):
                results_list.append({
                    'filename': file.filename or 'unknown',
                    'success': False,
                    'error': 'Invalid file'
                })
                continue

            try:
                filename = build_safe_upload_name(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                unique_filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                image_hash = calculate_sha256(filepath)

                file_start = time.time()
                results = model.predict(
                    source=filepath, conf=conf_threshold,
                    iou=iou_threshold, save=False
                )
                file_inference = time.time() - file_start

                result = results[0]
                img = cv2.imread(filepath)
                detections = []
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    class_name = result.names[cls]
                    detections.append({
                        'class': class_name, 'confidence': conf,
                        'bbox': [x1, y1, x2, y2]
                    })

                detections = merge_detections(detections, threshold=0.8, same_class_only=True, prefer='confidence')
                draw_detections_on_image(img, detections)

                result_filename = f"result_{unique_filename}"
                result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
                cv2.imwrite(result_path, img)

                _, buffer = cv2.imencode('.jpg', img)
                img_base64 = base64.b64encode(buffer).decode('utf-8')

                try:
                    save_detection(
                        timestamp=datetime.now().isoformat(),
                        model_name=model_name,
                        original_filename=filename,
                        saved_filename=unique_filename,
                        result_filename=result_filename,
                        detection_count=len(detections),
                        detections_json=json.dumps(detections),
                        inference_time_s=round(file_inference, 3),
                        conf_threshold=conf_threshold,
                        iou_threshold=iou_threshold,
                        source_type='batch',
                        image_hash=image_hash
                    )
                except Exception as e:
                    print(f"Failed to save batch detection history: {e}")

                results_list.append({
                    'filename': file.filename,
                    'success': True,
                    'detections': detections,
                    'count': len(detections),
                    'image': f"data:image/jpeg;base64,{img_base64}",
                    'result_file': result_filename,
                    'inference_time': round(file_inference, 3)
                })
            except Exception as file_err:
                results_list.append({
                    'filename': file.filename or 'unknown',
                    'success': False,
                    'error': str(file_err)
                })

        total_inference = time.time() - total_start
        return jsonify({
            'success': True,
            'total_files': len(files),
            'results': results_list,
            'total_inference_time': round(total_inference, 3)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/detect/video', methods=['POST'])
def detect_video():
    """Detect objects in uploaded video by sampling frames"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get parameters
        available_models = list(MODEL_PATHS.keys())
        default_model = available_models[0] if available_models else 'yolo11n'
        model_name = request.form.get('model', default_model)
        detection_mode = request.form.get('detection_mode', 'single')
        
        if model_name not in MODEL_PATHS:
            model_name = default_model
        selected_models = [model_name]
        if detection_mode == 'composite':
            selected_models = [name for name in COMPOSITE_MODEL_NAMES if name in MODEL_PATHS]
            if not selected_models:
                selected_models = [model_name]
        conf_threshold = float(request.form.get('conf', 0.25))
        iou_threshold = float(request.form.get('iou', 0.45))
        frame_interval = int(request.form.get('interval', 30))
        frame_interval = max(frame_interval, 1)
        start_time_s = max(float(request.form.get('start_time', 0) or 0), 0)
        
        # Save uploaded file
        filename = build_safe_upload_name(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        video_hash = calculate_sha256(filepath)
        
        # 朴素抽帧检测：从第 0 帧开始，按固定帧间隔逐帧取样。
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            raise ValueError("Unable to open video file")

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        if fps <= 0:
            fps = 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        start_frame = int(start_time_s * fps)
        if total_frames > 0:
            start_frame = min(start_frame, max(total_frames - 1, 0))
        if start_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        # 用于计算平均处理时间
        import time
        total_inference_time = 0
        
        frame_count = start_frame
        sampled_frames = []
        history_detections = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            should_detect = (frame_count - start_frame) % frame_interval == 0
            
            if should_detect:
                frame_detections = []
                model_results = []
                for current_model_name in selected_models:
                    model_result = run_frame_detection_for_model(
                        current_model_name,
                        frame,
                        conf_threshold,
                        iou_threshold
                    )
                    total_inference_time += model_result['inference_time']
                    frame_detections.extend(model_result['detections'])
                    model_results.append(model_result)

                if detection_mode == 'composite':
                    frame_detections = merge_detections(frame_detections, threshold=0.7, same_class_only=False, prefer='area')
                else:
                    frame_detections = merge_detections(frame_detections, threshold=0.8, same_class_only=True, prefer='confidence')
                draw_detections_on_image(frame, frame_detections)

                # 保存检测结果帧
                frame_filename = f"frame_{timestamp}_{frame_count}.jpg"
                frame_path = os.path.join(app.config['RESULT_FOLDER'], frame_filename)
                cv2.imwrite(frame_path, frame)
                
                # Convert to base64
                _, buffer = cv2.imencode('.jpg', frame)
                img_base64 = base64.b64encode(buffer).decode('utf-8')
                
                frame_time_s = round(frame_count / fps, 3)
                for detection in frame_detections:
                    history_item = dict(detection)
                    history_item['frame_number'] = frame_count
                    history_item['time_s'] = frame_time_s
                    history_item['frame_filename'] = frame_filename
                    history_detections.append(history_item)

                sampled_frames.append({
                    'frame_number': frame_count,
                    'time': f"{frame_count / fps:.2f}s",
                    'time_s': frame_time_s,
                    'detections': frame_detections,
                    'detection_count': len(frame_detections),
                    'models': model_results,
                    'image': f"data:image/jpeg;base64,{img_base64}",
                    'filename': frame_filename
                })
            
            frame_count += 1
        
        cap.release()
        
        avg_frame_time = 0
        if len(sampled_frames) > 0:
            avg_frame_time = round(total_inference_time / len(sampled_frames), 3)

        history_model_name = model_name if detection_mode != 'composite' else '+'.join(selected_models)
        representative_frame = sampled_frames[0]['filename'] if sampled_frames else ''
        try:
            save_detection(
                timestamp=datetime.now().isoformat(),
                model_name=history_model_name,
                original_filename=filename,
                saved_filename=unique_filename,
                result_filename=representative_frame,
                detection_count=len(history_detections),
                detections_json=json.dumps(history_detections),
                inference_time_s=round(total_inference_time, 3),
                conf_threshold=conf_threshold,
                iou_threshold=iou_threshold,
                source_type='video',
                image_hash=video_hash
            )
        except Exception as e:
            print(f"Failed to save video detection history: {e}")
        
        return jsonify({
            'success': True,
            'total_frames': total_frames,
            'sampled_frames': len(sampled_frames),
            'avg_frame_time': avg_frame_time,
            'fps': round(fps, 3),
            'model': model_name if detection_mode != 'composite' else '+'.join(selected_models),
            'detection_mode': detection_mode,
            'interval': frame_interval,
            'start_time': round(start_time_s, 3),
            'start_frame': start_frame,
            'video_width': video_width,
            'video_height': video_height,
            'frames': sampled_frames
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/detect/webcam', methods=['POST'])
def detect_webcam():
    """Process webcam frame."""
    try:
        data = request.get_json()
        image_data = data.get('image')

        available_models = list(MODEL_PATHS.keys())
        default_model = available_models[0] if available_models else 'yolo11n'
        model_name = data.get('model', default_model)
        detection_mode = data.get('detection_mode', 'single')

        if model_name not in MODEL_PATHS:
            model_name = default_model
        selected_models = [model_name]
        if detection_mode == 'composite':
            selected_models = [name for name in COMPOSITE_MODEL_NAMES if name in MODEL_PATHS]
            if not selected_models:
                selected_models = [model_name]

        conf_threshold = float(data.get('conf', 0.25))
        iou_threshold = float(data.get('iou', 0.45))

        img_bytes = base64.b64decode(image_data.split(',')[1])
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        detections = []
        model_results = []
        total_inference_time = 0.0
        for current_model_name in selected_models:
            model_result = run_frame_detection_for_model(
                current_model_name,
                img,
                conf_threshold,
                iou_threshold
            )
            detections.extend(model_result['detections'])
            model_results.append(model_result)
            total_inference_time += model_result['inference_time']

        if detection_mode == 'composite':
            detections = merge_detections(detections, threshold=0.7, same_class_only=False, prefer='area')
        else:
            detections = merge_detections(detections, threshold=0.8, same_class_only=True, prefer='confidence')
        draw_detections_on_image(img, detections)

        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            'success': True,
            'detection_mode': detection_mode,
            'models': model_results,
            'model': model_name if detection_mode != 'composite' else '+'.join(selected_models),
            'detections': detections,
            'count': len(detections),
            'inference_time': round(total_inference_time, 3),
            'image': f"data:image/jpeg;base64,{img_base64}"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/results/<filename>')
def get_result(filename):
    """Serve result files"""
    return send_from_directory(app.config['RESULT_FOLDER'], filename)


@app.route('/api/uploads/<filename>')
def get_upload(filename):
    """Serve original uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    model_status = get_model_status()
    return jsonify({
        'status': 'ok',
        'message': 'YOLO Web API is running',
        'service': 'real-time-detection',
        'backend_base': request.host_url.rstrip('/'),
        'models': model_status,
        'model_ready': any(item['exists'] for item in model_status),
        'active_streams': len(rtsp_detectors)
    })


@app.route('/api/system/info', methods=['GET'])
def system_info():
    """Real system metrics for telemetry dashboard"""
    import subprocess
    info = {
        'gpu_name': 'N/A',
        'cuda_version': 'N/A',
        'vram_total_gb': None,
        'vram_used_gb': None,
        'vram_free_gb': None,
        'gpu_temp': None,
        'gpu_util': None,
        'gpu_error': '',
        'model_loaded': False,
        'model_name': '',
        'total_detections_today': 0,
        'uptime_seconds': 0,
        'python_version': '',
    }
    try:
        # GPU info via nvidia-smi. This provides temperature/utilization that torch cannot expose.
        result = subprocess.run([
            'nvidia-smi', '--query-gpu=name,temperature.gpu,utilization.gpu,memory.total,memory.used,memory.free',
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            parts = [x.strip() for x in result.stdout.strip().split(',')]
            if len(parts) >= 6:
                info['gpu_name'] = parts[0]
                info['gpu_temp'] = int(parts[1])
                info['gpu_util'] = int(parts[2])
                info['vram_total_gb'] = round(int(parts[3]) / 1024, 1)
                info['vram_used_gb'] = round(int(parts[4]) / 1024, 1)
                info['vram_free_gb'] = round(int(parts[5]) / 1024, 1)
        else:
            info['gpu_error'] = (result.stderr or result.stdout or 'nvidia-smi unavailable').strip()
    except Exception as exc:
        info['gpu_error'] = str(exc)

    if info['gpu_name'] == 'N/A':
        try:
            if torch.cuda.is_available():
                device_index = torch.cuda.current_device()
                props = torch.cuda.get_device_properties(device_index)
                total_gb = props.total_memory / (1024 ** 3)
                reserved_gb = torch.cuda.memory_reserved(device_index) / (1024 ** 3)
                allocated_gb = torch.cuda.memory_allocated(device_index) / (1024 ** 3)
                used_gb = max(reserved_gb, allocated_gb)
                info['gpu_name'] = torch.cuda.get_device_name(device_index)
                info['vram_total_gb'] = round(total_gb, 1)
                info['vram_used_gb'] = round(used_gb, 1)
                info['vram_free_gb'] = round(max(total_gb - used_gb, 0), 1)
        except Exception as exc:
            if not info['gpu_error']:
                info['gpu_error'] = str(exc)

    try:
        info['cuda_version'] = torch.version.cuda or 'N/A'
        info['python_version'] = sys.version.split()[0]
    except Exception:
        pass

    try:
        # Check loaded models
        loaded = [name for name, model in MODELS.items() if model is not None]
        info['model_loaded'] = len(loaded) > 0
        info['model_name'] = get_model_display_name(loaded[0]) if loaded else ''
    except Exception:
        pass

    try:
        from database import get_db
        conn = get_db()
        today = conn.execute(
            "SELECT COUNT(*) FROM detections WHERE date(timestamp) = date('now')"
        ).fetchone()[0]
        conn.close()
        info['total_detections_today'] = today
    except Exception:
        pass

    return jsonify({'success': True, 'info': info})
@app.route('/api/rtsp/status', methods=['GET'])
def get_rtsp_status():
    """Get active RTSP stream status for total-system cards and integrations."""
    model_status = get_model_status()
    streams = []
    for stream_id, detector in rtsp_detectors.items():
        stats = detector.get_stats()
        streams.append({
            'camera_id': stream_id,
            'rtsp_url': stats.get('rtsp_url'),
            'running': bool(stats.get('is_running')),
            'frame_count': stats.get('frame_count', 0),
            'fire_count': stats.get('fire_count', 0),
            'last_detection_time': stats.get('last_detection_time'),
        })

    return jsonify({
        'success': True,
        'service': 'real-time-detection',
        'model_ready': any(item['exists'] for item in model_status),
        'active_streams': len(streams),
        'streams': streams,
    })


def run_rtsp_frame_detection(frame, model_name, detection_mode, conf_threshold, iou_threshold):
    available_models = list(MODEL_PATHS.keys())
    default_model = available_models[0] if available_models else 'SFGA-YOLO26M'
    if model_name not in MODEL_PATHS:
        model_name = default_model

    selected_models = [model_name]
    if detection_mode == 'composite':
        selected_models = [name for name in COMPOSITE_MODEL_NAMES if name in MODEL_PATHS]
        if not selected_models:
            selected_models = [model_name]

    all_detections = []
    for current_model_name in selected_models:
        model_result = run_frame_detection_for_model(
            current_model_name,
            frame,
            conf_threshold,
            iou_threshold
        )
        all_detections.extend(model_result['detections'])

    if detection_mode == 'composite':
        final_detections = merge_detections(all_detections, threshold=0.7, same_class_only=False, prefer='area')
    else:
        final_detections = merge_detections(all_detections, threshold=0.8, same_class_only=True, prefer='confidence')

    annotated_frame = frame.copy()
    draw_detections_on_image(annotated_frame, final_detections)

    return annotated_frame, final_detections


def start_rtsp_detector(data):
    """Start or update an RTSP detector."""
    stream_id = data.get('stream_id') or data.get('streamId') or 'rtsp_cam_01'
    rtsp_url = data.get('rtsp_url') or data.get('rtspUrl')
    camera_name = data.get('camera_name') or data.get('cameraName') or 'RTSP Camera'
    model_name = data.get('model') or list(MODEL_PATHS.keys())[0]
    detection_mode = data.get('detection_mode') or 'single'
    task_type = data.get('task_type') or 'collision'
    conf_threshold = float(data.get('conf') if data.get('conf') is not None else 0.25)
    iou_threshold = float(data.get('iou') if data.get('iou') is not None else 0.45)

    if not rtsp_url:
        return {'error': 'RTSP URL is required'}, 400

    if stream_id in rtsp_detectors:
        detector = rtsp_detectors[stream_id]
        detector.update_settings(
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            model_name=model_name,
            detection_mode=detection_mode,
            task_type=task_type
        )
        return {'success': True, 'message': 'Stream settings updated', 'stream_id': stream_id}, 200

    raw_model_path = MODEL_PATHS.get(model_name)
    model_path = str(resolve_path(raw_model_path)) if raw_model_path else None

    detector = RTSPDetector(
        model_path=model_path,
        rtsp_url=rtsp_url,
        camera_id=stream_id,
        on_detection=on_rtsp_detection_event,
        detect_frame_fn=run_rtsp_frame_detection,
        conf_threshold=conf_threshold,
        iou_threshold=iou_threshold,
        model_name=model_name,
        detection_mode=detection_mode,
        task_type=task_type
    )
    detector.connect()
    detector.start()
    rtsp_detectors[stream_id] = detector
    publish_detection_event(
        'detection.stream.started',
        stream_id,
        {
            'streamId': stream_id,
            'rtspUrl': rtsp_url,
            'cameraName': camera_name,
            'model': model_name,
            'startedAt': datetime.now().isoformat(timespec='seconds'),
        },
    )

    return {'success': True, 'stream_id': stream_id}, 200


def stop_rtsp_detector(stream_id):
    """Stop an RTSP detector from a plain command/API payload."""
    if stream_id in rtsp_detectors:
        stats = rtsp_detectors[stream_id].get_stats()
        rtsp_detectors[stream_id].stop()
        del rtsp_detectors[stream_id]
        publish_detection_event(
            'detection.stream.stopped',
            stream_id,
            {
                'streamId': stream_id,
                'stats': stats,
                'stoppedAt': datetime.now().isoformat(timespec='seconds'),
            },
        )
        return {'success': True, 'stream_id': stream_id}, 200
    return {'error': 'Not found', 'stream_id': stream_id}, 404


def execute_detection_command(command):
    command_type = command.get('type', '')
    payload = command.get('payload') or {}
    try:
        publish_command_status(command, 'accepted', message='detection command accepted')

        if command_type == 'detection.rtsp.start':
            result, status_code = start_rtsp_detector(payload)
        elif command_type == 'detection.rtsp.stop':
            stream_id = payload.get('streamId') or payload.get('stream_id') or command.get('subject') or 'rtsp_cam_01'
            result, status_code = stop_rtsp_detector(stream_id)
        else:
            publish_command_status(
                command,
                'failed',
                message='unsupported detection command',
                error_message=f'unsupported_command:{command_type}',
            )
            return

        if status_code >= 400:
            publish_command_status(
                command,
                'failed',
                message='detection command failed',
                result=result,
                error_message=result.get('error', f'http_status:{status_code}'),
            )
            return

        publish_command_status(
            command,
            'completed',
            message='detection command completed',
            result=result,
        )
    except Exception as exc:
        publish_command_status(
            command,
            'failed',
            message='detection command failed',
            error_message=str(exc),
        )


def command_task():
    while True:
        commands = COMMAND_CLIENT.poll(count=10)
        for command in commands:
            execute_detection_command(command)
        if not commands:
            time.sleep(0.2)


def start_command_worker():
    global command_worker_started
    with command_worker_lock:
        if command_worker_started:
            return
        command_worker_started = True
        thread = threading.Thread(target=command_task, daemon=True)
        thread.start()


@app.before_request
def ensure_command_worker_started():
    if os.getenv('INTEGRATION_COMMANDS_START_ON_REQUEST', '1').lower() in {'1', 'true', 'yes', 'on'}:
        start_command_worker()


@app.route('/api/rtsp/start', methods=['POST'])
def start_rtsp_detection():
    """启动RTSP流检测"""
    try:
        data = request.get_json()
        result, status_code = start_rtsp_detector(data or {})
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rtsp/stop/<stream_id>', methods=['POST'])
def stop_rtsp_detection(stream_id):
    result, status_code = stop_rtsp_detector(stream_id)
    return jsonify(result), status_code

@app.route('/api/rtsp/video_feed/<stream_id>')
def rtsp_video_feed(stream_id):
    def generate():
        detector = rtsp_detectors.get(stream_id)
        if not detector: return
        last_version = -1
        while detector and detector.is_running:
            frame, version = detector.get_frame()
            if frame is not None and version != last_version:
                last_version = version
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            else:
                time.sleep(0.015)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/rtsp/detection/<stream_id>', methods=['GET'])
def get_rtsp_detection(stream_id):
    if stream_id in rtsp_detectors:
        detector = rtsp_detectors[stream_id]
        res = {
            'success': True,
            'detection': detector.get_detection_result(),
            'stats': detector.get_stats()
        }
        frame, _ = detector.get_frame()
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
            if ret:
                res['image'] = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
        return jsonify(res)
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    print("Starting YOLO Web API...")
    debug_enabled = os.getenv('FLASK_DEBUG', '1').lower() in {'1', 'true', 'yes', 'on'}
    if not debug_enabled or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_command_worker()
    app.run(host='0.0.0.0', port=5000, debug=debug_enabled)
