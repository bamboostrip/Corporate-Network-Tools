"""平台后端契约。

UI 层只依赖此 Protocol，从不直接 import 具体后端实现。
后期扩展（如 add_printer）时再向此 Protocol 添加方法。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from route_tool.core.models import PingResult, Result, RouteInfo


@runtime_checkable
class PlatformBackend(Protocol):
    """平台后端契约。所有平台实现必须满足此接口。"""

    def is_admin(self) -> bool:
        """当前进程是否有管理员/root 权限。"""
        ...

    def route_exists(self, route: RouteInfo) -> bool:
        """检查路由是否已配置。"""
        ...

    def add_route(self, route: RouteInfo) -> Result:
        """添加路由（持久化）。"""
        ...

    def remove_route(self, route: RouteInfo) -> Result:
        """删除路由。"""
        ...

    def ping(self, host: str, count: int = 2) -> PingResult:
        """测试主机连通性。"""
        ...
