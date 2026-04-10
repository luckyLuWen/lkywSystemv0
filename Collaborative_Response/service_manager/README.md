# 协同响应服务控制层
这个目录提供 `dh` 子系统的远程服务状态与启停控制层。

它不承载业务页面，只负责：

- 轮询探测协同响应相关服务是否在线
- 暴露统一 HTTP 接口给 `Collaborative_Response` 前端和 `vue-project_all`
- 按配置命令启动或停止远程端服务

## 目录说明

- `server.py`：控制层主程序，基于 Python 标准库
- `config.example.json`：默认配置模板，已对齐本仓库内的 `backend/command_center`
- `config.local.json`：本机或服务器实际配置，需要自行创建，不进 Git
- `logs/`：服务输出日志
- `runtime/`：PID 文件

## 首次配置
```powershell
cd q:\liangkeweb\lkywSystem\Collaborative_Response\service_manager
Copy-Item config.example.json config.local.json
```

如果你们部署地址不是默认的 `127.0.0.1:5000` / `127.0.0.1:8501`，就在 `config.local.json` 覆盖：

- `public_url`：浏览器真正访问的地址
- `health_url`：控制层探活地址
- `working_directory`：启动命令工作目录
- `start_command`：启动命令
- `stop_command`：可选关闭命令

默认模板里的 `streamlit` 已改成 `python -m streamlit`，这样比直接写 `streamlit` 命令更稳。
如果控制层运行时提示 `No module named streamlit`，说明当前 Python 环境没装依赖，
要么先在该环境执行 `pip install -r ../backend/command_center/requirements.txt`，
要么在 `config.local.json` 里把 `start_command` 改成你们实际虚拟环境里的 Python 绝对路径。

## 启动控制层
```powershell
cd q:\liangkeweb\lkywSystem\Collaborative_Response\service_manager
python server.py
```

默认监听：

- `http://127.0.0.1:18601`

## 主要接口

- `GET /api/health`
- `GET /api/services`
- `GET /api/services/{serviceId}`
- `POST /api/services/{serviceId}/start`
- `POST /api/services/{serviceId}/stop`
- `POST /api/services/{serviceId}/restart`
- `POST /api/reload-config`

## 注意事项

- 控制层默认没有鉴权，不要直接暴露到公网
- `stop_command` 留空时，会尝试结束由控制层自身拉起并记录了 PID 的进程
- 示例配置里的 `commandCenter` 和 `streamlit` 已能直接管理当前仓库内的协同响应后端
