"""Windows 打印机安装测试。全部 mock subprocess，不真实安装。"""
from unittest.mock import patch, MagicMock

from route_tool.core.models import PrinterTarget, PrinterInstallResult
from route_tool.platform.windows.printers import (
    printer_exists, add_printer, run_powershell,
    DRIVER_NAME_MAP, build_add_command,
)


BIG = PrinterTarget(
    name="大打印机", description="SHARP MX-M905C",
    ip="192.168.0.210", driver_label="big",
)
SMALL = PrinterTarget(
    name="小打印机", description="SHARP MX-C6082D",
    ip="192.168.0.241", driver_label="small",
)


# === run_powershell：封装层 ===

def test_run_powershell_hides_console_window():
    """PowerShell 调用必须隐藏控制台窗口。"""
    import sys
    if sys.platform != "win32":
        import pytest
        pytest.skip("仅验证 Windows")
    with patch("route_tool.platform.windows.printers.subprocess.run",
               return_value=MagicMock(returncode=0, stdout="", stderr="")) as mock_run:
        run_powershell("Get-Printer")
    kwargs = mock_run.call_args[1]
    assert "creationflags" in kwargs or "startupinfo" in kwargs


def test_run_powershell_returns_completed_proc():
    mock = MagicMock(returncode=0, stdout="ok\n", stderr="")
    with patch("route_tool.platform.windows.printers.subprocess.run", return_value=mock):
        proc = run_powershell("Get-Printer")
    assert proc.returncode == 0
    assert proc.stdout == "ok\n"


# === printer_exists ===

def test_printer_exists_true_when_found():
    """Get-Printer 返回非空 stdout 时认为存在。"""
    mock = MagicMock(returncode=0, stdout="Name\n----\n大打印机\n", stderr="")
    with patch("route_tool.platform.windows.printers.run_powershell", return_value=mock):
        assert printer_exists(BIG) is True


def test_printer_exists_false_when_not_found():
    """Get-Printer 失败（returncode≠0）→ False。"""
    mock = MagicMock(returncode=1, stdout="", stderr="未找到")
    with patch("route_tool.platform.windows.printers.run_powershell", return_value=mock):
        assert printer_exists(BIG) is False


# === build_add_command：构造添加命令序列 ===

def test_build_add_command_big_printer():
    """构造大打印机的完整命令序列：建端口→加打印机。"""
    cmds = build_add_command(BIG, driver_name="SHARP MX-M905C PCL6")
    assert any("Add-PrinterPort" in c and "192.168.0.210" in c for c in cmds)
    assert any("Add-Printer" in c and "大打印机" in c for c in cmds)


def test_build_add_command_small_printer():
    cmds = build_add_command(SMALL, driver_name="SHARP UD3 PCL6")
    assert any("Add-PrinterPort" in c and "192.168.0.241" in c for c in cmds)
    assert any("Add-Printer" in c and "小打印机" in c for c in cmds)


# === add_printer：完整流程 ===

def test_add_printer_idempotent_when_already_exists():
    """已存在时直接返回成功，already_exists=True。"""
    with patch("route_tool.platform.windows.printers.printer_exists", return_value=True):
        result = add_printer(BIG)
    assert result.ok is True
    assert result.already_exists is True


def test_add_printer_success_flow():
    """正常添加：存在检查→装驱动→建端口→加打印机，全成功。"""
    with patch("route_tool.platform.windows.printers.printer_exists", return_value=False), \
         patch("route_tool.platform.windows.printers.install_driver", return_value="SHARP UD3 PCL6") as mock_drv, \
         patch("route_tool.platform.windows.printers.run_powershell",
               return_value=MagicMock(returncode=0, stdout="", stderr="")):
        result = add_printer(SMALL)
    assert result.ok is True
    mock_drv.assert_called_once()


def test_add_printer_add_command_failure():
    """Add-Printer 命令失败时返回失败结果。"""
    fail_proc = MagicMock(returncode=1, stdout="", stderr="驱动名无效")
    with patch("route_tool.platform.windows.printers.printer_exists", return_value=False), \
         patch("route_tool.platform.windows.printers.install_driver", return_value="BAD"), \
         patch("route_tool.platform.windows.printers.run_powershell", return_value=fail_proc):
        result = add_printer(SMALL)
    assert result.ok is False


def test_add_printer_driver_missing():
    """驱动名映射缺失时返回失败。"""
    weird = PrinterTarget(name="x", description="x", ip="1.2.3.4", driver_label="unknown")
    with patch("route_tool.platform.windows.printers.printer_exists", return_value=False):
        result = add_printer(weird)
    assert result.ok is False
    assert "驱动" in result.message
