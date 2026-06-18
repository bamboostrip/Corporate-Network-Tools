"""Windows subprocess 隐藏控制台封装的测试。

解决痛点：PyInstaller 打包的 GUI 程序（无 console）调用 subprocess 时，
ping/route 等命令会闪现一个黑色控制台窗口，体验差。
封装在 win32 下注入 CREATE_NO_WINDOW + STARTF_USESHOWWINDOW。
"""
import subprocess
import sys
from unittest.mock import patch

import pytest

from route_tool.platform.windows.subprocess_utils import no_window_kwargs


def test_no_window_kwargs_on_win32():
    """Windows 下返回的 kwargs 应含隐藏控制台的标志。"""
    with patch.object(sys, "platform", "win32"):
        kwargs = no_window_kwargs()
    assert kwargs.get("creationflags") == subprocess.CREATE_NO_WINDOW
    si = kwargs.get("startupinfo")
    assert isinstance(si, subprocess.STARTUPINFO)
    # 确实设置了"使用显示窗口标志"
    assert si.dwFlags & subprocess.STARTF_USESHOWWINDOW


def test_no_window_kwargs_on_non_win32():
    """非 Windows 平台返回空 dict，不注入任何标志。"""
    with patch.object(sys, "platform", "darwin"):
        assert no_window_kwargs() == {}
    with patch.object(sys, "platform", "linux"):
        assert no_window_kwargs() == {}


def test_no_window_kwargs_mergeable():
    """返回的 dict 能正常解包进 subprocess.run（不与 encoding 等参数冲突）。"""
    with patch.object(sys, "platform", "win32"):
        kwargs = no_window_kwargs()
    # 模拟调用方典型用法：subprocess.run(cmd, text=True, encoding='gbk', **kwargs)
    # 这里只验证键集合不含 text/encoding 等会冲突的键
    assert "text" not in kwargs
    assert "encoding" not in kwargs
    assert "capture_output" not in kwargs


@pytest.mark.skipif(sys.platform != "win32", reason="仅 Windows 验证真实常量")
def test_constants_available_on_real_win32():
    """真实 Windows 环境下常量确实存在（防止拼写错误）。"""
    kwargs = no_window_kwargs()
    assert "creationflags" in kwargs
    assert "startupinfo" in kwargs
