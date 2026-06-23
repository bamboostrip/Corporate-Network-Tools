"""macOS 打印机安装测试（lpadmin）。全部 mock subprocess。"""
from unittest.mock import patch, MagicMock

from route_tool.core.models import PrinterTarget
from route_tool.platform.macos.printers import (
    printer_exists, add_printer, build_lpadmin_command,
)


BIG = PrinterTarget(
    name="大打印机", description="SHARP MX-M905C",
    ip="192.168.0.210", driver_label="big",
)


def test_printer_exists_true_when_lpstat_finds():
    """lpstat -p 找到打印机 → True。"""
    mock = MagicMock(returncode=0, stdout="printer 大打印机 is idle.\n", stderr="")
    with patch("route_tool.platform.macos.printers.subprocess.run", return_value=mock):
        assert printer_exists(BIG) is True


def test_printer_exists_false_when_lpstat_empty():
    mock = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.macos.printers.subprocess.run", return_value=mock):
        assert printer_exists(BIG) is False


def test_build_lpadmin_command():
    """构造 lpadmin 命令（IPP driverless）。"""
    cmd = build_lpadmin_command(BIG)
    assert "lpadmin" in cmd
    assert "-p" in cmd
    assert "大打印机" in cmd
    assert "ipp://192.168.0.210:631/ipp/print" in cmd
    assert "-m" in cmd
    assert "everywhere" in cmd


def test_add_printer_idempotent():
    with patch("route_tool.platform.macos.printers.printer_exists", return_value=True):
        result = add_printer(BIG)
    assert result.ok is True
    assert result.already_exists is True


def test_add_printer_success():
    mock = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.macos.printers.printer_exists", return_value=False), \
         patch("route_tool.platform.macos.printers.subprocess.run", return_value=mock) as mock_run:
        result = add_printer(BIG)
    assert result.ok is True
    mock_run.assert_called_once()


def test_add_printer_failure():
    mock = MagicMock(returncode=1, stdout="", stderr="lpadmin: Permission denied")
    with patch("route_tool.platform.macos.printers.printer_exists", return_value=False), \
         patch("route_tool.platform.macos.printers.subprocess.run", return_value=mock):
        result = add_printer(BIG)
    assert result.ok is False
