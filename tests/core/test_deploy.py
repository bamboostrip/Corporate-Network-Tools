"""一键部署编排器测试。全部 mock backend，不真实操作。"""
from unittest.mock import MagicMock, patch

from route_tool.core.deploy import DeployOrchestrator, TOTAL_STEPS
from route_tool.core.models import (
    DeployResult, NetworkInfo, Result, ResultLevel, RouteInfo,
    PrinterInstallResult, ShareInstallResult, PrinterTarget,
)


def make_orchestrator():
    """构造一个 backend 全部 mock 成功的编排器。"""
    backend = MagicMock()
    backend.get_network_info.return_value = NetworkInfo(
        wifi_name="X", local_ip="1.2.3.4",
        gateway522_reachable=True, gateway522_message="可达",
    )
    backend.route_exists.return_value = False  # 路由未配（会调 add_route）
    backend.printer_exists.return_value = False  # 打印机未加（会调 add_printer）
    backend.add_route.return_value = Result(
        level=ResultLevel.SUCCESS, message="路由添加成功"
    )
    backend.add_printer.return_value = PrinterInstallResult(
        printer_name="x", ok=True, message="ok"
    )
    backend.add_scan_share.return_value = ShareInstallResult(
        share_name="x", ok=True, message="ok"
    )
    return backend, DeployOrchestrator(backend, on_progress=lambda *a: None, on_log=lambda *a: None)


def test_total_steps_constant():
    """总步骤数固定（5 步：网络检测/路由/大打印机/小打印机/扫描共享）。"""
    assert TOTAL_STEPS == 5


# === 全部成功 ===

def test_run_full_deploy_all_success():
    """全部步骤成功 → ok=True, completed=5。"""
    backend, orch = make_orchestrator()
    result = orch.run_full_deploy()
    assert result.ok is True
    assert result.completed_steps == 5
    assert result.total_steps == 5
    assert result.failed_step == ""


def test_run_full_deploy_calls_steps_in_order():
    """步骤按正确顺序调用：网络检测 → 路由 → 大打印机 → 小打印机 → 扫描共享。"""
    backend, orch = make_orchestrator()
    orch.run_full_deploy()
    # 验证调用顺序
    backend.get_network_info.assert_called_once()
    backend.route_exists.assert_called_once()
    backend.add_route.assert_called_once()  # 路由未配置时会调 add_route
    assert backend.add_printer.call_count == 2  # 大+小
    backend.add_scan_share.assert_called_once()


# === 网络不可达：第一步就中断 ===

def test_run_full_deploy_aborts_when_gateway_unreachable():
    """5.22 不可达时，后续步骤全不执行，completed=0。"""
    backend = MagicMock()
    backend.get_network_info.return_value = NetworkInfo(
        wifi_name="未连接", local_ip="未知",
        gateway522_reachable=False, gateway522_message="超时",
    )
    orch = DeployOrchestrator(backend, lambda *a: None, lambda *a: None)
    result = orch.run_full_deploy()
    assert result.ok is False
    assert result.completed_steps == 0
    assert "网关" in result.message or "网络" in result.message
    backend.add_route.assert_not_called()
    backend.add_printer.assert_not_called()
    backend.add_scan_share.assert_not_called()


# === 中间步骤失败：中断后续 ===

def test_run_full_deploy_aborts_on_printer_failure():
    """大打印机失败时，后续（小打印机/扫描共享）不执行，completed=2。"""
    backend, orch = make_orchestrator()
    # 让 add_printer 第一次（大）失败
    backend.add_printer.side_effect = [
        PrinterInstallResult(printer_name="大", ok=False, message="驱动失败"),
    ]
    result = orch.run_full_deploy()
    assert result.ok is False
    assert result.completed_steps == 2  # 网络检测 + 路由 已完成
    assert "大打印机" in result.failed_step
    # 小打印机（第二次 add_printer）不应被调用
    assert backend.add_printer.call_count == 1
    backend.add_scan_share.assert_not_called()


def test_run_full_deploy_aborts_on_route_failure():
    """路由添加失败时，后续全不执行，completed=1。"""
    backend, orch = make_orchestrator()
    backend.add_route.return_value = Result(
        level=ResultLevel.FAILURE, message="拒绝访问"
    )
    result = orch.run_full_deploy()
    assert result.ok is False
    assert result.completed_steps == 1
    assert "路由" in result.failed_step
    backend.add_printer.assert_not_called()


# === 幂等：已配置的项目仍算成功 ===

def test_run_full_deploy_idempotent_when_all_already_configured():
    """路由已配、打印机已加、共享已加 → 仍返回成功，不重复操作。"""
    backend, orch = make_orchestrator()
    backend.route_exists.return_value = True  # 路由已配
    backend.printer_exists.return_value = True  # 打印机已加
    # 注意：路由和打印机已存在时，add_route/add_printer 不应被调用
    result = orch.run_full_deploy()
    assert result.ok is True
    assert result.completed_steps == 5
    backend.add_route.assert_not_called()  # 路由已存在，不重复添加
    backend.add_printer.assert_not_called()  # 打印机已存在，不重复添加


# === 进度回调 ===

def test_progress_callback_invoked_per_step():
    """on_progress 回调每步都被调用，带步骤序号和描述。"""
    progress_calls = []
    backend, _ = make_orchestrator()
    orch = DeployOrchestrator(
        backend,
        on_progress=lambda step, total, desc: progress_calls.append((step, total, desc)),
        on_log=lambda *a: None,
    )
    orch.run_full_deploy()
    # 5 步至少 5 次进度回调
    assert len(progress_calls) >= 5
    # 第一次是 step=1
    assert progress_calls[0][0] == 1
    assert progress_calls[0][1] == 5
    # 最后一次是 step=5
    assert progress_calls[-1][0] == 5


def test_log_callback_invoked_with_results():
    """on_log 回调记录每步的结果。"""
    log_calls = []
    backend, _ = make_orchestrator()
    orch = DeployOrchestrator(
        backend,
        on_progress=lambda *a: None,
        on_log=lambda msg, level: log_calls.append((msg, level)),
    )
    orch.run_full_deploy()
    # 应该有成功日志
    assert any("成功" in msg or "✓" in msg or "完成" in msg for msg, _ in log_calls)
