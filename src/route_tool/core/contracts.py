"""平台后端契约。

UI 层只依赖此 Protocol，从不直接 import 具体后端实现。
后期扩展（如 add_printer）时再向此 Protocol 添加方法。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from route_tool.core.models import (
    NetworkInfo,
    PingResult,
    PrinterInstallResult,
    PrinterTarget,
    Result,
    RouteInfo,
    ShareInstallResult,
)


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

    def get_network_info(self) -> NetworkInfo:
        """查询当前网络环境（WiFi 名、本机 IP、网关 5.22 可达性）。

        UI 据此决定是否允许配置路由：5.22 不可达时禁用配置按钮。
        """
        ...

    def printer_exists(self, target: PrinterTarget) -> bool:
        """检查打印机是否已添加到系统。"""
        ...

    def add_printer(self, target: PrinterTarget) -> PrinterInstallResult:
        """添加打印机到系统（静默安装驱动+端口+打印机）。

        幂等：已存在时直接返回成功。
        Windows 用 9100+驱动，macOS 用 IPP driverless 尝试。
        """
        ...

    def add_scan_share(self) -> ShareInstallResult:
        """添加扫描文件共享的网络位置（凭据 + 快捷方式）。

        幂等：已存在时覆盖不报错。
        Windows 用 cmdkey + Network Shortcuts，macOS 暂不支持。
        """
        ...

    def scan_share_exists(self) -> bool:
        """检查扫描文件共享网络位置是否已添加到系统。"""
        ...

