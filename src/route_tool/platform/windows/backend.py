"""Windows 平台后端：组合 routes/connectivity/admin 模块。"""
from __future__ import annotations

from route_tool.core.models import PingResult, Result, RouteInfo
from route_tool.platform.windows.admin import is_admin
from route_tool.platform.windows.connectivity import ping as _ping
from route_tool.platform.windows.routes import (
    add_route as _add_route,
    remove_route as _remove_route,
    route_exists as _route_exists,
)


class WindowsBackend:
    """Windows 平台的 PlatformBackend 实现。"""

    def is_admin(self) -> bool:
        return is_admin()

    def route_exists(self, route: RouteInfo) -> bool:
        return _route_exists(route)

    def add_route(self, route: RouteInfo) -> Result:
        return _add_route(route)

    def remove_route(self, route: RouteInfo) -> Result:
        return _remove_route(route)

    def ping(self, host: str, count: int = 2) -> PingResult:
        return _ping(host, count)
