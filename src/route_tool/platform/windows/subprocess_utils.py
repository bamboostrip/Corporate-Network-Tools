"""Windows subprocess 工具：隐藏子进程控制台窗口。

背景：本程序是 PyInstaller 打包的 GUI（无 console 子系统），
调用 ping/route/netsh 等系统命令时，Windows 会为每个子进程
闪现一个黑色控制台窗口，影响体验。

解决：在 win32 下给 subprocess.run 注入
- creationflags=CREATE_NO_WINDOW：不创建控制台
- startupinfo（STARTF_USESHOWWINDOW）：双保险隐藏窗口

用法：
    subprocess.run(cmd, ..., **no_window_kwargs())

非 Windows 平台返回空 dict，调用方无需关心平台差异。
"""
from __future__ import annotations

import subprocess
import sys


def no_window_kwargs() -> dict:
    """返回用于隐藏子进程控制台的 subprocess kwargs。

    Windows 平台：返回 {creationflags, startupinfo}。
    其他平台：返回 {}（无副作用）。
    """
    if sys.platform != "win32":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {
        "creationflags": subprocess.CREATE_NO_WINDOW,
        "startupinfo": startupinfo,
    }
