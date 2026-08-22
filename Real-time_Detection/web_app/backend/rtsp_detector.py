"""
RTSP实时流检测模块
支持从RTSP流接收视频并进行YOLO检测
"""
import cv2
import threading
import time
from ultralytics import YOLO
import numpy as np


CLASS_COLORS = {
    "carFire": (53, 57, 229),
    "car_fire": (53, 57, 229),
    "lkywFire": (91, 24, 194),
    "lkyw_fire": (91, 24, 194),
    "carNofire": (53, 216, 253),
    "car_nofire": (53, 216, 253),
    "lkywNofire": (0, 140, 251),
    "lkyw_nofire": (0, 140, 251),
    "car_normal": (53, 216, 253),
    "lkyw_normal": (0, 140, 251),
    "normal": (233, 165, 14),
    "accident": (46, 67, 168),
}


def get_class_color(class_name):
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
    """
    检查类别是否属于事故/异常类别（用于事故检测次数统计）：
    - 包含事故标签：carFire, lkywFire, carNofire, lkywNofire, leak
    - 排除正常/未泄露标签：noleak, no_leak, tank_normal, normal
    """
    if not class_name:
        return False
    normalized_name = str(class_name).strip().lower().replace("-", "_").replace(" ", "_")

    normal_markers = ("noleak", "no_leak", "tank_normal", "normal", "正常", "未泄露", "未起火")
    if any(marker in normalized_name for marker in normal_markers):
        return False

    accident_markers = ("fire", "起火", "火灾", "着火", "leak", "hazmat", "tank", "泄露", "泄漏", "危化", "nofire", "accident")
    return any(marker in normalized_name for marker in accident_markers)


class RTSPDetector:
    def __init__(self, model_path, rtsp_url, camera_id="RTSP-01", on_detection=None, detect_frame_fn=None, conf_threshold=0.70, iou_threshold=0.45, model_name=None, detection_mode='single', task_type='collision'):
        """
        初始化RTSP检测器
        """
        self.model = YOLO(model_path) if model_path else None
        self.rtsp_url = rtsp_url
        self.camera_id = camera_id
        self.on_detection = on_detection
        self.detect_frame_fn = detect_frame_fn
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.model_name = model_name or 'SFGA-YOLO26M'
        self.detection_mode = detection_mode
        self.task_type = task_type
        
        self.cap = None
        self.is_running = False
        self.current_frame = None
        self.detection_result = None
        self.frame_version = 0
        self.last_inference_time = 0.019
        self.lock = threading.Lock()
        
        # 统计信息与事故防抖控制
        self.frame_count = 0
        self.fire_count = 0
        self.last_detection_time = None
        self.in_accident_state = False
        self.last_accident_count_time = 0.0

    def update_settings(self, conf_threshold=None, iou_threshold=None, model_name=None, detection_mode=None, task_type=None):
        with self.lock:
            if conf_threshold is not None:
                self.conf_threshold = float(conf_threshold)
            if iou_threshold is not None:
                self.iou_threshold = float(iou_threshold)
            if model_name is not None:
                self.model_name = str(model_name)
            if detection_mode is not None:
                self.detection_mode = str(detection_mode)
            if task_type is not None:
                self.task_type = str(task_type)
        print(f"🔄 RTSP检测器参数实时更新: conf={self.conf_threshold}, iou={self.iou_threshold}, model={self.model_name}, mode={self.detection_mode}")
        
    def connect(self):
        """连接RTSP流"""
        self.cap = cv2.VideoCapture(self.rtsp_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self.cap.isOpened():
            raise Exception(f"无法连接到RTSP流: {self.rtsp_url}")
        
        print(f"✅ 成功连接RTSP流: {self.rtsp_url}")
        return True
    
    def start(self):
        """启动检测线程"""
        if self.is_running:
            print("检测器已在运行")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        print(f"🚀 RTSP检测器已启动: {self.camera_id}")
    
    def stop(self):
        """停止检测"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        print(f"⏹️ RTSP检测器已停止: {self.camera_id}")
    
    def _detection_loop(self):
        """检测循环（在独立线程中运行）"""
        retry_count = 0
        max_retries = 5
        
        while self.is_running:
            try:
                if not self.cap or not self.cap.isOpened():
                    if retry_count < max_retries:
                        print(f"尝试重新连接RTSP流... ({retry_count + 1}/{max_retries})")
                        self.connect()
                        retry_count += 1
                        time.sleep(2)
                        continue
                    else:
                        print("❌ 达到最大重试次数，停止检测")
                        break
                
                ret, frame = self.cap.read()
                
                if not ret:
                    print("⚠️ 读取帧失败，尝试重新连接...")
                    self.cap.release()
                    time.sleep(1)
                    continue
                
                retry_count = 0
                
                # 获取最新的设置参数
                with self.lock:
                    conf_val = self.conf_threshold
                    iou_val = self.iou_threshold
                    model_val = self.model_name
                    mode_val = self.detection_mode

                start_t = time.time()
                if self.detect_frame_fn:
                    annotated_frame, detections = self.detect_frame_fn(frame, model_val, mode_val, conf_val, iou_val)
                else:
                    results = self.model.predict(source=frame, conf=conf_val, iou=iou_val, verbose=False)
                    annotated_frame = self._draw_detection_result(frame, results[0])
                    detections = self._extract_detections(results[0])
                proc_time = round(time.time() - start_t, 3)
                
                detection_info = {
                    'camera_id': self.camera_id,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'detections': detections,
                    'has_fire': any(is_fire_class(d.get('class', '')) for d in detections),
                    'vehicle_type': next((d.get('class') for d in detections if '客车' in d.get('class', '') or '危化品' in d.get('class', '')), None),
                    'inference_time': proc_time
                }

                notify_detection = False
                stats_snapshot = None
                now_t = time.time()
                has_accident = detection_info.get('has_fire', False)

                with self.lock:
                    self.current_frame = annotated_frame
                    self.detection_result = detection_info
                    self.frame_count += 1
                    self.frame_version += 1
                    self.last_detection_time = now_t
                    self.last_inference_time = proc_time
                    
                    if has_accident:
                        # 防抖与事件去重逻辑：从无事故变为有事故，或距上次计数超过3秒时记为一次新的事故检测
                        if not self.in_accident_state or (now_t - self.last_accident_count_time > 3.0):
                            self.fire_count += 1
                            self.last_accident_count_time = now_t
                            notify_detection = True
                        self.in_accident_state = True
                    else:
                        self.in_accident_state = False

                    stats_snapshot = {
                        'camera_id': self.camera_id,
                        'rtsp_url': self.rtsp_url,
                        'is_running': self.is_running,
                        'frame_count': self.frame_count,
                        'fire_count': self.fire_count,
                        'last_detection_time': self.last_detection_time,
                        'inference_time': proc_time
                    }

                if notify_detection and self.on_detection:
                    try:
                        self.on_detection(detection_info, stats_snapshot)
                    except Exception as callback_error:
                        print(f"⚠️ RTSP检测事件回调失败: {callback_error}")
                
                time.sleep(0.01)
                
            except Exception as e:
                print(f"❌ 检测循环错误: {e}")
                time.sleep(1)
    
    def _draw_detection_result(self, frame, result):
        annotated_frame = frame.copy()
        if result.boxes is None or len(result.boxes) == 0:
            return annotated_frame

        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_name = result.names[cls]
            color = get_class_color(class_name)

            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            label = f"{class_name} {conf:.2f}"
            label_y = max(y1 - 10, 20)
            cv2.putText(
                annotated_frame,
                label,
                (x1, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )

        return annotated_frame

    def _extract_detections(self, result):
        detections = []
        if result.boxes is not None and len(result.boxes) > 0:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = result.names[cls_id]
                detections.append({
                    'class': class_name,
                    'confidence': round(conf, 3),
                    'bbox': box.xyxy[0].tolist()
                })
        return detections

    def get_frame(self):
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame.copy(), self.frame_version
        return None, 0
    
    def get_detection_result(self):
        with self.lock:
            return self.detection_result.copy() if self.detection_result else None
    
    def get_stats(self):
        with self.lock:
            return {
                'camera_id': self.camera_id,
                'rtsp_url': self.rtsp_url,
                'is_running': self.is_running,
                'frame_count': self.frame_count,
                'fire_count': self.fire_count,
                'last_detection_time': self.last_detection_time,
                'inference_time': getattr(self, 'last_inference_time', 0.019)
            }
