"""Windows netsh wlan 解析 WiFi SSID 的测试。"""
from unittest.mock import patch, MagicMock

from route_tool.platform.windows.network import parse_ssid, get_wifi_ssid


# === parse_ssid：纯解析逻辑 ===

def test_parse_ssid_chinese_system():
    """中文 Windows 的 netsh 输出：SSID 关键字仍是英文，后跟中文的描述行。"""
    # 真实中文系统输出（GBK 解码后）：SSID 行始终用英文关键字 "SSID"
    output = (
        "\n系统上有 1 个接口: \n"
        "\n    名称                   : WLAN\n"
        "    描述            : RZ608 Wi-Fi 6E 80MHz\n"
        "    GUID                   : e407e619-879f-478c-8f4e-b7bd1229c02c\n"
        "    物理地址       : 4c:d5:77:08:66:9b\n"
        "    状态                  : 已连接\n"
        "    SSID                   : Corp-WiFi\n"
        "    AP BSSID               : c6:70:ab:86:e8:4a\n"
        "    波型                   : 5 GHz\n"
        "    配置文件               : Corp-WiFi\n"
    )
    assert parse_ssid(output) == "Corp-WiFi"


def test_parse_ssid_english_system():
    """英文 Windows 的 netsh 输出。"""
    output = (
        "There is 1 interface on the system:\n"
        "\n"
        "    Name                   : Wireless Network Connection\n"
        "    State                  : connected\n"
        "    SSID                   : OfficeNet\n"
    )
    assert parse_ssid(output) == "OfficeNet"


def test_parse_ssid_returns_empty_when_disconnected():
    """未连接时 SSID 行为空，返回空字符串。"""
    output = (
        "    State                  : disconnected\n"
        "    SSID                   :\n"
    )
    assert parse_ssid(output) == ""


def test_parse_ssid_returns_empty_when_no_ssid_line():
    """没有 SSID 行（如无无线网卡）返回空字符串。"""
    output = "接口名称 : 以太网\n状态 : 已连接\n"
    assert parse_ssid(output) == ""


def test_parse_ssid_empty_output():
    assert parse_ssid("") == ""


# === get_wifi_ssid：封装 subprocess ===

def test_get_wifi_ssid_calls_netsh_and_parses():
    """调用 netsh wlan show interfaces 并解析。"""
    mock_result = MagicMock()
    mock_result.stdout = "    SSID                   : Corp-WiFi\n"
    mock_result.returncode = 0
    with patch("route_tool.platform.windows.network.subprocess.run", return_value=mock_result) as mock_run:
        ssid = get_wifi_ssid()
    assert ssid == "Corp-WiFi"
    args = mock_run.call_args[0][0]
    assert "netsh" in args
    assert "wlan" in args
    assert "show" in args
    assert "interfaces" in args


def test_get_wifi_ssid_uses_gbk_encoding():
    """netsh 输出是 GBK，必须指定 encoding。"""
    mock_result = MagicMock()
    mock_result.stdout = "    SSID                   : X\n"
    mock_result.returncode = 0
    with patch("route_tool.platform.windows.network.subprocess.run", return_value=mock_result) as mock_run:
        get_wifi_ssid()
    kwargs = mock_run.call_args[1]
    assert kwargs.get("encoding") == "gbk"


def test_get_wifi_ssid_returns_unconnected_on_empty():
    """解析结果为空时（未连接/无网卡），返回 '未连接'。"""
    mock_result = MagicMock()
    mock_result.stdout = "    State : disconnected\n"
    mock_result.returncode = 0
    with patch("route_tool.platform.windows.network.subprocess.run", return_value=mock_result):
        assert get_wifi_ssid() == "未连接"


def test_get_wifi_ssid_returns_unconnected_on_subprocess_error():
    """netsh 执行失败时返回 '未连接'，不抛异常。"""
    with patch("route_tool.platform.windows.network.subprocess.run", side_effect=OSError("找不到 netsh")):
        assert get_wifi_ssid() == "未连接"


def test_get_wifi_ssid_hides_console_window():
    """GUI 程序调 netsh 不能弹黑窗口，必须注入 no_window_kwargs。"""
    mock_result = MagicMock()
    mock_result.stdout = "    SSID : X\n"
    mock_result.returncode = 0
    with patch("route_tool.platform.windows.network.subprocess.run", return_value=mock_result) as mock_run:
        get_wifi_ssid()
    kwargs = mock_run.call_args[1]
    # Windows 平台下应包含 creationflags 或 startupinfo
    import sys
    if sys.platform == "win32":
        assert "creationflags" in kwargs or "startupinfo" in kwargs
