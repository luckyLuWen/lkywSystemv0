# 登录配置

双击仓库根目录 create_login_account.bat 创建账号。输入账号、角色和至少八位密码（密码输入时不显示）。可重复执行创建不同账号。

角色：commander（指挥员）、dispatcher（调度员）、expert（技术专家）、admin（系统管理员）。

随后重启 start_integration_hub.bat 与前端开发服务。登录页选择的岗位必须与账号匹配。没有预置账号或通用密码。

账号密码以 PBKDF2 哈希保存于 accounts.sqlite3，服务端会话有效期为八小时。数据库不提交版本库；请备份并限制读取权限。

生产部署须将 /api/auth 反向代理至 Integration Hub（默认端口18701），使用 HTTPS。当前变更控制系统页面入口；其他模块业务 API 尚未统一接入认证，不能据此宣称所有业务接口已获访问保护。

如需数字人动画，将原项目的 digital-human-assistant.gif 放入 vue-project_all/public/hud-assets/ 后再启动或构建前端。文件缺失时，可通过首页的“数字人讲解”按钮打开讲解面板。
