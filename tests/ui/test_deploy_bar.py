"""DeployBar 测试：静态检查 + 按钮状态纯逻辑。"""
import inspect

from route_tool.ui.widgets.deploy_bar import DeployBar


def test_deploy_bar_has_async_methods():
    assert hasattr(DeployBar, "deploy_async")
    assert hasattr(DeployBar, "_on_deploy_done")


def test_deploy_bar_callbacks_signature():
    sig = inspect.signature(DeployBar.__init__)
    params = sig.parameters
    assert "on_deploy" in params   # 后台执行编排的回调
    assert "on_log" in params
    assert "on_progress" in params  # 进度回调（更新按钮文字）


def test_deploy_bar_button_states():
    """按钮有三种状态文字：待机/部署中/完成。通过 set_state 切换。"""
    # 静态方法验证状态常量存在
    assert hasattr(DeployBar, "STATE_IDLE")
    assert hasattr(DeployBar, "STATE_DEPLOYING")
    assert hasattr(DeployBar, "STATE_DONE")
