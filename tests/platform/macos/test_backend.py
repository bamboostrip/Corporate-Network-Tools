from unittest.mock import patch, MagicMock

import pytest

from route_tool.core.contracts import PlatformBackend
from route_tool.core.models import NetworkInfo, PingResult, ResultLevel, RouteInfo
from route_tool.platform.macos.backend import MacBackend


ROUTE = RouteInfo(network="192.168.0.0", mask="255.255.252.0", gateway="192.168.5.22")

# geteuid 是 Unix 专有 API，Windows 的 os 模块没有该属性
_HAS_GETEUID = hasattr(__import__("os"), "geteuid")


def test_mac_backend_satisfies_protocol():
    assert isinstance(MacBackend(), PlatformBackend)


@pytest.mark.skipif(not _HAS_GETEUID, reason="geteuid 是 Unix 专有，Windows 上无此属性")
def test_is_admin_true_when_euid_zero():
    with patch("route_tool.platform.macos.backend.os.geteuid", return_value=0):
        assert MacBackend().is_admin() is True


@pytest.mark.skipif(not _HAS_GETEUID, reason="geteuid 是 Unix 专有，Windows 上无此属性")
def test_is_admin_false_when_euid_nonzero():
    with patch("route_tool.platform.macos.backend.os.geteuid", return_value=501):
        assert MacBackend().is_admin() is False


def test_is_admin_returns_false_when_no_geteuid():
    """Windows 上没有 geteuid，is_admin 应返回 False（靠 except AttributeError 兜底）。"""
    if _HAS_GETEUID:
        pytest.skip("此测试验证 Windows 行为，仅在没有 geteuid 的平台运行")
    assert MacBackend().is_admin() is False


def test_add_route_success():
    mock_proc = MagicMock(returncode=0, stdout="add net", stderr="")
    with patch("route_tool.platform.macos.backend.subprocess.run", return_value=mock_proc) as mock_run:
        result = MacBackend().add_route(ROUTE)
    assert result.level == ResultLevel.SUCCESS
    args = mock_run.call_args[0][0]
    # macOS: sudo route -n add -net 192.168.0.0/22 192.168.5.22
    assert "route" in args
    assert "add" in args
    assert "-net" in args
    assert "192.168.0.0/22" in args  # macOS 用 CIDR
    assert "192.168.5.22" in args


def test_route_exists_uses_netstat():
    mock_proc = MagicMock(returncode=0, stdout="192.168.0.0/22    192.168.5.22    UG", stderr="")
    with patch("route_tool.platform.macos.backend.subprocess.run", return_value=mock_proc) as mock_run:
        assert MacBackend().route_exists(ROUTE) is True
    args = mock_run.call_args[0][0]
    assert "netstat" in args
    assert "-rn" in args


def test_route_exists_absent():
    mock_proc = MagicMock(returncode=0, stdout="default    192.168.5.1", stderr="")
    with patch("route_tool.platform.macos.backend.subprocess.run", return_value=mock_proc):
        assert MacBackend().route_exists(ROUTE) is False


def test_ping_success():
    mock_proc = MagicMock(returncode=0, stdout="64 bytes from 192.168.0.210: icmp_seq=0 ttl=64 time=10.5 ms", stderr="")
    with patch("route_tool.platform.macos.backend.subprocess.run", return_value=mock_proc):
        result = MacBackend().ping("192.168.0.210", count=2)
    assert result.ok is True


def test_ping_failure():
    mock_proc = MagicMock(returncode=2, stdout="Request timeout", stderr="")
    with patch("route_tool.platform.macos.backend.subprocess.run", return_value=mock_proc):
        result = MacBackend().ping("192.168.0.248", count=2)
    assert result.ok is False


def test_backend_get_network_info_combines_sources():
    """get_network_info 组合 WiFi SSID、本机 IP、5.22 ping 结果。"""
    fake_ping = PingResult(host="192.168.5.22", ok=True, message="可达", latency_ms=3.0)
    with patch.object(MacBackend, "ping", return_value=fake_ping) as mock_ping, \
         patch("route_tool.platform.macos.backend._get_wifi_ssid", return_value="OfficeNet") as mock_wifi, \
         patch("route_tool.platform.macos.backend._get_local_ip", return_value="192.168.5.100") as mock_ip:
        info = MacBackend().get_network_info()
    assert info.wifi_name == "OfficeNet"
    assert info.local_ip == "192.168.5.100"
    assert info.gateway522_reachable is True
    assert "可达" in info.gateway522_message
    # ping 测的是网关 5.22
    mock_ping.assert_called_once()
    assert mock_ping.call_args[0][0] == "192.168.5.22"
    mock_wifi.assert_called_once()
    mock_ip.assert_called_once()


def test_backend_get_network_info_unreachable():
    """5.22 ping 不通时，gateway522_reachable=False。"""
    fake_ping = PingResult(host="192.168.5.22", ok=False, message="不可达")
    with patch.object(MacBackend, "ping", return_value=fake_ping), \
         patch("route_tool.platform.macos.backend._get_wifi_ssid", return_value="未连接"), \
         patch("route_tool.platform.macos.backend._get_local_ip", return_value="未知"):
        info = MacBackend().get_network_info()
    assert info.gateway522_reachable is False
    assert info.wifi_name == "未连接"
    assert info.local_ip == "未知"


def test_backend_printer_exists_delegates():
    from route_tool.core.models import PrinterTarget
    target = PrinterTarget(name="大打印机", description="x", ip="1.2.3.4", driver_label="big")
    with patch("route_tool.platform.macos.backend._printer_exists", return_value=True) as mock:
        assert MacBackend().printer_exists(target) is True
    mock.assert_called_once_with(target)


def test_backend_add_printer_delegates():
    from route_tool.core.models import PrinterTarget, PrinterInstallResult
    target = PrinterTarget(name="大打印机", description="x", ip="1.2.3.4", driver_label="big")
    fake = PrinterInstallResult(printer_name="大打印机", ok=True, message="ok")
    with patch("route_tool.platform.macos.backend._add_printer", return_value=fake) as mock:
        result = MacBackend().add_printer(target)
    assert result is fake
    mock.assert_called_once_with(target)


def test_backend_add_scan_share_unsupported_on_macos():
    """macOS 暂不支持扫描共享网络位置，应返回失败提示。"""
    result = MacBackend().add_scan_share()
    assert result.ok is False
    assert "macOS" in result.message or "不支持" in result.message
