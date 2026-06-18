"""Windows 平台后端：组合 routes/connectivity/admin/network 模块。"""
from __future__ import annotations

from route_tool.core.config import GATEWAY, PING_COUNT
from route_tool.core.models import NetworkInfo, PingResult, Result, RouteInfo
from route_tool.core.network_util import get_local_ip as _get_local_ip
from route_tool.platform.windows.admin import is_admin
from route_tool.platform.windows.connectivity import ping as _ping
from route_tool.platform.windows.network import get_wifi_ssid as _get_wifi_ssid
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

    def get_network_info(self) -> NetworkInfo:
        """查询当前网络环境：WiFi 名、本机 IP、网关 5.22 可达性。

        5.22 不可达时 UI 禁用配置按钮，所以这里要稳定返回结果，
        任一子项失败都不应抛异常（各模块内部已兜底）。
        """
        result = _ping(GATEWAY, PING_COUNT)
        return NetworkInfo(
            wifi_name=_get_wifi_ssid(),
            local_ip=_get_local_ip(),
            gateway522_reachable=result.ok,
            gateway522_message=result.message,
        )
