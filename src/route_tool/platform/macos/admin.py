"""macOS 管理员权限执行工具。

问题：subprocess 直接调 sudo 会卡死（sudo 要在终端读密码，但 GUI 程序无终端）。

解决：用 osascript 的 'do shell script ... with administrator privileges'。
macOS 会弹出系统授权对话框（类似 Windows UAC），用户输密码后命令以 root 执行。
若用户取消，osascript 返回非 0 退出码（不会卡死）。
"""
from __future__ import annotations

import subprocess


def run_with_admin(command: str) -> subprocess.CompletedProcess:
    """以管理员权限执行 shell 命令（弹出系统授权对话框）。

    command: 完整的 shell 命令字符串（如 "route -n add -net 192.168.0.0/22 192.168.5.22"）
    返回: CompletedProcess，returncode 非 0 表示失败（用户拒绝/命令错误）

    注意：command 内的双引号会被转义，避免破坏 AppleScript 语法。
    """
    # 转义 command 里的双引号（AppleScript 用双引号定界字符串）
    escaped = command.replace("\\", "\\\\").replace('"', '\\"')
    apple_script = f'do shell script "{escaped}" with administrator privileges'
    return subprocess.run(
        ["osascript", "-e", apple_script],
        capture_output=True,
        text=True,
        timeout=120,  # 授权对话框可能等用户输入，给足时间
    )
