"""Windows 打印机安装测试。全部 mock subprocess，不真实安装。"""
from unittest.mock import patch, MagicMock

from route_tool.core.models import PrinterTarget, PrinterInstallResult
from route_tool.platform.windows.printers import (
    printer_exists, add_printer, run_powershell, install_driver,
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
    """正常添加：存在检查→装驱动→建端口→加打印机→最终验证，全成功。"""
    # printer_exists 第一次（开头幂等检查）False，第二次（最终验证）True
    with patch("route_tool.platform.windows.printers.printer_exists",
               side_effect=[False, True]), \
         patch("route_tool.platform.windows.printers.install_driver", return_value="SHARP UD3 PCL6") as mock_drv, \
         patch("route_tool.platform.windows.printers.run_powershell",
               return_value=MagicMock(returncode=0, stdout="", stderr="")):
        result = add_printer(SMALL)
    assert result.ok is True
    mock_drv.assert_called_once()


def test_add_printer_succeeds_when_port_already_exists():
    """端口已存在不应视为失败（端口命令 returncode=1 但 try/catch 吞了错误）。

    真实场景：用户重复添加，或端口残留。端口创建命令的 PowerShell 进程退出码
    可能是 1（即使 try/catch 吞了错误对象），但 Add-Printer 仍能成功。
    工具应该看 Add-Printer 的结果，而不是端口命令的退出码。
    """
    # 端口命令 returncode=1（已存在），Add-Printer returncode=0（成功）
    port_exists = MagicMock(returncode=1, stdout="", stderr="")
    add_ok = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.windows.printers.printer_exists",
               side_effect=[False, True]), \
         patch("route_tool.platform.windows.printers.install_driver", return_value="SHARP UD3 PCL6"), \
         patch("route_tool.platform.windows.printers.run_powershell",
               side_effect=[port_exists, add_ok]):
        result = add_printer(SMALL)
    assert result.ok is True


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


# === install_driver：pnputil + inf 静默安装 ===

def test_install_driver_already_installed():
    """系统已装该驱动时，直接返回驱动名，不调用 pnputil。"""
    with patch("route_tool.platform.windows.printers.run_powershell",
               return_value=MagicMock(returncode=0, stdout="SHARP MX-M905 PCL6\n", stderr="")):
        result = install_driver(BIG)
    assert result == "SHARP MX-M905 PCL6"


def test_install_driver_not_installed_uses_pnputil():
    """驱动未装时，定位 inf 并用 pnputil 静默安装。

    注意：pnputil 成功时 returncode 也可能是 1（退出码不可靠），
    必须看 stdout 是否含"成功"关键字。
    Add-PrinterDriver 不带 -InfPath（-InfPath 参数在某些情况下报 0x80070057，
    驱动已被 pnputil 装进 DriverStore 后，按名字注册即可）。
    """
    # Get-PrinterDriver 检查（空）→ pnputil（returncode=1 但 stdout 含成功）→ Add-PrinterDriver（成功）
    check_empty = MagicMock(returncode=0, stdout="", stderr="")
    pnputil_ok = MagicMock(returncode=1, stdout="已成功添加驱动程序包", stderr="")
    register_ok = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.windows.printers.run_powershell",
               side_effect=[check_empty, pnputil_ok, register_ok]) as mock_ps, \
         patch("route_tool.platform.windows.printers.find_driver_inf",
               return_value=r"C:\drivers\su0emenu.inf"):
        result = install_driver(BIG)
    assert result == "SHARP MX-M905 PCL6"
    # 至少有一条命令含 pnputil
    pnputil_calls = [str(c) for c in mock_ps.call_args_list if "pnputil" in str(c)]
    assert len(pnputil_calls) >= 1, "应该调用 pnputil 安装 inf"
    # Add-PrinterDriver 命令不应含 InfPath（避免 0x80070057 参数错误）
    register_calls = [str(c) for c in mock_ps.call_args_list if "Add-PrinterDriver" in str(c)]
    assert any("InfPath" not in c for c in register_calls), "Add-PrinterDriver 不应带 InfPath"


def test_install_driver_pnputil_failure_returns_none():
    """pnputil 失败时返回 None。"""
    check_empty = MagicMock(returncode=0, stdout="", stderr="")
    fail = MagicMock(returncode=1, stdout="", stderr="拒绝访问")
    with patch("route_tool.platform.windows.printers.run_powershell",
               side_effect=[check_empty, fail]), \
         patch("route_tool.platform.windows.printers.find_driver_inf",
               return_value=r"C:\drivers\su0emenu.inf"):
        result = install_driver(BIG)
    assert result is None


def test_install_driver_inf_not_found_returns_none():
    """inf 文件找不到时返回 None（驱动资源缺失）。"""
    check_empty = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.windows.printers.run_powershell",
               return_value=check_empty), \
         patch("route_tool.platform.windows.printers.find_driver_inf", return_value=None):
        result = install_driver(BIG)
    assert result is None


# === find_driver_inf：资源定位 ===

def test_find_driver_inf_returns_path_when_exists(tmp_path):
    """资源目录存在 inf 时返回路径。"""
    from route_tool.platform.windows import printers
    # 模拟驱动资源目录
    big_dir = tmp_path / "big"
    big_dir.mkdir()
    inf_file = big_dir / "su0emenu.inf"
    inf_file.write_text("test")
    with patch.object(printers, "_drivers_root", return_value=tmp_path):
        path = printers.find_driver_inf("big")
    assert path is not None
    assert path.name == "su0emenu.inf"


def test_find_driver_inf_returns_none_when_missing(tmp_path):
    """资源目录无 inf 时返回 None。"""
    from route_tool.platform.windows import printers
    with patch.object(printers, "_drivers_root", return_value=tmp_path):
        path = printers.find_driver_inf("big")
    assert path is None
