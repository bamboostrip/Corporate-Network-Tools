"""平台抽象层工厂。

UI 层调用 get_backend() 获取当前系统的后端，无需关心具体实现。
"""
from __future__ import annotations

import platform as _platform

from route_tool.core.contracts import PlatformBackend
from route_tool.core.errors import UnsupportedOSError


def get_backend() -> PlatformBackend:
    """根据当前操作系统返回对应后端。

    Raises:
        UnsupportedOSError: 当前系统不在支持列表中。
    """
    system = _platform.system()
    if system == "Windows":
        from route_tool.platform.windows.backend import WindowsBackend
        return WindowsBackend()
    if system == "Darwin":
        from route_tool.platform.macos.backend import MacBackend
        return MacBackend()
    raise UnsupportedOSError(system)
