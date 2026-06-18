"""RoutePanel 网络预检逻辑测试。

完整 GUI 测试成本高（需 Tk root + 事件循环），这里采用项目既有策略：
1. 静态检查：关键方法/回调签名存在（同 test_threading_safety.py 风格）
2. 纯逻辑测试：把"是否允许配置"的判断抽成静态方法 can_configure，
   不依赖 GUI 控件，可单独验证业务规则。
"""
import inspect

from route_tool.core.models import NetworkInfo
from route_tool.ui.widgets.route_panel import RoutePanel


def test_route_panel_has_prerequisite_methods():
    """RoutePanel 必须有网络预检相关方法。"""
    assert hasattr(RoutePanel, "check_prerequisite_async")
    assert hasattr(RoutePanel, "recheck_prerequisite")
    assert hasattr(RoutePanel, "_update_network_info")


def test_route_panel_accepts_network_info_callback():
    """构造函数新增 on_get_network_info 回调注入（同 backend 解耦）。"""
    sig = inspect.signature(RoutePanel.__init__)
    params = sig.parameters
    assert "on_get_network_info" in params
    assert "on_check_route" in params
    assert "on_add_route" in params
    assert "on_log" in params


# === can_configure：业务规则纯逻辑 ===

def test_can_configure_true_when_gateway_reachable_and_route_absent():
    """5.22 可达 + 路由未配置 → 允许配置。"""
    info = NetworkInfo(wifi_name="X", local_ip="1.2.3.4",
                       gateway522_reachable=True, gateway522_message="可达")
    assert RoutePanel.can_configure(info, route_exists=False) is True


def test_can_configure_false_when_gateway_unreachable():
    """5.22 不可达 → 无论路由状态都禁止配置。"""
    info = NetworkInfo(wifi_name="X", local_ip="1.2.3.4",
                       gateway522_reachable=False, gateway522_message="超时")
    assert RoutePanel.can_configure(info, route_exists=False) is False
    # 即使路由已配置，5.22 不通也不允许（虽然此时按钮本就该禁用）
    assert RoutePanel.can_configure(info, route_exists=True) is False


def test_can_configure_false_when_route_already_exists():
    """5.22 可达但路由已配置 → 无需重复配置，禁止。"""
    info = NetworkInfo(wifi_name="X", local_ip="1.2.3.4",
                       gateway522_reachable=True, gateway522_message="可达")
    assert RoutePanel.can_configure(info, route_exists=True) is False
