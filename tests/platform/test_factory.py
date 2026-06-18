from unittest.mock import patch

import pytest

from route_tool.core.errors import UnsupportedOSError
from route_tool.platform import get_backend


def test_factory_unsupported_os():
    with patch("route_tool.platform._platform.system", return_value="Linux"):
        with pytest.raises(UnsupportedOSError) as exc_info:
            get_backend()
    assert "Linux" in str(exc_info.value)


def test_factory_windows_routes_to_windows_backend():
    # 只验证 import 路径正确，不真正实例化（实例化需要 windows 模块存在）
    # 此测试在 Task 6 完成 WindowsBackend 后会真正通过
    with patch("route_tool.platform._platform.system", return_value="Windows"):
        try:
            backend = get_backend()
            from route_tool.platform.windows.backend import WindowsBackend
            assert isinstance(backend, WindowsBackend)
        except ImportError:
            pytest.skip("WindowsBackend 尚未实现（Task 6 完成）")


def test_factory_macos_routes_to_mac_backend():
    with patch("route_tool.platform._platform.system", return_value="Darwin"):
        try:
            backend = get_backend()
            from route_tool.platform.macos.backend import MacBackend
            assert isinstance(backend, MacBackend)
        except ImportError:
            pytest.skip("MacBackend 尚未实现（Task 10 完成）")
