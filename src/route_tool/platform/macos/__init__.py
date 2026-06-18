"""macOS 平台后端实现。

已知限制（首版）：
- 路由持久化需 sudo，且 macOS 无 -p 等价物；首版只做临时路由，重启失效
- 权限检测用 os.geteuid()，非 root 时需 sudo 运行
"""
