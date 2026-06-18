from route_tool.core.models import (
    Result, ResultLevel, RouteInfo, PingResult, PrinterInfo
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
