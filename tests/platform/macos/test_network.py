"""macOS networksetup 解析 WiFi SSID 的测试。"""
from unittest.mock import patch, MagicMock

from route_tool.platform.macos.network import parse_ssid, get_wifi_ssid


# === parse_ssid：纯解析逻辑 ===

def test_parse_ssid_success():
    """networksetup -getairportnetwork 输出 'Current Wi-Fi Network: <SSID>'。"""
    output = "Current Wi-Fi Network: Corp-WiFi\n"
    assert parse_ssid(output) == "Corp-WiFi"


def test_parse_sssid_with_locale_chinese_macos():
    """中文 macOS 输出 '当前 Wi-Fi 网络: <SSID>'。"""
    output = "当前 Wi-Fi 网络: 办公无线\n"
    assert parse_ssid(output) == "办公无线"


def test_parse_ssid_returns_empty_when_not_connected():
    """未连接 WiFi 时输出 '** Not associated'，返回空串。"""
    # 不同版本输出略有差异，但都不是 "Network: xxx" 形式
    assert parse_ssid("You are not associated with an AirPort network.\n") == ""
    assert parse_ssid("** Not associated\n") == ""


def test_parse_ssid_empty_output():
    assert parse_ssid("") == ""


# === get_wifi_ssid：封装 subprocess ===

def test_get_wifi_ssid_calls_networksetup():
    """调用 networksetup -getairportnetwork。"""
    mock_proc = MagicMock(returncode=0, stdout="Current Wi-Fi Network: OfficeNet\n", stderr="")
    with patch("route_tool.platform.macos.network.subprocess.run", return_value=mock_proc) as mock_run:
        ssid = get_wifi_ssid()
    assert ssid == "OfficeNet"
    args = mock_run.call_args[0][0]
    assert "networksetup" in args
    assert "-getairportnetwork" in args


def test_get_wifi_ssid_returns_unconnected_when_not_associated():
    """未连接时返回 '未连接'。"""
    mock_proc = MagicMock(returncode=0, stdout="** Not associated\n", stderr="")
    with patch("route_tool.platform.macos.network.subprocess.run", return_value=mock_proc):
        assert get_wifi_ssid() == "未连接"


def test_get_wifi_ssid_returns_unconnected_on_error():
    """命令失败（如无 WiFi 模块）返回 '未连接'，不抛异常。"""
    with patch("route_tool.platform.macos.network.subprocess.run", side_effect=OSError("command not found")):
        assert get_wifi_ssid() == "未连接"
