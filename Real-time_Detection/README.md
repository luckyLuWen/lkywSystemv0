# 🚗 两客一危交通事故火灾检测系统

基于 YOLOv11 的智能火灾检测系统，专门用于检测两客一危车辆（客车、危化品车）的火灾事故。

## 📋 项目简介

本项目使用深度学习技术，实现对交通事故中火灾的实时检测，特别关注"两客一危"车辆（客运车辆、危险品运输车辆）的安全监控。

### 主要功能

- 🔥 **火灾检测**：实时检测车辆火灾
- 🚌 **车辆分类**：识别两客一危车辆类型
- 📷 **多种检测模式**：
  - 图片检测
  - 视频抽帧检测
  - 实时摄像头检测
  - RTSP流检测（支持OBS推流）
- 🌐 **Web界面**：友好的可视化操作界面

## 🎯 检测类别

- `lkyw_fire` - 两客一危车辆火灾
- `lkyw_normal` - 两客一危车辆正常
- `car_fire` - 普通车辆火灾
- `car_normal` - 普通车辆正常

## 🚀 快速开始

### 环境要求

- Python 3.8+
- CUDA 11.0+ (可选，用于GPU加速)
- 8GB+ RAM

### 安装依赖

```bash
pip install ultralytics opencv-python flask flask-cors
```

### 下载模型

由于模型文件较大，请从以下链接下载：

- [YOLOv11n 模型](链接) - 推荐，速度快
- [YOLOv11s 模型](链接) - 平衡性能

将下载的模型文件放在项目根目录。

### 启动Web应用

```bash
# Windows
cd web_app
双击运行: 启动完整系统.bat

# 或手动启动
cd web_app/backend
python app.py
# 然后打开 web_app/frontend/index.html
```

## 📊 模型性能

| 模型 | mAP50 | mAP50-95 | 速度 (ms) | 参数量 |
|------|-------|----------|-----------|--------|
| YOLOv11n | 87.25% | 65.8% | ~10ms | 2.6M |
| YOLOv11s | 89.5% | 68.2% | ~15ms | 9.4M |

## 🎨 功能演示

### 1. 图片检测
上传图片，系统自动检测火灾和车辆类型。

### 2. 视频检测
上传视频，系统抽帧检测并展示结果。

### 3. 实时检测
- **本地摄像头**：直接使用电脑摄像头
- **RTSP流**：支持OBS推流，模拟真实监控场景

## 📁 项目结构

```
project/
├── web_app/                    # Web应用
│   ├── backend/               # Flask后端
│   │   ├── app.py            # 主应用
│   │   ├── rtsp_detector.py  # RTSP检测模块
│   │   └── rtsp_config.json  # RTSP配置
│   ├── frontend/              # 前端界面
│   │   └── index.html        # 主页面
│   └── 启动完整系统.bat       # 一键启动
├── dataset_split/             # 数据集（需自行准备）
├── runs/                      # 训练结果（需自行训练）
├── *.pt                       # 模型文件（需下载）
└── README.md                  # 本文件
```

## 🔧 RTSP实时检测

### 使用OBS Studio推流

1. 安装 [OBS Studio](https://obsproject.com/)
2. 安装 [obs-rtspserver 插件](https://github.com/iamscottxu/obs-rtspserver)
3. 配置RTSP服务器（端口8554）
4. 在Web界面选择"RTSP流"模式
5. 开始实时检测

详细配置请参考：`web_app/OBS_RTSP配置指南.md`

## 📖 文档

- [RTSP实时检测使用指南](web_app/RTSP实时检测使用指南.md)
- [OBS配置指南](web_app/OBS_RTSP配置指南.md)
- [部署说明](web_app/部署到实时检测模块说明.md)
- [项目清理指南](项目清理指南.md)

## 🛠️ 训练自己的模型

```python
from ultralytics import YOLO

# 加载预训练模型
model = YOLO('yolo11n.pt')

# 训练
model.train(
    data='dataset_split/dataset.yaml',
    epochs=100,
    imgsz=640,
    batch=16
)
```

## 📈 性能优化

- 使用GPU加速（CUDA）
- 降低输入分辨率
- 使用更小的模型（yolo11n）
- 调整置信度阈值

## ⚠️ 注意事项

1. **模型文件**：由于文件较大，未包含在仓库中，请单独下载
2. **数据集**：训练数据集需自行准备或联系作者获取
3. **GPU推荐**：实时检测建议使用GPU加速

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👨‍💻 作者

[你的名字]

## 🙏 致谢

- [Ultralytics YOLOv11](https://github.com/ultralytics/ultralytics)
- [OBS Studio](https://obsproject.com/)
- [Flask](https://flask.palletsprojects.com/)

## 📞 联系方式

- Email: your.email@example.com
- GitHub: [@yourusername](https://github.com/yourusername)

---

**⭐ 如果这个项目对你有帮助，请给个Star！**
