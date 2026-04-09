# lkywSystem 项目说明

## 一、项目结构

- `vue-project_all`：主程序壳工程，统一入口。
- `Collaborative_Response`：协同响应子系统，由同事 A 负责。
- `Constructive simulation`：建构仿真子系统，由同事 B 负责。
- `Real-time_Detection`：实时检测子系统，由同事 C 负责。
- `Sensor_Management`：传感器管理子系统，由同事 D 负责。
- `scripts/sync-subsystems.ps1`：将子系统构建结果同步到 `vue-project_all/public` 的脚本。

## 二、当前仓库约定

- 四个子系统目录是源码真源。
- `vue-project_all/public` 只放主程序集成时使用的静态副本。
- 不要手工直接修改 `vue-project_all/public` 里的子系统页面。
- 如果子系统改动影响主程序集成页面，应先构建对应子系统，再执行同步脚本。

## 三、为什么保留 scripts

`scripts` 目录目前只保留了一个脚本：`sync-subsystems.ps1`。

这个脚本是有必要的，因为当前主程序通过 `iframe` 引用的是 `vue-project_all/public` 下的静态副本，而不是直接读取四个子系统源码目录。
如果没有这个脚本，后续大家只能手工复制文件，极容易漏拷、错拷、覆盖错误版本。

结论：

- `scripts` 目录保留。
- 目前没有多余脚本，不再额外删除。

## 四、本地运行方式

### 1. 只运行主程序壳界面

适合查看整体菜单、路由跳转、主程序集成页面。

```powershell
cd vue-project_all
npm install
npm run dev
```

启动后打开终端输出的本地地址，通常类似：

```text
http://localhost:5173
```

说明：

- 主程序会直接读取 `vue-project_all/public` 下已经同步好的四个子系统静态页面。
- 如果只看页面框架，这一步通常已经够了。

### 2. 运行完整联调环境

如果你希望不仅看到页面，还希望传感器管理、实时检测等功能真正访问后端，就需要分别启动对应服务。

#### 主程序

```powershell
cd vue-project_all
npm install
npm run dev
```

#### 协同响应子系统

```powershell
cd Collaborative_Response
npm install
npm run dev
```

注意：

- 该子系统源码中还依赖 `http://localhost:8501` 和 `http://127.0.0.1:3005` 相关服务。
- 如果这些服务没启动，页面可能只能部分显示。

#### 实时检测子系统

后端：

```powershell
cd Real-time_Detection\web_app\backend
pip install -r requirements.txt
python app.py
```

说明：

- 默认后端地址是 `http://localhost:5000`。
- 主程序集成页和该子系统前端都依赖这个后端。

前端单独查看时可直接打开：

```text
Real-time_Detection\web_app\frontend\index.html
```

#### 传感器管理子系统

后端：

```powershell
cd Sensor_Management\IOT\backend
pip install -r requirements.txt
python main.py
```

前端开发：

```powershell
cd Sensor_Management\IOT\frontend
npm install
npm run dev
```

说明：

- 默认后端地址是 `http://localhost:8000`。
- 前端中也使用了 `ws://localhost:8000/ws`。

#### 建构仿真子系统

该子系统当前是静态页面资源，直接通过主程序加载即可。
如果单独查看，可以直接打开：

```text
Constructive simulation\index.html
```

## 五、子系统改动后如何同步到主程序

如果某个同事改了自己的子系统，并且希望主程序也使用最新页面，需要在仓库根目录执行：

```powershell
.\scripts\sync-subsystems.ps1
```

它会刷新以下目录：

- `vue-project_all/public/collaborative-response`
- `vue-project_all/public/constructive-simulation`
- `vue-project_all/public/realtime-detection`
- `vue-project_all/public/sensor-management`

## 六、Git 分支模型

- `main`：稳定发布分支。
- `develop`：日常集成分支。
- `feature/<子系统>-<功能>`：每个人从 `develop` 拉出来的功能分支。
- `hotfix/<问题名>`：线上紧急修复分支。

建议分支命名：

- 同事 A：`feature/collaborative-response-...`
- 同事 B：`feature/constructive-simulation-...`
- 同事 C：`feature/realtime-detection-...`
- 同事 D：`feature/sensor-management-...`

## 七、每个人负责范围

- 同事 A 主要改 `Collaborative_Response/`
- 同事 B 主要改 `Constructive simulation/`
- 同事 C 主要改 `Real-time_Detection/`
- 同事 D 主要改 `Sensor_Management/`
- 你作为总负责人，主要改 `vue-project_all/` 和跨子系统集成规则

以下内容属于共享区域，改动前最好先沟通：

- `vue-project_all/src/router/`
- `vue-project_all/src/views/`
- `vue-project_all/src/components/`
- `vue-project_all/public/`
- `scripts/`
- `.gitignore`
- `README.md`
- `CONTRIBUTING.md`

## 八、上传到 GitHub 后的推荐协作方式

### 你如何工作

1. 维护 `main` 和 `develop`
2. 审查四位同事提交到 `develop` 的 Pull Request
3. 处理跨子系统冲突
4. 在主程序里完成统一接入和联调
5. 当 `develop` 稳定后，再合并到 `main`

### 同事 A-D 如何工作

每个人都遵循同一套流程：

1. 先切到 `develop`
2. 拉最新代码
3. 从 `develop` 新建自己的功能分支
4. 只修改自己负责的目录，或者经过沟通后再改共享文件
5. 在自己本机环境下运行、验证
6. 提交并推送自己的功能分支
7. 发起到 `develop` 的 Pull Request
8. 等你 review 后再合并

### 一个模拟示例

假设同事 C 要改实时检测：

```powershell
git switch develop
git pull origin develop
git switch -c feature/realtime-detection-camera-page
```

然后他只修改：

- `Real-time_Detection/...`

如果这次改动还影响主程序里显示的静态页面，他再执行：

```powershell
.\scripts\sync-subsystems.ps1
```

然后提交：

```powershell
git add .
git commit -m "feat: 更新实时检测页面与联调资源"
git push origin feature/realtime-detection-camera-page
```

再去 GitHub 上发起：

- 源分支：`feature/realtime-detection-camera-page`
- 目标分支：`develop`

你审核通过后合并到 `develop`。

## 九、新机器拉代码后的最小操作

如果只是负责某一个子系统，不需要一上来把所有目录都装依赖。

例如你只负责主程序：

```powershell
cd vue-project_all
npm install
```

例如你只负责传感器管理前端：

```powershell
cd Sensor_Management\IOT\frontend
npm install
```

按负责范围安装依赖即可。
