from unittest.mock import patch

from route_tool.core.contracts import PlatformBackend
from route_tool.core.models import ResultLevel, Result, RouteInfo, PingResult, NetworkInfo
from route_tool.platform.windows.backend import WindowsBackend


ROUTE = RouteInfo(network="192.168.0.0", mask="255.255.252.0", gateway="192.168.5.22")


def test_windows_backend_satisfies_protocol():
    backend = WindowsBackend()
    # runtime_checkable Protocol 可用 isinstance 检查
    assert isinstance(backend, PlatformBackend)


def test_backend_add_route_delegates_to_routes_module():
    fake_result = Result(level=ResultLevel.SUCCESS, message="ok")
    with patch("route_tool.platform.windows.backend._add_route", return_value=fake_result) as mock_add:
        backend = WindowsBackend()
        result = backend.add_route(ROUTE)
    assert result is fake_result
    mock_add.assert_called_once_with(ROUTE)


def test_backend_route_exists_delegates():
    with patch("route_tool.platform.windows.backend._route_exists", return_value=True) as mock_exists:
        backend = WindowsBackend()
        assert backend.route_exists(ROUTE) is True
    mock_exists.assert_called_once_with(ROUTE)


def test_backend_remove_route_delegates():
    fake_result = Result(level=ResultLevel.SUCCESS, message="ok")
    with patch("route_tool.platform.windows.backend._remove_route", return_value=fake_result) as mock_del:
        backend = WindowsBackend()
        result = backend.remove_route(ROUTE)
    assert result is fake_result
    mock_del.assert_called_once_with(ROUTE)


def test_backend_ping_delegates():
    fake = PingResult(host="1.2.3.4", ok=True, message="ok")
    with patch("route_tool.platform.windows.backend._ping", return_value=fake) as mock_ping:
        backend = WindowsBackend()
        result = backend.ping("1.2.3.4", count=3)
    assert result is fake
    mock_ping.assert_called_once_with("1.2.3.4", 3)


def test_backend_is_admin_delegates():
    with patch("route_tool.platform.windows.backend.is_admin", return_value=True):
        backend = WindowsBackend()
        assert backend.is_admin() is True


def test_backend_get_network_info_combines_sources():
    """get_network_info 组合 WiFi SSID、本机 IP、5.22 ping 结果。"""
    fake_ping = PingResult(host="192.168.5.22", ok=True, message="可达", latency_ms=3.0)
    with patch("route_tool.platform.windows.backend._ping", return_value=fake_ping) as mock_ping, \
         patch("route_tool.platform.windows.backend._get_wifi_ssid", return_value="Corp-WiFi") as mock_wifi, \
         patch("route_tool.platform.windows.backend._get_local_ip", return_value="192.168.5.100") as mock_ip:
        info = WindowsBackend().get_network_info()
    assert info.wifi_name == "Corp-WiFi"
    assert info.local_ip == "192.168.5.100"
    assert info.gateway522_reachable is True
    assert "可达" in info.gateway522_message
    # ping 测的是网关 5.22
    mock_ping.assert_called_once()
    assert mock_ping.call_args[0][0] == "192.168.5.22"
    mock_wifi.assert_called_once()
    mock_ip.assert_called_once()


def test_backend_get_network_info_unreachable():
    """5.22 ping 不通时，gateway522_reachable=False，message 含失败原因。"""
    fake_ping = PingResult(host="192.168.5.22", ok=False, message="请求超时")
    with patch("route_tool.platform.windows.backend._ping", return_value=fake_ping), \
         patch("route_tool.platform.windows.backend._get_wifi_ssid", return_value="未连接"), \
         patch("route_tool.platform.windows.backend._get_local_ip", return_value="未知"):
        info = WindowsBackend().get_network_info()
    assert info.gateway522_reachable is False
    assert info.wifi_name == "未连接"
    assert info.local_ip == "未知"
    assert "超时" in info.gateway522_message or "不可达" in info.gateway522_message
