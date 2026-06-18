"""Windows 管理员权限检测。

UAC 提权由 PyInstaller 的 --uac-admin manifest 负责（双击即弹 UAC）。
此模块只做检测，不做重启逻辑。
"""
from __future__ import annotations

import ctypes


def is_admin() -> bool:
    """检测当前进程是否以管理员身份运行。"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False
