"""macOS 平台后端实现。

注意：macOS 路由用 CIDR 表示法（192.168.0.0/22），不是 Windows 的点分掩码。
掩码 255.255.252.0 = /22。
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from route_tool.core.config import GATEWAY, PING_COUNT, PING_TIMEOUT_SECONDS, SCAN_SHARE_PASSWORD, SCAN_SHARE_PATH, SCAN_SHARE_USER
from route_tool.core.models import NetworkInfo, PingResult, PrinterInstallResult, PrinterTarget, Result, ResultLevel, RouteInfo, ShareInstallResult
from route_tool.core.network_util import get_local_ip as _get_local_ip
from route_tool.platform.macos.network import get_wifi_ssid as _get_wifi_ssid
from route_tool.platform.macos.printers import (
    add_printer as _add_printer,
    printer_exists as _printer_exists,
)
from route_tool.platform.macos.shares import add_scan_share as _add_scan_share

# 255.255.252.0 -> 22（前缀长度），用二进制 1 的个数
_MASK_TO_PREFIX = {
    "255.255.255.255": 32, "255.255.255.254": 31, "255.255.255.252": 30,
    "255.255.255.248": 29, "255.255.255.240": 28, "255.255.255.224": 27,
    "255.255.255.192": 26, "255.255.255.128": 25, "255.255.255.0": 24,
    "255.255.254.0": 23, "255.255.252.0": 22, "255.255.248.0": 21,
    "255.255.240.0": 20, "255.255.224.0": 19, "255.255.192.0": 18,
    "255.255.128.0": 17, "255.255.0.0": 16, "255.0.0.0": 8, "0.0.0.0": 0,
}


def _mask_to_prefix(mask: str) -> int:
    return _MASK_TO_PREFIX.get(mask, 22)


def _run(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class MacBackend:
    """macOS 平台的 PlatformBackend 实现。"""

    def is_admin(self) -> bool:
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

    def route_exists(self, route: RouteInfo) -> bool:
        prefix = _mask_to_prefix(route.mask)
        cidr = f"{route.network}/{prefix}"
        try:
            proc = _run(["netstat", "-rn"])
            # 匹配 "192.168.0.0/22    192.168.5.22"
            pattern = re.compile(
                rf"\b{re.escape(cidr)}\s+{re.escape(route.gateway)}\b"
            )
            return pattern.search(proc.stdout) is not None
        except (subprocess.SubprocessError, OSError):
            return False

    def add_route(self, route: RouteInfo) -> Result:
        prefix = _mask_to_prefix(route.mask)
        cidr = f"{route.network}/{prefix}"
        cmd = ["sudo", "route", "-n", "add", "-net", cidr, route.gateway]
        try:
            proc = _run(cmd)
        except (subprocess.SubprocessError, OSError) as e:
            return Result(
                level=ResultLevel.FAILURE,
                message=f"执行 route 命令失败: {e}",
                error_code=-1,
            )
        if proc.returncode == 0:
            return Result(
                level=ResultLevel.SUCCESS,
                message="路由添加成功（临时，重启后失效）",
                raw_output=proc.stdout,
            )
        return Result(
            level=ResultLevel.FAILURE,
            message="路由添加失败（可能需要 sudo 权限）",
            raw_output=proc.stderr or proc.stdout,
            error_code=proc.returncode,
        )

    def remove_route(self, route: RouteInfo) -> Result:
        prefix = _mask_to_prefix(route.mask)
        cidr = f"{route.network}/{prefix}"
        cmd = ["sudo", "route", "-n", "delete", "-net", cidr]
        try:
            proc = _run(cmd)
        except (subprocess.SubprocessError, OSError) as e:
            return Result(
                level=ResultLevel.FAILURE,
                message=f"执行 route 命令失败: {e}",
                error_code=-1,
            )
        if proc.returncode == 0:
            return Result(level=ResultLevel.SUCCESS, message="路由删除成功")
        return Result(
            level=ResultLevel.FAILURE,
            message="路由删除失败",
            raw_output=proc.stderr or proc.stdout,
            error_code=proc.returncode,
        )

    def ping(self, host: str, count: int = 2) -> PingResult:
        cmd = ["ping", "-c", str(count), host]
        try:
            proc = _run(cmd, timeout=PING_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return PingResult(host=host, ok=False, message=f"{host} ping 超时")
        except (subprocess.SubprocessError, OSError) as e:
            return PingResult(host=host, ok=False, message=f"ping 执行失败: {e}")

        ok = proc.returncode == 0
        latency = None
        time_match = re.search(r"time=([\d.]+)\s*ms", proc.stdout)
        if time_match:
            latency = float(time_match.group(1))
        message = f"{host} 可达" if ok else f"{host} 不可达"
        return PingResult(
            host=host, ok=ok, message=message, raw_output=proc.stdout, latency_ms=latency
        )

    def get_network_info(self) -> NetworkInfo:
        """查询当前网络环境：WiFi 名、本机 IP、网关 5.22 可达性。"""
        result = self.ping(GATEWAY, PING_COUNT)
        return NetworkInfo(
            wifi_name=_get_wifi_ssid(),
            local_ip=_get_local_ip(),
            gateway522_reachable=result.ok,
            gateway522_message=result.message,
        )

    def printer_exists(self, target: PrinterTarget) -> bool:
        return _printer_exists(target)

    def add_printer(self, target: PrinterTarget) -> PrinterInstallResult:
        return _add_printer(target)

    def add_scan_share(self) -> ShareInstallResult:
        """添加扫描共享：Keychain 凭据 + Finder 别名（.app 快捷方式）。"""
        return _add_scan_share(
            share_path=SCAN_SHARE_PATH,
            user=SCAN_SHARE_USER,
            password=SCAN_SHARE_PASSWORD,
            display_name="SMY扫描",
        )

    def scan_share_exists(self) -> bool:
        """检查桌面是否有 SMY扫描.app。"""
        return (Path.home() / "Desktop" / "SMY扫描.app").exists()

