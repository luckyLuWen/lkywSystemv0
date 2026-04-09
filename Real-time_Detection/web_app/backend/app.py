from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import sys

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

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'webp', 'mp4', 'avi', 'mov'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# Load YOLO model - 使用最佳性能模型 YOLOv11n (mAP50=87.25%)
MODELS = {
    'yolo11n': None
}

MODEL_PATHS = {
    'yolo11n': '../../runs/detect/lkyw_fire_detection/weights/best.pt'
}

# 类别颜色映射 (BGR格式，OpenCV使用BGR而非RGB)
CLASS_COLORS = {
    'car_fire': (0, 0, 255),        # 红色 - 普通车辆火灾（最危险）
    'car_normal': (0, 255, 0),      # 绿色 - 普通车辆正常
    'lkyw_fire': (0, 0, 139),       # 深红色 - 两客一危火灾（最高优先级）
    'lkyw_normal': (255, 144, 30)   # 橙色 - 两客一危正常
}

# RTSP检测器管理
rtsp_detectors = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_model(model_name):
    """Lazy load model when needed"""
    if MODELS[model_name] is None:
        model_path = MODEL_PATHS[model_name]
        if os.path.exists(model_path):
            print(f"Loading model: {model_name} from {model_path}")
            try:
                # 尝试使用标准方式加载
                MODELS[model_name] = YOLO(model_path)
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
                MODELS[model_name] = YOLO(model_path)
                torch.load = original_load
            print(f"✓ Model loaded successfully: {model_name}")
        else:
            raise FileNotFoundError(f"Model file not found: {model_path}")
    return MODELS[model_name]

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get available models"""
    available_models = []
    for name, path in MODEL_PATHS.items():
        if os.path.exists(path):
            available_models.append({
                'name': name,
                'path': path,
                'size': os.path.getsize(path) / (1024 * 1024)  # Size in MB
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
        model_name = request.form.get('model', 'yolo11s')
        conf_threshold = float(request.form.get('conf', 0.25))
        iou_threshold = float(request.form.get('iou', 0.45))
        
        # Save uploaded file
        filename = secure_filename(file.filename)
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
        
        return jsonify({
            'success': True,
            'detections': detections,
            'count': len(detections),
            'image': f"data:image/jpeg;base64,{img_base64}",
            'result_file': result_filename,
            'inference_time': round(inference_time * 1000, 2)  # 转换为毫秒
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
        model_name = request.form.get('model', 'yolo11n')
        conf_threshold = float(request.form.get('conf', 0.25))
        iou_threshold = float(request.form.get('iou', 0.45))
        frame_interval = int(request.form.get('interval', 30))
        
        # Save uploaded file
        filename = secure_filename(file.filename)
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
        if demo_frames is None:
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
                                print(f"  视频帧率: {fps} fps")
                                print(f"  配置秒数: {seconds}")
                                print(f"  转换帧号: {demo_frames}")
                                print(f"  说明: {config_data.get('description', '无')}")
                                break
                except Exception as e:
                    print(f"加载 video_test_folder_config 失败: {e}")
        
        # 优先级2: video_test 命名规则（只支持整数秒）
        if demo_frames is None and 'video_test' in filename.lower():
            try:
                # 提取文件名中的数字（秒数）
                import re
                # 匹配 video_test 后面的数字（只匹配纯整数格式）
                pattern = r'video_test[_\-](\d+(?:[_\-]\d+)*)'
                match = re.search(pattern, filename.lower())
                if match:
                    # 提取所有数字
                    numbers_str = match.group(1)
                    # 分割数字（支持下划线或连字符分隔）
                    seconds = [int(s) for s in re.findall(r'\d+', numbers_str)]
                    if seconds:
                        # 转换秒数为帧号
                        demo_frames = [s * fps for s in seconds]
                        print(f"✓ 检测到 video_test 命名规则")
                        print(f"  视频帧率: {fps} fps")
                        print(f"  提取的秒数: {seconds}")
                        print(f"  转换的帧号: {demo_frames}")
            except Exception as e:
                print(f"解析 video_test 文件名失败: {e}")
        
        # 优先级3: 检查 demo_frames_config.json（直接配置帧号）
        if demo_frames is None:
                demo_config_path = os.path.join(os.path.dirname(__file__), 'demo_frames_config.json')
                if os.path.exists(demo_config_path):
                    try:
                        with open(demo_config_path, 'r', encoding='utf-8') as f:
                            demo_config = json.load(f)
                            # 检查文件名是否匹配配置中的任何键
                            for config_name, frames in demo_config.items():
                                if config_name in filename or filename in config_name:
                                    demo_frames = frames
                                    print(f"检测到演示视频配置: {config_name}, 目标帧: {frames}")
                                    break
                    except Exception as e:
                        print(f"加载演示帧配置失败: {e}")
        
        # Process video (重新打开视频进行处理)
        cap = cv2.VideoCapture(filepath)
        
        frame_count = 0
        sampled_frames = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # 判断是否需要检测当前帧
            # 如果有演示帧配置，只检测指定帧；否则按间隔检测
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
                    
                    # 根据类别选择颜色
                    color = CLASS_COLORS.get(class_name, (0, 255, 0))  # 默认绿色
                    
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
        
        # 计算平均帧处理时间（毫秒）
        avg_frame_time = 0
        if len(sampled_frames) > 0:
            avg_frame_time = round((total_inference_time / len(sampled_frames)) * 1000, 2)
        
        return jsonify({
            'success': True,
            'total_frames': total_frames,
            'sampled_frames': len(sampled_frames),
            'avg_frame_time': avg_frame_time,  # 新增：平均帧处理时间（毫秒）
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
        model_name = data.get('model', 'yolo11s')
        conf_threshold = float(data.get('conf', 0.25))
        iou_threshold = float(data.get('iou', 0.45))
        
        # Decode base64 image
        img_bytes = base64.b64decode(image_data.split(',')[1])
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Load model and perform detection
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
        
        # Draw bounding boxes
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_name = result.names[cls]
            
            # 根据类别选择颜色
            color = CLASS_COLORS.get(class_name, (0, 255, 0))  # 默认绿色
            
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            label = f"{class_name} {conf:.2f}"
            cv2.putText(img, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            detections.append({
                'class': class_name,
                'confidence': conf,
                'bbox': [x1, y1, x2, y2]
            })
        
        # Convert to base64
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

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'YOLO Web API is running'})


# ==================== RTSP实时流检测接口 ====================

@app.route('/api/rtsp/streams', methods=['GET'])
def get_rtsp_streams():
    """获取所有RTSP流配置"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'rtsp_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return jsonify({
                    'success': True,
                    'streams': config.get('rtsp_streams', [])
                })
        else:
            return jsonify({
                'success': True,
                'streams': []
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rtsp/start', methods=['POST'])
def start_rtsp_detection():
    """启动RTSP流检测"""
    try:
        data = request.get_json()
        stream_id = data.get('stream_id')
        rtsp_url = data.get('rtsp_url')
        camera_name = data.get('camera_name', 'RTSP Camera')
        
        if not rtsp_url:
            return jsonify({'error': 'RTSP URL is required'}), 400
        
        # 检查是否已经在运行
        if stream_id in rtsp_detectors:
            return jsonify({
                'success': True,
                'message': 'Stream already running',
                'stream_id': stream_id
            })
        
        # 创建并启动检测器
        model_path = MODEL_PATHS.get('yolo11n', '../../yolo11n.pt')
        detector = RTSPDetector(
            model_path=model_path,
            rtsp_url=rtsp_url,
            camera_id=stream_id
        )
        
        detector.connect()
        detector.start()
        
        rtsp_detectors[stream_id] = detector
        
        return jsonify({
            'success': True,
            'message': 'RTSP detection started',
            'stream_id': stream_id,
            'camera_name': camera_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rtsp/stop/<stream_id>', methods=['POST'])
def stop_rtsp_detection(stream_id):
    """停止RTSP流检测"""
    try:
        if stream_id not in rtsp_detectors:
            return jsonify({'error': 'Stream not found'}), 404
        
        detector = rtsp_detectors[stream_id]
        detector.stop()
        del rtsp_detectors[stream_id]
        
        return jsonify({
            'success': True,
            'message': 'RTSP detection stopped',
            'stream_id': stream_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rtsp/video_feed/<stream_id>')
def rtsp_video_feed(stream_id):
    """RTSP视频流输出（Motion JPEG）"""
    def generate():
        detector = rtsp_detectors.get(stream_id)
        if not detector:
            return
        
        while detector.is_running:
            frame = detector.get_frame()
            if frame is not None:
                # 编码为JPEG，降低质量以减少数据量
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # 如果没有帧，稍微等待
                import time
                time.sleep(0.05)
    
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/rtsp/detection/<stream_id>', methods=['GET'])
def get_rtsp_detection(stream_id):
    """获取RTSP流的最新检测结果"""
    try:
        if stream_id not in rtsp_detectors:
            return jsonify({'error': 'Stream not found'}), 404
        
        detector = rtsp_detectors[stream_id]
        result = detector.get_detection_result()
        stats = detector.get_stats()
        
        return jsonify({
            'success': True,
            'stream_id': stream_id,
            'detection': result,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rtsp/status', methods=['GET'])
def get_rtsp_status():
    """获取所有RTSP流的状态"""
    try:
        status = []
        for stream_id, detector in rtsp_detectors.items():
            stats = detector.get_stats()
            status.append(stats)
        
        return jsonify({
            'success': True,
            'active_streams': len(rtsp_detectors),
            'streams': status
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting YOLO Web API...")
    print("Available models:")
    for name, path in MODEL_PATHS.items():
        if os.path.exists(path):
            print(f"  - {name}: {path}")
    app.run(host='0.0.0.0', port=5000, debug=True)
