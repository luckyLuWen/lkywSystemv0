"""
配置文件 - 可根据需要修改
"""
import os

class Config:
    """应用配置"""
    
    # 服务器配置
    HOST = '0.0.0.0'
    PORT = 5000
    DEBUG = True
    
    # 文件上传配置
    UPLOAD_FOLDER = 'uploads'
    RESULT_FOLDER = 'results'
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'webp', 'mp4', 'avi', 'mov'}
    
    # 模型配置 - 使用最佳性能模型 YOLOv11n (mAP50=87.25%)
    MODEL_PATHS = {
        'yolo11n': '../../runs/detect/lkyw_fire_detection/weights/best.pt'
    }
    
    # 默认检测参数
    DEFAULT_CONF = 0.70  # 置信度阈值
    DEFAULT_IOU = 0.45   # IOU 阈值
    
    # CORS 配置
    CORS_ORIGINS = '*'  # 允许所有来源，生产环境建议指定具体域名
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'app.log'
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 创建必要的目录
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.RESULT_FOLDER, exist_ok=True)


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
