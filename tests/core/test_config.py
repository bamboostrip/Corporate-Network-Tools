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
    assert "192.168.0.248" in ips  # 小打印机
    assert "192.168.0.1" in ips    # 锐捷网关
