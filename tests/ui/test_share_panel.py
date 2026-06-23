"""SharePanel 测试：静态检查 + 按钮启用规则纯逻辑。"""
import inspect

from route_tool.ui.widgets.share_panel import SharePanel


def test_share_panel_has_async_methods():
    assert hasattr(SharePanel, "add_share_async")
    assert hasattr(SharePanel, "_on_add_done")


def test_share_panel_callbacks_signature():
    sig = inspect.signature(SharePanel.__init__)
    params = sig.parameters
    assert "on_add_share" in params
    assert "on_log" in params
    assert "gateway_reachable" in params


def test_can_add_share_true_when_gateway_reachable():
    """5.22 可达时允许添加。"""
    assert SharePanel.can_add_share(gateway_reachable=True) is True


def test_can_add_share_false_when_gateway_unreachable():
    """5.22 不可达时禁止添加（跨网段路由未配）。"""
    assert SharePanel.can_add_share(gateway_reachable=False) is False
