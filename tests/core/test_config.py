from route_tool.core.config import (
    TARGET_NETWORK, SUBNET_MASK, GATEWAY, ROUTE_METRIC,
    ROUTE_PERSISTENT, TEST_TARGETS, PING_COUNT, PING_TIMEOUT_SECONDS,
    DEFAULT_ROUTE, TARGET_CIDR,
)
from route_tool.core.models import RouteInfo, PrinterInfo


def test_route_constants():
    assert TARGET_NETWORK == "192.168.0.0"
    assert SUBNET_MASK == "255.255.252.0"  # /22 的点分十进制
    assert GATEWAY == "192.168.5.22"
    assert ROUTE_METRIC == 1
    assert ROUTE_PERSISTENT is True


def test_target_cidr():
    assert TARGET_CIDR == "192.168.0.0/22"


def test_default_route_is_route_info():
    assert isinstance(DEFAULT_ROUTE, RouteInfo)
    assert DEFAULT_ROUTE.network == TARGET_NETWORK
    assert DEFAULT_ROUTE.mask == SUBNET_MASK
    assert DEFAULT_ROUTE.gateway == GATEWAY


def test_ping_params():
    assert PING_COUNT == 2
    assert PING_TIMEOUT_SECONDS == 10


def test_test_targets_are_printers():
    assert len(TEST_TARGETS) == 3
    assert all(isinstance(t, PrinterInfo) for t in TEST_TARGETS)
    ips = [t.ip for t in TEST_TARGETS]
    assert "192.168.0.210" in ips  # 大打印机
    assert "192.168.0.241" in ips  # 小打印机（修正：原 248 错误）
    assert "192.168.0.1" in ips    # 锐捷网关


def test_printer_defs():
    from route_tool.core.config import PRINTER_DEFS
    from route_tool.core.models import PrinterTarget
    assert len(PRINTER_DEFS) == 2
    assert all(isinstance(p, PrinterTarget) for p in PRINTER_DEFS)

    big = PRINTER_DEFS[0]
    assert big.name == "大打印机"
    assert big.ip == "192.168.0.210"
    assert "MX-M905C" in big.description

    small = PRINTER_DEFS[1]
    assert small.name == "小打印机"
    assert small.ip == "192.168.0.241"  # 修正：原 248 是错的
    assert "MX-C6082D" in small.description


def test_scan_share_config():
    """扫描文件共享配置：路径、账号、密码。"""
    from route_tool.core.config import SCAN_SHARE_PATH, SCAN_SHARE_USER, SCAN_SHARE_PASSWORD
    assert SCAN_SHARE_PATH == r"\\192.168.0.210\shared\SMY"
    assert SCAN_SHARE_USER == "admin"
    assert SCAN_SHARE_PASSWORD == "admin"
