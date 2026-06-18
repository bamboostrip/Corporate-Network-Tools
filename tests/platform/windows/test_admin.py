from unittest.mock import patch, MagicMock

from route_tool.platform.windows.admin import is_admin


def test_is_admin_true_when_windll_returns_nonzero():
    mock_ctypes = MagicMock()
    mock_ctypes.windll.shell32.IsUserAnAdmin.return_value = 1
    with patch("route_tool.platform.windows.admin.ctypes", mock_ctypes):
        assert is_admin() is True


def test_is_admin_false_when_windll_returns_zero():
    mock_ctypes = MagicMock()
    mock_ctypes.windll.shell32.IsUserAnAdmin.return_value = 0
    with patch("route_tool.platform.windows.admin.ctypes", mock_ctypes):
        assert is_admin() is False


def test_is_admin_false_on_exception():
    mock_ctypes = MagicMock()
    mock_ctypes.windll.shell32.IsUserAnAdmin.side_effect = Exception("no windll")
    with patch("route_tool.platform.windows.admin.ctypes", mock_ctypes):
        assert is_admin() is False
