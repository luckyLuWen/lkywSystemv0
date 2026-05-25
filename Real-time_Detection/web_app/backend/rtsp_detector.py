"""
RTSP实时流检测模块
支持从RTSP流接收视频并进行YOLO检测
"""
import cv2
import threading
import time
from ultralytics import YOLO
import numpy as np


class RTSPDetector:
    def __init__(self, model_path, rtsp_url, camera_id="RTSP-01", on_detection=None):
        """
        初始化RTSP检测器
        
        Args:
            model_path: YOLO模型路径
            rtsp_url: RTSP流地址
            camera_id: 摄像头标识
        """
        self.model = YOLO(model_path)
        self.rtsp_url = rtsp_url
        self.camera_id = camera_id
        self.on_detection = on_detection
        
        self.cap = None
        self.is_running = False
        self.current_frame = None
        self.detection_result = None
        self.lock = threading.Lock()
        
        # 统计信息
        self.frame_count = 0
        self.fire_count = 0
        self.last_detection_time = None
        
    def connect(self):
        """连接RTSP流"""
        self.cap = cv2.VideoCapture(self.rtsp_url)
        
        # 设置缓冲区大小，减少延迟
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
        frame_skip_counter = 0  # 帧跳过计数器
        
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
                
                # 重置重试计数
                retry_count = 0
                
                # 跳帧处理：每2帧处理1帧，减少闪烁
                frame_skip_counter += 1
                if frame_skip_counter % 2 != 0:
                    continue
                
                # 执行YOLO检测
                results = self.model(frame, verbose=False)
                
                # 绘制检测结果
                annotated_frame = results[0].plot()
                
                # 提取检测信息
                detection_info = self._extract_detection_info(results[0])
                
                # 更新当前帧和检测结果
                notify_detection = False
                stats_snapshot = None
                with self.lock:
                    self.current_frame = annotated_frame
                    self.detection_result = detection_info
                    self.frame_count += 1
                    self.last_detection_time = time.time()
                    
                    # 统计火灾检测次数
                    if detection_info.get('has_fire', False):
                        self.fire_count += 1
                        notify_detection = True

                    stats_snapshot = {
                        'camera_id': self.camera_id,
                        'rtsp_url': self.rtsp_url,
                        'is_running': self.is_running,
                        'frame_count': self.frame_count,
                        'fire_count': self.fire_count,
                        'last_detection_time': self.last_detection_time
                    }

                if notify_detection and self.on_detection:
                    try:
                        self.on_detection(detection_info, stats_snapshot)
                    except Exception as callback_error:
                        print(f"⚠️ RTSP检测事件回调失败: {callback_error}")
                
                # 控制帧率，避免CPU占用过高和画面闪烁
                time.sleep(0.1)  # 约10fps，更稳定
                
            except Exception as e:
                print(f"❌ 检测循环错误: {e}")
                time.sleep(1)
    
    def _extract_detection_info(self, result):
        """提取检测信息"""
        info = {
            'camera_id': self.camera_id,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'detections': [],
            'has_fire': False,
            'vehicle_type': None
        }
        
        if result.boxes is not None and len(result.boxes) > 0:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = result.names[cls_id]
                
                detection = {
                    'class': class_name,
                    'confidence': round(conf, 3),
                    'bbox': box.xyxy[0].tolist()
                }
                info['detections'].append(detection)
                
                # 判断是否检测到火灾
                if '火' in class_name or 'fire' in class_name.lower():
                    info['has_fire'] = True
                
                # 判断车辆类型
                if '客车' in class_name or '危化品' in class_name:
                    info['vehicle_type'] = class_name
        
        return info
    
    def get_frame(self):
        """获取当前检测帧（用于视频流传输）"""
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None
    
    def get_detection_result(self):
        """获取最新检测结果"""
        with self.lock:
            return self.detection_result.copy() if self.detection_result else None
    
    def get_stats(self):
        """获取统计信息"""
        return {
            'camera_id': self.camera_id,
            'rtsp_url': self.rtsp_url,
            'is_running': self.is_running,
            'frame_count': self.frame_count,
            'fire_count': self.fire_count,
            'last_detection_time': self.last_detection_time
        }
