from route_tool.core.models import (
    Result, ResultLevel, RouteInfo, PingResult, PrinterInfo, NetworkInfo
)


def test_result_success():
    r = Result(level=ResultLevel.SUCCESS, message="ok")
    assert r.level == ResultLevel.SUCCESS
    assert r.message == "ok"
    assert r.raw_output == ""
    assert r.error_code == 0


def test_result_failure_with_output():
    r = Result(
        level=ResultLevel.FAILURE,
        message="路由添加失败",
        raw_output="The route addition failed",
        error_code=1,
    )
    assert r.level == ResultLevel.FAILURE
    assert r.raw_output == "The route addition failed"
    assert r.error_code == 1


def test_route_info_defaults():
    r = RouteInfo(network="192.168.0.0", mask="255.255.252.0", gateway="192.168.5.22")
    assert r.network == "192.168.0.0"
    assert r.mask == "255.255.252.0"
    assert r.gateway == "192.168.5.22"
    assert r.metric == 1
    assert r.persistent is True


def test_ping_result_ok():
    p = PingResult(host="192.168.0.210", ok=True, message="可达", latency_ms=12.5)
    assert p.ok is True
    assert p.latency_ms == 12.5
    assert p.raw_output == ""


def test_ping_result_fail():
    p = PingResult(host="192.168.0.248", ok=False, message="超时")
    assert p.ok is False
    assert p.latency_ms is None


def test_printer_info_defaults():
    p = PrinterInfo(name="大打印机", ip="192.168.0.210")
    assert p.name == "大打印机"
    assert p.ip == "192.168.0.210"
    assert p.icon == "🖨"


def test_result_level_is_enum():
    assert ResultLevel.SUCCESS != ResultLevel.FAILURE
    assert ResultLevel.UNSUPPORTED.value == "unsupported"


def test_result_ok_property():
    assert Result(level=ResultLevel.SUCCESS, message="x").ok is True
    assert Result(level=ResultLevel.FAILURE, message="x").ok is False
    assert Result(level=ResultLevel.UNSUPPORTED, message="x").ok is False


def test_network_info_defaults():
    """NetworkInfo 携带当前网络环境信息，给 UI 显示用。"""
    info = NetworkInfo(
        wifi_name="Corp-WiFi",
        local_ip="192.168.5.100",
        gateway522_reachable=True,
        gateway522_message="可达",
    )
    assert info.wifi_name == "Corp-WiFi"
    assert info.local_ip == "192.168.5.100"
    assert info.gateway522_reachable is True
    assert info.gateway522_message == "可达"


def test_network_info_unreachable_scenario():
    """5.22 不可达时的典型取值。"""
    info = NetworkInfo(
        wifi_name="未连接",
        local_ip="未知",
        gateway522_reachable=False,
        gateway522_message="ping 超时",
    )
    assert info.gateway522_reachable is False


def test_printer_target_defaults():
    from route_tool.core.models import PrinterTarget
    t = PrinterTarget(
        name="大打印机",
        description="SHARP MX-M905C 彩色复合机",
        ip="192.168.0.210",
        driver_label="big",
    )
    assert t.name == "大打印机"
    assert t.description == "SHARP MX-M905C 彩色复合机"
    assert t.ip == "192.168.0.210"
    assert t.port == 9100  # 默认 9100
    assert t.driver_label == "big"


def test_printer_install_result_success():
    from route_tool.core.models import PrinterInstallResult
    r = PrinterInstallResult(printer_name="大打印机", ok=True, message="添加成功")
    assert r.ok is True
    assert r.already_exists is False  # 默认 False
    assert r.raw_output == ""
    assert r.error_code == 0


def test_printer_install_result_already_exists():
    from route_tool.core.models import PrinterInstallResult
    r = PrinterInstallResult(
        printer_name="大打印机", ok=True, already_exists=True, message="已添加过"
    )
    assert r.ok is True
    assert r.already_exists is True


def test_deploy_result_defaults():
    """DeployResult 携带一键部署的整体结果。"""
    from route_tool.core.models import DeployResult
    r = DeployResult(
        total_steps=5,
        completed_steps=5,
        ok=True,
        message="一键部署完成",
    )
    assert r.total_steps == 5
    assert r.completed_steps == 5
    assert r.ok is True
    assert r.failed_step == ""  # 默认空


def test_deploy_result_partial_failure():
    """部分失败时记录已完成步数和失败步骤名。"""
    from route_tool.core.models import DeployResult
    r = DeployResult(
        total_steps=5,
        completed_steps=3,
        ok=False,
        message="大打印机添加失败",
        failed_step="添加大打印机",
    )
    assert r.completed_steps == 3
    assert r.ok is False
    assert r.failed_step == "添加大打印机"
