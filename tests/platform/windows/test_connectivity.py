from unittest.mock import patch, MagicMock

from route_tool.platform.windows.connectivity import parse_ping_result, ping


def test_parse_ping_success():
    """Windows ping 成功的典型输出（GBK 解码后）。"""
    output = (
        "\n正在 Ping 192.168.0.210 具有 32 字节的数据:\n"
        "来自 192.168.0.210 的回复: 字节=32 时间=12ms TTL=64\n"
        "来自 192.168.0.210 的回复: 字节=32 时间=13ms TTL=64\n"
        "\n192.168.0.210 的 Ping 统计信息:\n"
        "    数据包: 已发送 = 2，已接收 = 2，丢失 = 0 (0% 丢失)，\n"
        "往返行程的估计时间(以毫秒为单位):\n"
        "    最短 = 12ms，最长 = 13ms，平均 = 12ms\n"
    )
    result = parse_ping_result("192.168.0.210", output)
    assert result.ok is True
    assert result.host == "192.168.0.210"
    assert "2" in result.message  # 2/2 包


def test_parse_ping_failure():
    """Windows ping 失败的典型输出。"""
    output = (
        "\n正在 Ping 192.168.0.248 具有 32 字节的数据:\n"
        "请求超时。\n"
        "请求超时。\n"
        "\n192.168.0.248 的 Ping 统计信息:\n"
        "    数据包: 已发送 = 2，已接收 = 0，丢失 = 2 (100% 丢失)，\n"
    )
    result = parse_ping_result("192.168.0.248", output)
    assert result.ok is False
    assert "192.168.0.248" in result.message


def test_parse_ping_host_unreachable():
    output = "PING: 传输失败。General failure.\n"
    result = parse_ping_result("192.168.0.99", output)
    assert result.ok is False


def test_parse_ping_empty_output():
    result = parse_ping_result("1.2.3.4", "")
    assert result.ok is False


def test_parse_ping_latency_extraction():
    """能从输出中提取延迟数值。"""
    output = (
        "来自 192.168.0.210 的回复: 字节=32 时间=15ms TTL=64\n"
        "来自 192.168.0.210 的回复: 字节=32 时间=17ms TTL=64\n"
        "    最短 = 15ms，最长 = 17ms，平均 = 16ms\n"
    )
    result = parse_ping_result("192.168.0.210", output)
    assert result.ok is True
    assert result.latency_ms == 16.0  # 平均值


def test_ping_calls_subprocess_with_correct_args():
    mock_result = MagicMock()
    mock_result.stdout = (
        "来自 192.168.0.210 的回复: 字节=32 时间=10ms TTL=64\n"
        "    数据包: 已发送 = 2，已接收 = 2，丢失 = 0 (0% 丢失)，\n"
    )
    mock_result.returncode = 0
    with patch("route_tool.platform.windows.connectivity.subprocess.run", return_value=mock_result) as mock_run:
        result = ping("192.168.0.210", count=2)
    assert result.ok is True
    args = mock_run.call_args[0][0]
    assert "ping" in args
    assert "192.168.0.210" in args
    assert "-n" in args
    assert "2" in args  # count


def test_ping_handles_timeout_exception():
    import subprocess as sp
    with patch(
        "route_tool.platform.windows.connectivity.subprocess.run",
        side_effect=sp.TimeoutExpired(cmd="ping", timeout=10),
    ):
        result = ping("192.168.0.210", count=2)
    assert result.ok is False
    assert "超时" in result.message or "timeout" in result.message.lower()


def test_ping_hides_console_window():
    """ping 不能弹黑窗口：subprocess 调用必须注入隐藏控制台的 kwargs。"""
    import sys
    if sys.platform != "win32":
        import pytest
        pytest.skip("仅验证 Windows 隐藏窗口行为")
    mock_result = MagicMock()
    mock_result.stdout = "来自 192.168.0.210 的回复: 字节=32 时间=10ms TTL=64\n"
    mock_result.returncode = 0
    with patch("route_tool.platform.windows.connectivity.subprocess.run", return_value=mock_result) as mock_run:
        ping("192.168.0.210", count=2)
    kwargs = mock_run.call_args[1]
    assert "creationflags" in kwargs or "startupinfo" in kwargs
