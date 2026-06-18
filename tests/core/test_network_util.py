"""core/network_util 平台无关网络工具的测试。"""
from unittest.mock import patch, MagicMock

from route_tool.core.network_util import get_local_ip


def test_get_local_ip_returns_sockname():
    """正常情况返回 UDP 探测选出的出口 IP。"""
    fake_sock = MagicMock()
    fake_sock.getsockname.return_value = ("192.168.5.100", 12345)
    with patch("route_tool.core.network_util.socket.socket", return_value=fake_sock):
        ip = get_local_ip()
    assert ip == "192.168.5.100"
    # 确实探测了 5.22（让 OS 选出口接口，不真正发包）
    fake_sock.connect.assert_called_once()
    connect_args = fake_sock.connect.call_args[0][0]
    assert "192.168.5.22" in connect_args


def test_get_local_ip_closes_socket():
    """无论成功与否都要关闭 socket。"""
    fake_sock = MagicMock()
    fake_sock.getsockname.return_value = ("10.0.0.5", 0)
    with patch("route_tool.core.network_util.socket.socket", return_value=fake_sock):
        get_local_ip()
    fake_sock.close.assert_called_once()


def test_get_local_ip_returns_unknown_on_error():
    """socket 连接失败时返回 '未知'，不抛异常。"""
    fake_sock = MagicMock()
    fake_sock.connect.side_effect = OSError("网络不可达")
    with patch("route_tool.core.network_util.socket.socket", return_value=fake_sock):
        ip = get_local_ip()
    assert ip == "未知"
    fake_sock.close.assert_called_once()


def test_get_local_ip_socket_creation_failure():
    """连 socket 都建不起来时也返回 '未知'。"""
    with patch("route_tool.core.network_util.socket.socket", side_effect=OSError("无可用网络")):
        assert get_local_ip() == "未知"
