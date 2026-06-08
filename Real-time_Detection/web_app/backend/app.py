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
from ultralytics import YOLO
from datetime import datetime
import base64
import json
from pathlib import Path
import warnings
from rtsp_detector import RTSPDetector
from database import save_detection
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

WEIGHTS_DIR = Path('/home/zhangboyu/DL_study/lkywSystem/lkywSystemv0/Real-time_Detection/LKYWDataset_weights')

def get_available_models():
    models_config = {}
    if WEIGHTS_DIR.exists():
        for model_folder in WEIGHTS_DIR.iterdir():
            if model_folder.is_dir():
                weight_file = model_folder / 'best.pt'
                if weight_file.exists():
                    # Use folder name as model name (e.g., yolo11n_BestPt_42)
                    models_config[model_folder.name] = str(weight_file)
    return models_config

MODEL_PATHS = get_available_models()
# Ensure at least one default model key exists for frontend compatibility
if not MODEL_PATHS:
    MODEL_PATHS = {'default': str(BASE_DIR.parent.parent / 'runs/detect/lkyw_fire_detection/weights/best.pt')}

for name in MODEL_PATHS:
    MODELS[name] = None

# 类别颜色映射 (BGR格式，OpenCV使用BGR而非RGB)
CLASS_COLORS = {
    'car_fire': (0, 0, 255),        # 红色 - 普通车辆火灾（最危险）
    'car_normal': (0, 255, 0),      # 绿色 - 普通车辆正常
    'lkyw_fire': (0, 0, 139),       # 深红色 - 两客一危火灾（最高优先级）
    'lkyw_normal': (255, 144, 30)   # 橙色 - 两客一危正常
}

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
        if 'fire' in str(item.get('class', '')).lower() or '火' in str(item.get('class', ''))
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
                'path': str(model_path),
                'size': model_path.stat().st_size / (1024 * 1024)  # Size in MB
            })
    return jsonify({'models': available_models})

@app.route('/api/detect/image', methods=['POST'])
def detect_image():
    """Detect objects in uploaded image"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Get parameters
        available_models = list(MODEL_PATHS.keys())
        default_model = available_models[0] if available_models else 'yolo11n'
        model_name = request.form.get('model', default_model)
        
        if model_name not in MODEL_PATHS:
            model_name = default_model
        conf_threshold = float(request.form.get('conf', 0.25))
        iou_threshold = float(request.form.get('iou', 0.45))
        
        # Save uploaded file
        filename = build_safe_upload_name(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Load model and perform detection
        import time
        start_time = time.time()
        
        model = load_model(model_name)
        results = model.predict(
            source=filepath,
            conf=conf_threshold,
            iou=iou_threshold,
            save=False
        )
        
        inference_time = time.time() - start_time
        
        # Process results
        result = results[0]
        img = cv2.imread(filepath)
        
        # Draw bounding boxes
        detections = []
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_name = result.names[cls]
            
            # 根据类别选择颜色
            color = CLASS_COLORS.get(class_name, (0, 255, 0))  # 默认绿色
            
            # Draw on image
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            label = f"{class_name} {conf:.2f}"
            cv2.putText(img, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            detections.append({
                'class': class_name,
                'confidence': conf,
                'bbox': [x1, y1, x2, y2]
            })
        
        # Save result image
        result_filename = f"result_{unique_filename}"
        result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        cv2.imwrite(result_path, img)

        # Convert to base64 for response
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        # Save to detection history
        try:
            save_detection(
                timestamp=datetime.now().isoformat(),
                model_name=model_name,
                original_filename=filename,
                saved_filename=unique_filename,
                result_filename=result_filename,
                detection_count=len(detections),
                detections_json=json.dumps(detections),
                inference_time_s=round(inference_time, 3),
                conf_threshold=conf_threshold,
                iou_threshold=iou_threshold,
                source_type='image'
            )
        except Exception as e:
            print(f"Failed to save detection history: {e}")

        return jsonify({
            'success': True,
            'detections': detections,
            'count': len(detections),
            'image': f"data:image/jpeg;base64,{img_base64}",
            'result_file': result_filename,
            'inference_time': round(inference_time, 3)
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
                    color = CLASS_COLORS.get(class_name, (0, 255, 0))
                    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                    label = f"{class_name} {conf:.2f}"
                    cv2.putText(img, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    detections.append({
                        'class': class_name, 'confidence': conf,
                        'bbox': [x1, y1, x2, y2]
                    })

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
                        source_type='batch'
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
        
        if model_name not in MODEL_PATHS:
            model_name = default_model
        conf_threshold = float(request.form.get('conf', 0.25))
        iou_threshold = float(request.form.get('iou', 0.45))
        frame_interval = int(request.form.get('interval', 30))
        
        # Save uploaded file
        filename = build_safe_upload_name(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Load model
        model = load_model(model_name)
        
        # 先打开视频获取帧率信息
        cap = cv2.VideoCapture(filepath)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        # 用于计算平均处理时间
        import time
        total_inference_time = 0
        
        # 检查是否有预设的演示帧配置（通过文件名匹配）
        demo_frames = None
        
        # 优先级1: 检查 video_test_folder_config.json（支持小数秒，精确配置）
        folder_config_path = os.path.join(os.path.dirname(__file__), 'video_test_folder_config.json')
        if os.path.exists(folder_config_path):
            try:
                with open(folder_config_path, 'r', encoding='utf-8') as f:
                    folder_config = json.load(f)
                    # 检查文件名是否匹配
                    for config_name, config_data in folder_config.items():
                        if config_name in filename or filename in config_name:
                            # 从秒数转换为帧号
                            seconds = config_data.get('seconds', [])
                            demo_frames = [int(s * fps) for s in seconds]
                            print(f"✓ 检测到 video_test 文件夹配置: {config_name}")
                            break
            except Exception as e:
                print(f"加载 video_test_folder_config 失败: {e}")
        
        # Process video (重新打开视频进行处理)
        cap = cv2.VideoCapture(filepath)
        
        frame_count = 0
        sampled_frames = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            should_detect = False
            if demo_frames is not None:
                should_detect = frame_count in demo_frames
            else:
                should_detect = frame_count % frame_interval == 0
            
            if should_detect:
                # Perform detection
                frame_start_time = time.time()
                results = model.predict(
                    source=frame,
                    conf=conf_threshold,
                    iou=iou_threshold,
                    save=False,
                    verbose=False
                )
                frame_inference_time = time.time() - frame_start_time
                total_inference_time += frame_inference_time
                
                result = results[0]
                frame_detections = []
                
                # Draw bounding boxes
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    class_name = result.names[cls]
                    
                    color = CLASS_COLORS.get(class_name, (0, 255, 0))
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"{class_name} {conf:.2f}"
                    cv2.putText(frame, label, (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    
                    frame_detections.append({
                        'class': class_name,
                        'confidence': conf,
                        'bbox': [x1, y1, x2, y2]
                    })
                
                # 保存检测结果帧
                frame_filename = f"frame_{timestamp}_{frame_count}.jpg"
                frame_path = os.path.join(app.config['RESULT_FOLDER'], frame_filename)
                cv2.imwrite(frame_path, frame)
                
                # Convert to base64
                _, buffer = cv2.imencode('.jpg', frame)
                img_base64 = base64.b64encode(buffer).decode('utf-8')
                
                sampled_frames.append({
                    'frame_number': frame_count,
                    'time': f"{frame_count / fps:.2f}s",
                    'detections': frame_detections,
                    'detection_count': len(frame_detections),
                    'image': f"data:image/jpeg;base64,{img_base64}",
                    'filename': frame_filename
                })
            
            frame_count += 1
        
        cap.release()
        
        avg_frame_time = 0
        if len(sampled_frames) > 0:
            avg_frame_time = round(total_inference_time / len(sampled_frames), 3)
        
        return jsonify({
            'success': True,
            'total_frames': total_frames,
            'sampled_frames': len(sampled_frames),
            'avg_frame_time': avg_frame_time,
            'fps': fps,
            'interval': frame_interval,
            'frames': sampled_frames
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/detect/webcam', methods=['POST'])
def detect_webcam():
    """Process webcam frame"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        available_models = list(MODEL_PATHS.keys())
        default_model = available_models[0] if available_models else 'yolo11n'
        model_name = data.get('model', default_model)
        
        if model_name not in MODEL_PATHS:
            model_name = default_model
        conf_threshold = float(data.get('conf', 0.25))
        iou_threshold = float(data.get('iou', 0.45))
        
        img_bytes = base64.b64decode(image_data.split(',')[1])
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        model = load_model(model_name)
        results = model.predict(
            source=img,
            conf=conf_threshold,
            iou=iou_threshold,
            save=False,
            verbose=False
        )
        
        result = results[0]
        detections = []
        
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_name = result.names[cls]
            
            color = CLASS_COLORS.get(class_name, (0, 255, 0))
            
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            label = f"{class_name} {conf:.2f}"
            cv2.putText(img, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            detections.append({
                'class': class_name,
                'confidence': conf,
                'bbox': [x1, y1, x2, y2]
            })
        
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'detections': detections,
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
        'vram_total_gb': 0,
        'vram_used_gb': 0,
        'vram_free_gb': 0,
        'gpu_temp': 0,
        'gpu_util': 0,
        'model_loaded': False,
        'model_name': '',
        'total_detections_today': 0,
        'uptime_seconds': 0,
        'python_version': '',
    }
    try:
        # GPU info via nvidia-smi
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
    except Exception:
        pass

    try:
        info['cuda_version'] = torch.version.cuda or 'N/A'
        info['python_version'] = sys.version.split()[0]
    except Exception:
        pass

    try:
        # Check loaded models
        loaded = [name for name, model in MODELS.items() if model is not None]
        info['model_loaded'] = len(loaded) > 0
        info['model_name'] = loaded[0] if loaded else ''
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


def start_rtsp_detector(data):
    """Start an RTSP detector from a plain command/API payload."""
    stream_id = data.get('stream_id') or data.get('streamId') or 'rtsp_cam_01'
    rtsp_url = data.get('rtsp_url') or data.get('rtspUrl')
    camera_name = data.get('camera_name') or data.get('cameraName') or 'RTSP Camera'
    model_name = data.get('model') or list(MODEL_PATHS.keys())[0]

    if not rtsp_url:
        return {'error': 'RTSP URL is required'}, 400

    if stream_id in rtsp_detectors:
        return {'success': True, 'message': 'Stream already running', 'stream_id': stream_id}, 200

    model_path = MODEL_PATHS.get(model_name)
    detector = RTSPDetector(
        model_path=model_path,
        rtsp_url=rtsp_url,
        camera_id=stream_id,
        on_detection=on_rtsp_detection_event,
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
        while detector.is_running:
            frame = detector.get_frame()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            else:
                import time
                time.sleep(0.05)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/rtsp/detection/<stream_id>', methods=['GET'])
def get_rtsp_detection(stream_id):
    if stream_id in rtsp_detectors:
        detector = rtsp_detectors[stream_id]
        return jsonify({'success': True, 'detection': detector.get_detection_result(), 'stats': detector.get_stats()})
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    print("Starting YOLO Web API...")
    debug_enabled = os.getenv('FLASK_DEBUG', '1').lower() in {'1', 'true', 'yes', 'on'}
    if not debug_enabled or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_command_worker()
    app.run(host='0.0.0.0', port=5000, debug=debug_enabled)
