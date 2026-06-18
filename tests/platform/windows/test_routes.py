from pathlib import Path
from unittest.mock import patch, MagicMock

from route_tool.core.models import ResultLevel, RouteInfo
from route_tool.platform.windows.routes import (
    route_exists, add_route, remove_route, parse_route_exists,
)

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
ROUTE_EXISTS = RouteInfo(
    network="192.168.0.0",
    mask="255.255.252.0",
    gateway="192.168.5.22",
)


# === parse_route_exists（纯解析逻辑，不调系统命令）===

def test_parse_finds_existing_route():
    output = (FIXTURES / "route_print_exists.txt").read_text(encoding="utf-8")
    assert parse_route_exists(output, ROUTE_EXISTS) is True


def test_parse_absent_route():
    output = (FIXTURES / "route_print_absent.txt").read_text(encoding="utf-8")
    assert parse_route_exists(output, ROUTE_EXISTS) is False


def test_parse_does_not_match_wrong_gateway():
    # 即使 network 和 mask 匹配，gateway 不对也不算存在
    output = (FIXTURES / "route_print_exists.txt").read_text(encoding="utf-8")
    wrong = RouteInfo(network="192.168.0.0", mask="255.255.252.0", gateway="192.168.5.99")
    assert parse_route_exists(output, wrong) is False


def test_parse_does_not_match_wrong_mask():
    output = (FIXTURES / "route_print_exists.txt").read_text(encoding="utf-8")
    wrong = RouteInfo(network="192.168.0.0", mask="255.255.255.0", gateway="192.168.5.22")
    assert parse_route_exists(output, wrong) is False


def test_parse_handles_empty_output():
    assert parse_route_exists("", ROUTE_EXISTS) is False


def test_parse_normalizes_whitespace():
    # 多空格 / tab 混合也要能匹配
    output = "192.168.0.0   \t  255.255.252.0   192.168.5.22   192.168.5.100  31\n"
    assert parse_route_exists(output, ROUTE_EXISTS) is True


# === route_exists（封装 subprocess）===

def test_route_exists_calls_subprocess_and_parses():
    fixture_output = (FIXTURES / "route_print_exists.txt").read_text(encoding="utf-8")
    mock_result = MagicMock()
    mock_result.stdout = fixture_output
    mock_result.returncode = 0
    with patch("route_tool.platform.windows.routes.subprocess.run", return_value=mock_result) as mock_run:
        assert route_exists(ROUTE_EXISTS) is True
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "route" in args
    assert "print" in args
    assert "192.168.0.0" in args


def test_route_exists_uses_gbk_encoding():
    """Windows route print 输出是 GBK，必须显式指定 encoding。"""
    mock_result = MagicMock()
    mock_result.stdout = "some output"
    mock_result.returncode = 0
    with patch("route_tool.platform.windows.routes.subprocess.run", return_value=mock_result) as mock_run:
        route_exists(ROUTE_EXISTS)
    kwargs = mock_run.call_args[1]
    assert kwargs.get("encoding") == "gbk"
    assert kwargs.get("errors") == "replace"


# === add_route ===

def test_add_route_success():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "操作完成"
    mock_result.stderr = ""
    with patch("route_tool.platform.windows.routes.subprocess.run", return_value=mock_result) as mock_run:
        result = add_route(ROUTE_EXISTS)
    assert result.level == ResultLevel.SUCCESS
    # 验证命令参数：-p（持久） + add + network + mask + mask_value + gateway
    args = mock_run.call_args[0][0]
    assert "-p" in args
    assert "add" in args
    assert "192.168.0.0" in args
    assert "mask" in args
    assert "255.255.252.0" in args
    assert "192.168.5.22" in args
    assert "1" in args  # metric


def test_add_route_no_shell():
    """不能用 shell=True。"""
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.windows.routes.subprocess.run", return_value=mock_result) as mock_run:
        add_route(ROUTE_EXISTS)
    assert mock_run.call_args[1].get("shell") is not True


def test_add_route_failure():
    mock_result = MagicMock(returncode=1, stdout="", stderr="拒绝访问")
    with patch("route_tool.platform.windows.routes.subprocess.run", return_value=mock_result):
        result = add_route(ROUTE_EXISTS)
    assert result.level == ResultLevel.FAILURE
    assert "拒绝访问" in result.raw_output or "拒绝访问" in result.message
    assert result.error_code == 1


# === remove_route ===

def test_remove_route_success():
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.windows.routes.subprocess.run", return_value=mock_result) as mock_run:
        result = remove_route(ROUTE_EXISTS)
    assert result.level == ResultLevel.SUCCESS
    args = mock_run.call_args[0][0]
    assert "delete" in args
    assert "192.168.0.0" in args
