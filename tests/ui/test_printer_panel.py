"""PrinterPanel 测试：静态检查 + 按钮启用规则纯逻辑。"""
import inspect

from route_tool.core.models import PrinterTarget
from route_tool.ui.widgets.printer_panel import PrinterPanel


BIG = PrinterTarget(name="大打印机", description="SHARP MX-M905C", ip="1.2.3.4", driver_label="big")


def test_printer_panel_has_async_methods():
    assert hasattr(PrinterPanel, "add_printer_async")
    assert hasattr(PrinterPanel, "_on_add_done")


def test_printer_panel_callbacks_signature():
    sig = inspect.signature(PrinterPanel.__init__)
    params = sig.parameters
    assert "on_add_printer" in params
    assert "on_check_printer" in params
    assert "on_log" in params
    assert "gateway_reachable" in params  # 接收网络可达性状态


def test_can_add_printer_true_when_gateway_reachable():
    """5.22 可达时允许添加。"""
    assert PrinterPanel.can_add_printer(gateway_reachable=True) is True


def test_can_add_printer_false_when_gateway_unreachable():
    """5.22 不可达时禁止添加（跨网段路由未配，9100 一定不通）。"""
    assert PrinterPanel.can_add_printer(gateway_reachable=False) is False
