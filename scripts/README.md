# 子系统静态资源同步脚本说明

本文说明这两个脚本的作用和每一步逻辑：

- `scripts/sync-subsystems.ps1`：Windows PowerShell 版本。
- `scripts/sync-subsystems.sh`：Bash / Linux / macOS / Git Bash 版本。

两个脚本做同一件事：把各子系统已经构建好的前端静态文件，同步到总系统 `vue-project_all/public` 下，供总系统通过 iframe 或静态路径加载。

## 什么时候需要运行

子系统负责人修改了前端页面，并且希望总系统里集成的静态副本也更新时，需要先构建子系统，再运行同步脚本。

示例：

```powershell
cd .\Sensor_Management\IOT\frontend
npm install
npm run build

cd ..\..\..
.\scripts\sync-subsystems.ps1 -TargetName sensor-management
```

如果要同步全部子系统：

```powershell
.\scripts\sync-subsystems.ps1
```

Bash 版本：

```bash
./scripts/sync-subsystems.sh sensor-management
./scripts/sync-subsystems.sh
```

## 目标目录对应关系

| 同步目标名 | 负责人/模块 | 源目录 | 复制到总系统 |
| --- | --- | --- | --- |
| `collaborative-response` | 协同响应 | `Collaborative_Response/dist` | `vue-project_all/public/collaborative-response` |
| `constructive-simulation` | 构建仿真 | `Constructive simulation` | `vue-project_all/public/constructive-simulation` |
| `realtime-detection` | 实时检测 | `Real-time_Detection/web_app/frontend/vue-frontend/dist` | `vue-project_all/public/realtime-detection` |
| `sensor-management` | 传感器管理 | `Sensor_Management/IOT/frontend/dist` | `vue-project_all/public/sensor-management` |

`dist` 目录必须先由对应子系统执行 `npm run build` 生成。同步脚本不会自动构建。

## PowerShell 版参数

同步全部：

```powershell
.\scripts\sync-subsystems.ps1
```

只同步一个：

```powershell
.\scripts\sync-subsystems.ps1 -TargetName realtime-detection
```

同步多个：

```powershell
.\scripts\sync-subsystems.ps1 -TargetName realtime-detection,sensor-management
```

如果目标名写错，脚本会报错并列出合法目标名。

## Bash 版参数

同步全部：

```bash
./scripts/sync-subsystems.sh
```

只同步一个：

```bash
./scripts/sync-subsystems.sh realtime-detection
```

同步多个：

```bash
./scripts/sync-subsystems.sh realtime-detection sensor-management
```

## 每一步逻辑

### 1. 失败即停止

PowerShell 版：

```powershell
$ErrorActionPreference = 'Stop'
```

Bash 版：

```bash
set -euo pipefail
```

含义：只要有关键步骤失败，就立即停止，避免只同步一半还继续往下跑。

### 2. 计算仓库根目录和总系统 public 目录

脚本先根据自身所在位置算出仓库根目录：

```text
scripts/..
```

然后得到总系统静态资源目录：

```text
vue-project_all/public
```

所以脚本可以从仓库根目录运行，也可以从其他目录运行。

### 3. 定义目标列表

脚本内维护一张目标表，每一项包含：

- `Name`：同步目标名，比如 `realtime-detection`。
- `Source`：子系统构建产物目录。
- `Type`：同步类型，当前有 `vite` 和 `static`。

`vite` 类型会额外处理 `index.html` 里的资源路径。

### 4. 可选过滤目标

如果没有传目标名，脚本同步全部。

如果传了目标名，脚本只同步指定目标。这样某个子系统负责人可以只更新自己的目录，避免影响其他子系统。

### 5. 检查源目录是否存在

如果源目录不存在，脚本会停止并提示：

```text
Source directory not found
```

常见原因：

- 还没执行 `npm run build`。
- 子系统目录路径改了，但脚本里的 `Source` 没同步更新。
- 当前分支缺少该子系统产物。

### 6. 重置目标目录

脚本会删除目标目录并重新创建，例如：

```text
vue-project_all/public/realtime-detection
```

这样可以避免旧的 hashed JS/CSS 文件残留。

两个脚本都加了保护：只允许重置 `vue-project_all/public` 下面的目标目录，避免误删仓库其他位置。

### 7. 复制目录内容

脚本复制源目录里的所有内容到目标目录。

例如实时检测：

```text
Real-time_Detection/web_app/frontend/vue-frontend/dist/*
```

复制到：

```text
vue-project_all/public/realtime-detection/*
```

同步完成后，总系统会通过下面的地址加载：

```text
/realtime-detection/index.html
```

### 8. 修正 Vite 资源路径

Vite 默认构建出的 `index.html` 通常会写：

```html
<script src="/assets/xxx.js"></script>
<link href="/assets/xxx.css">
```

但子系统放在总系统 public 的子目录下时，正确路径应是：

```html
<script src="./assets/xxx.js"></script>
<link href="./assets/xxx.css">
```

所以 `vite` 类型目标会把：

- `href="/assets/` 改成 `href="./assets/`
- `src="/assets/` 改成 `src="./assets/`
- `href="/vite.svg"` 改成 `href="./vite.svg"`

PowerShell 版使用显式 UTF-8 读写，避免中文 `<title>` 被写成乱码。

## 常见问题

### 1. `Source directory not found`

先进入对应子系统执行构建：

```powershell
npm install
npm run build
```

然后重新同步。

### 2. 页面白屏，但文件存在

优先检查同步后的 `index.html`：

- `<title>` 是否完整闭合。
- `script` 是否引用 `./assets/...`。
- `assets` 目录里是否真的有对应 JS/CSS。

### 3. title 在 PowerShell 里看是乱码

如果 `Select-String` 能正常显示，浏览器也正常显示，通常只是 PowerShell 控制台编码问题。

如果文件里真的变成乱码，重新运行最新的同步脚本即可。

### 4. 删除目标目录失败

如果报：

```text
Access to the path ... is denied
```

通常是文件被浏览器、编辑器、杀毒软件、dev server 或权限策略占用。先关闭相关程序，再重试。必要时用管理员权限运行。

### 5. 总系统还是看不到最新页面

尝试：

```text
Ctrl + F5
```

强制刷新浏览器缓存。

## 维护规则

如果子系统路径变化，需要同时更新：

- `sync-subsystems.ps1`
- `sync-subsystems.sh`
- 本说明文档中的目标目录表

如果新增一个子系统，需要增加：

1. 子系统构建产物目录。
2. 总系统 public 下的目标名。
3. 两个脚本里的目标配置。
4. 总系统路由或 iframe 入口配置。
