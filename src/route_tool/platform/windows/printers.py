"""Windows 打印机自动安装。

流程：检查存在 → 强制覆盖安装驱动 → 建 TCP/IP 端口 → 添加打印机。
全部用 PowerShell PrintManagement 模块；pnputil 装驱动 inf。
所有 subprocess 调用隐藏控制台窗口（复用 no_window_kwargs）。

设计决策：
  驱动安装策略采用"总是覆盖"而非"检查后跳过"。
  理由：pnputil /add-driver /install 本身幂等，驱动已存在时直接覆盖文件，
  不报错也不需要先检查。这样无论用户之前装过什么版本、卸没卸干净，
  都能保证驱动文件是我们内嵌的已知可用版本，彻底避免"驱动注册存在但
  文件损坏"导致的 0x8007000d / 0x80070006 等错误。
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from route_tool.core.models import PrinterInstallResult, PrinterTarget
from route_tool.platform.windows.subprocess_utils import no_window_kwargs

# 驱动名映射：driver_label → 系统中的驱动名
DRIVER_NAME_MAP: dict[str, str] = {
    "big": "SHARP MX-M905 PCL6",
    "small": "SHARP UD3 PCL6",
}

# Add-Printer 时序重试参数（驱动覆盖安装后偶发 Spooler 延迟）
_RETRY_DELAYS = [3, 6]   # 最多重试 2 次，等待 3 / 6 秒


def _drivers_root() -> Path:
    """返回驱动资源根目录。

    开发环境：src/route_tool/drivers/
    PyInstaller 打包后：sys._MEIPASS/route_tool/drivers/
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "route_tool" / "drivers"  # type: ignore
    return Path(__file__).resolve().parent.parent.parent / "drivers"


def find_driver_inf(driver_label: str) -> Path | None:
    """在 drivers/<label>/ 下查找 .inf 文件，返回第一个匹配的路径。"""
    driver_dir = _drivers_root() / driver_label
    if not driver_dir.is_dir():
        return None
    inf_files = list(driver_dir.glob("*.inf"))
    return inf_files[0] if inf_files else None


def run_powershell(script: str) -> subprocess.CompletedProcess:
    """执行 PowerShell 脚本，强制 UTF-8 输出编码，隐藏控制台窗口。"""
    utf8_prefix = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
    cmd = [
        "powershell", "-NoProfile", "-NonInteractive",
        "-Command", utf8_prefix + script,
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **no_window_kwargs(),
    )


def printer_exists(target: PrinterTarget) -> bool:
    """检查打印机是否已添加。"""
    proc = run_powershell(
        f"Get-Printer -Name '{target.name}' -ErrorAction Stop | Out-String"
    )
    return proc.returncode == 0 and bool(proc.stdout.strip())


def install_driver(target: PrinterTarget) -> str | None:
    """总是覆盖安装驱动，返回驱动名；失败返回 None。

    不检查驱动是否已存在，直接用 pnputil 覆盖安装内嵌 inf。
    pnputil /add-driver /install 是幂等的：
      - 驱动未装：正常安装
      - 驱动已装（任意版本/状态）：覆盖文件，保证驱动文件完整可用
    这样无论用户之前的驱动状态如何，都能得到干净的已知可用驱动。
    """
    driver_name = DRIVER_NAME_MAP.get(target.driver_label)
    if not driver_name:
        return None

    inf_path = find_driver_inf(target.driver_label)
    if inf_path is None:
        return None  # 驱动资源未就位（打包时漏掉）

    # 1. pnputil 覆盖安装 inf 到 DriverStore（支持覆盖已有版本）
    pnputil_script = f"& pnputil /add-driver '{inf_path}' /install 2>&1 | Out-String"
    proc = run_powershell(pnputil_script)
    success_keywords = (
        "成功", "successfully", "Published Name", "oem",
        "already exists", "已存在",
        "Driver package added",
    )
    if not any(kw.lower() in proc.stdout.lower() for kw in success_keywords):
        return None  # pnputil 真失败

    # 2. Add-PrinterDriver 注册驱动到打印子系统
    #    驱动已注册时此命令会报错，忽略即可（文件已经被 pnputil 覆盖更新了）
    run_powershell(
        f"Add-PrinterDriver -Name '{driver_name}' -ErrorAction SilentlyContinue | Out-String"
    )

    # 3. 等待 Spooler 完成驱动初始化
    time.sleep(2)

    return driver_name


def _ensure_printer_port(port_name: str, ip: str) -> bool:
    """确保 TCP/IP 打印机端口存在，返回是否成功。先检查再创建。"""
    check = run_powershell(
        f"Get-PrinterPort -Name '{port_name}' -ErrorAction SilentlyContinue | Out-String"
    )
    if check.returncode == 0 and check.stdout.strip():
        return True  # 端口已存在

    create = run_powershell(
        f"Add-PrinterPort -Name '{port_name}' "
        f"-PrinterHostAddress '{ip}' -ErrorAction Stop | Out-String"
    )
    return create.returncode == 0


def add_printer(target: PrinterTarget) -> PrinterInstallResult:
    """完整添加流程：幂等检查 → 覆盖安装驱动 → 端口 → 添加打印机（含重试）。"""
    # 1. 幂等检查：打印机已存在则跳过
    if printer_exists(target):
        return PrinterInstallResult(
            printer_name=target.name, ok=True, already_exists=True,
            message=f"{target.name} 已添加过，无需重复操作",
        )

    # 2. 覆盖安装驱动（不管之前状态如何，总是重装）
    driver_name = install_driver(target)
    if not driver_name:
        return PrinterInstallResult(
            printer_name=target.name, ok=False,
            message=f"驱动安装失败（driver_label={target.driver_label}，"
                    f"请确认程序完整性）",
            error_code=-1,
        )

    # 3. 确保打印机端口存在
    port_name = f"IP_{target.ip}"
    if not _ensure_printer_port(port_name, target.ip):
        return PrinterInstallResult(
            printer_name=target.name, ok=False,
            message=f"创建打印机端口失败（{port_name} → {target.ip}）",
            error_code=-2,
        )

    # 4. Add-Printer，遇到 Spooler 时序问题（0x80070006）则等待重试
    add_cmd = (
        f"Add-Printer -Name '{target.name}' "
        f"-DriverName '{driver_name}' "
        f"-PortName '{port_name}' -ErrorAction Stop | Out-String"
    )
    last_proc = run_powershell(add_cmd)

    for wait_sec in _RETRY_DELAYS:
        if last_proc.returncode == 0:
            break
        stderr = last_proc.stderr or last_proc.stdout
        # 只对 Spooler 时序错误重试，其他错误直接失败
        if "0x80070006" not in stderr:
            break
        time.sleep(wait_sec)
        last_proc = run_powershell(add_cmd)

    if last_proc.returncode != 0:
        err_msg = (last_proc.stderr or last_proc.stdout or "未知错误").strip()
        return PrinterInstallResult(
            printer_name=target.name, ok=False,
            message=f"添加打印机失败: {err_msg}",
            raw_output=last_proc.stderr or last_proc.stdout,
            error_code=last_proc.returncode,
        )

    # 5. 最终验证
    if not printer_exists(target):
        return PrinterInstallResult(
            printer_name=target.name, ok=False,
            message="添加打印机失败：命令执行但打印机未出现",
            raw_output=last_proc.stdout,
            error_code=-1,
        )

    return PrinterInstallResult(
        printer_name=target.name, ok=True,
        message=f"{target.name} 添加成功（{target.description}）",
    )
