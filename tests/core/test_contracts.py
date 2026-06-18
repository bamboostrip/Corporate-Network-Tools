"""验证 Protocol 结构（防止后期改动破坏接口）。"""
import inspect

from route_tool.core.contracts import PlatformBackend
from route_tool.core.errors import UnsupportedOSError


def test_unsupported_os_error_message():
    err = UnsupportedOSError("Linux")
    assert "Linux" in str(err)
    assert "IT" in str(err)


def test_protocol_has_required_methods():
    # 验证 Protocol 声明了所有必要方法
    required = {"is_admin", "route_exists", "add_route", "remove_route", "ping"}
    members = {
        name for name, _ in inspect.getmembers(
            PlatformBackend, predicate=lambda x: True
        )
    }
    for method in required:
        assert method in members, f"Protocol 缺少方法: {method}"


def test_unsupported_os_error_has_system_attr():
    err = UnsupportedOSError("FreeBSD")
    assert err.system == "FreeBSD"
