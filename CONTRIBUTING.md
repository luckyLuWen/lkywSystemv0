# 协作提交流程

## 一、分支规则

- 不要直接在 `main` 上开发。
- 不要直接在 `develop` 上开发。
- 一律从 `develop` 拉个人功能分支。
- 分支名要体现子系统和任务内容。

示例：

- `feature/collaborative-response-map-panel`
- `feature/constructive-simulation-scene-fix`
- `feature/realtime-detection-camera-page`
- `feature/sensor-management-device-table`

## 二、提交范围规则

- 只提交与你任务相关的文件。
- 不要提交 `node_modules`、`dist`、`__pycache__` 这类生成目录。
- 不要顺手混入别人的功能改动。

如果你的改动影响主程序集成页面：

1. 先构建对应子系统。
2. 再执行 `.\scripts\sync-subsystems.ps1`。
3. 把源码改动和同步后的主程序静态副本一起提交。

## 三、Pull Request 前检查

- 该分支是从 `develop` 创建的。
- 改动主要集中在自己负责的子系统。
- 已在自己的本地环境完成验证。
- 如涉及主程序集成，已执行 `.\scripts\sync-subsystems.ps1`。
- 没有带入无关文件。

## 四、需要谨慎修改的共享区域

- `vue-project_all/src/router/`
- `vue-project_all/src/views/`
- `vue-project_all/src/components/`
- `vue-project_all/public/`
- `scripts/`
- `.gitignore`
- `README.md`
- `CONTRIBUTING.md`

这些文件如果多人同时改，最容易冲突。
改之前最好先在群里说一声。

## 五、推荐工作流

```powershell
git switch develop
git pull origin develop
git switch -c feature/你的子系统-你的任务
```

开发完成后：

```powershell
git add .
git commit -m "feat: 说明你的改动"
git push origin feature/你的子系统-你的任务
```

然后在 GitHub 上发起：

- 源分支：你的功能分支
- 目标分支：`develop`

## 六、总负责人职责

- 维护 `main` 和 `develop`
- 审核同事 A-D 的 Pull Request
- 处理共享文件冲突
- 负责主程序 `vue-project_all` 的统一集成
- 在适合发布时把 `develop` 合并到 `main`
