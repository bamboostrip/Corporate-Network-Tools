"""UI 线程安全性验证。

CustomTkinter/tkinter 的完整 GUI 测试成本高且收益低，
这里只做静态验证：确认所有 panel 类可导入、关键方法存在、回调签名正确。
真正的线程安全（after 调度）靠代码审查 + 手动冒烟测试保证。
"""
import inspect

from route_tool.ui.widgets.route_panel import RoutePanel
from route_tool.ui.widgets.test_panel import TestPanel, _DeviceRow
from route_tool.ui.widgets.log_panel import LogPanel
from route_tool.ui.widgets.printer_panel import PrinterPanel


def test_route_panel_has_async_methods():
    """RoutePanel 必须有后台线程入口和主线程回调方法。"""
    assert hasattr(RoutePanel, "check_route_async")
    assert hasattr(RoutePanel, "check_prerequisite_async")
    assert hasattr(RoutePanel, "_update_route_status")
    assert hasattr(RoutePanel, "_on_config_done")


def test_printer_panel_has_async_methods():
    """PrinterPanel 必须有后台添加入口和主线程回调。"""
    assert hasattr(PrinterPanel, "add_printer_async")
    assert hasattr(PrinterPanel, "_on_add_done")


def test_test_panel_has_async_methods():
    """TestPanel 必须有后台测试入口和主线程结果回调。"""
    assert hasattr(TestPanel, "_test_single")
    assert hasattr(TestPanel, "_on_ping_done")
    assert hasattr(TestPanel, "_test_all")


def test_device_row_has_state_methods():
    """_DeviceRow 必须有 set_testing/set_result（主线程调用）。"""
    assert hasattr(_DeviceRow, "set_testing")
    assert hasattr(_DeviceRow, "set_result")


def test_log_panel_has_append():
    """LogPanel 必须有 append(message, level) 方法。"""
    assert hasattr(LogPanel, "append")
    sig = inspect.signature(LogPanel.append)
    params = list(sig.parameters.keys())
    assert "message" in params
    assert "level" in params


def test_route_panel_callbacks_signature():
    """RoutePanel 构造函数要求三个回调注入。"""
    sig = inspect.signature(RoutePanel.__init__)
    params = sig.parameters
    assert "on_check_route" in params
    assert "on_add_route" in params
    assert "on_log" in params


def test_test_panel_callbacks_signature():
    """TestPanel 构造函数要求两个回调注入。"""
    sig = inspect.signature(TestPanel.__init__)
    params = sig.parameters
    assert "on_ping" in params
    assert "on_log" in params
