# 协同响应后端
这个目录是 `dh` 子系统真正的业务后端，来自 `Command_Center` 的整理版，已经并入 `Collaborative_Response`。

包含能力：

- `app_2d.py`：协同调度平台 `Streamlit` 页面
- `server.py`：二维推演、三维态势地图、策略评估与静态资源服务
- `Cesium/`：本地三维查看器资源
- `path_result.json`、`mission.czml`：三维与评估输出文件

## 首次安装
```powershell
cd q:\liangkeweb\lkywSystem\Collaborative_Response\backend\command_center
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 单独启动后端
```powershell
cd q:\liangkeweb\lkywSystem\Collaborative_Response\backend\command_center
python server.py
```

默认地址：

- 指挥后端：`http://127.0.0.1:5001`
- 三维页面：`http://127.0.0.1:5001/cesium_viewer`
- 二维推演：`http://127.0.0.1:5001/wuhan_rescue_optimized.html`
- 评估指标：`http://127.0.0.1:5001/api/strategy_metrics`

## 单独启动协同调度平台
```powershell
cd q:\liangkeweb\lkywSystem\Collaborative_Response\backend\command_center
python -m streamlit run app_2d.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false
```

默认地址：

- `http://127.0.0.1:8501/?embed=true`

## 推荐方式
推荐通过 `Collaborative_Response/service_manager/server.py` 启动和管理：

- `commandCenter` 负责 `server.py`
- `streamlit` 负责 `app_2d.py`

这样 `vue-project_all` 首页和协同响应页都能看到状态并远程启停。
