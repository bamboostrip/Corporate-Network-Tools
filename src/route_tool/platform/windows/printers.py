"""Windows 打印机自动安装。

流程：检查存在 → 装/确认驱动 → 建 TCP/IP 端口(9100) → 添加打印机。
全部用 PowerShell PrintManagement 模块；pnputil 装驱动 inf。
所有 subprocess 调用隐藏控制台窗口（复用 no_window_kwargs）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from route_tool.core.models import PrinterInstallResult, PrinterTarget
from route_tool.platform.windows.subprocess_utils import no_window_kwargs

# 驱动名映射：driver_label → 系统中的驱动名
# 实测确认（用户手动安装后从 Get-PrinterDriver 取得）：
#   大打印机：SHARP MX-M905 PCL6（注意是 M905，非 M905C；驱动名与型号不同）
#   小打印机：SHARP UD3 PCL6（从 sv0emenu.inf 的 Model1 字段确认）
# PCL6 优先于 PS：日常文档速度更快、兼容性好，PS 留给设计师按需手动安装。
DRIVER_NAME_MAP: dict[str, str] = {
    "big": "SHARP MX-M905 PCL6",
    "small": "SHARP UD3 PCL6",
}


def _drivers_root() -> Path:
    """返回驱动资源根目录。

    开发环境：src/route_tool/drivers/
    PyInstaller 打包后：sys._MEIPASS/route_tool/drivers/
    """
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后，资源在 _MEIPASS 下
        return Path(sys._MEIPASS) / "route_tool" / "drivers"  # type: ignore
    # 开发环境：本文件在 platform/windows/，往上 3 级到 route_tool/
    return Path(__file__).resolve().parent.parent.parent / "drivers"


def find_driver_inf(driver_label: str) -> Path | None:
    """在 drivers/<label>/ 下查找 .inf 文件，返回第一个匹配的路径。

    驱动目录可能含多个文件（inf + dll + dat），只取 inf。
    找不到（资源未就位）返回 None。
    """
    driver_dir = _drivers_root() / driver_label
    if not driver_dir.is_dir():
        return None
    inf_files = list(driver_dir.glob("*.inf"))
    return inf_files[0] if inf_files else None


def run_powershell(script: str) -> subprocess.CompletedProcess:
    """执行 PowerShell 脚本，隐藏控制台窗口。

    用 -Command 而非 -File，避免临时文件。
    """
    cmd = [
        "powershell", "-NoProfile", "-NonInteractive",
        "-Command", script,
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
    """检查打印机是否已添加（Get-Printer 成功返回即存在）。"""
    # 用单引号包裹中文名；Get-Printer 找不到会抛异常(returncode≠0)
    script = f"Get-Printer -Name '{target.name}' -ErrorAction Stop | Out-String"
    proc = run_powershell(script)
    return proc.returncode == 0 and bool(proc.stdout.strip())


def install_driver(target: PrinterTarget) -> str | None:
    """确保驱动已安装，返回驱动名。

    - 已装：直接返回驱动名
    - 未装：用 pnputil 装内嵌 inf，再 Add-PrinterDriver 注册
    - 失败（资源缺失/pnputil 报错）：返回 None
    """
    driver_name = DRIVER_NAME_MAP.get(target.driver_label)
    if not driver_name:
        return None

    # 1. 检查驱动是否已装
    check = run_powershell(
        f"Get-PrinterDriver -Name '{driver_name}' -ErrorAction SilentlyContinue | Out-String"
    )
    if check.stdout.strip():
        return driver_name  # 已装

    # 2. 未装 → 定位内嵌 inf
    inf_path = find_driver_inf(target.driver_label)
    if inf_path is None:
        return None  # 驱动资源未就位

    # 3. pnputil 安装 inf 到驱动库（静默、需管理员）
    #    注意：pnputil 的退出码不可靠（成功也可能返回 1），
    #    必须看 stdout 是否含"成功/successfully"关键字判断。
    pnputil_script = f"& pnputil /add-driver '{inf_path}' /install 2>&1 | Out-String"
    proc = run_powershell(pnputil_script)
    success_keywords = ("成功", "successfully", "Published Name", "oem")
    if not any(kw.lower() in proc.stdout.lower() for kw in success_keywords):
        return None  # pnputil 真失败

    # 4. Add-PrinterDriver 注册驱动到打印子系统
    #    不带 -InfPath：pnputil 已把驱动装进 DriverStore，按名字注册即可。
    #    -InfPath 参数在某些 inf 上会报 0x80070057（参数无效）。
    register_script = (
        f"Add-PrinterDriver -Name '{driver_name}' -ErrorAction Stop | Out-String"
    )
    proc = run_powershell(register_script)
    if proc.returncode != 0:
        return None

    return driver_name


def build_add_command(target: PrinterTarget, driver_name: str) -> list[str]:
    """构造添加打印机的 PowerShell 命令序列。

    返回多条独立命令（顺序执行）。端口已存在不视为错误。
    """
    port_name = f"IP_{target.ip}"
    return [
        # 1. 创建 TCP/IP 端口（若已存在则跳过）
        #    用 try/catch 吞"已存在"错误，端口命令的退出码不影响后续
        f"try {{ Add-PrinterPort -Name '{port_name}' "
        f"-PrinterHostAddress '{target.ip}' -ErrorAction Stop }} catch {{ }}",
        # 2. 添加打印机，绑定驱动和端口
        f"Add-Printer -Name '{target.name}' -DriverName '{driver_name}' "
        f"-PortName '{port_name}'",
    ]


def add_printer(target: PrinterTarget) -> PrinterInstallResult:
    """完整添加流程：幂等检查 → 驱动 → 端口 → 打印机。"""
    # 1. 幂等
    if printer_exists(target):
        return PrinterInstallResult(
            printer_name=target.name, ok=True, already_exists=True,
            message=f"{target.name} 已添加过，无需重复操作",
        )

    # 2. 驱动
    driver_name = install_driver(target)
    if not driver_name:
        return PrinterInstallResult(
            printer_name=target.name, ok=False,
            message=f"驱动配置缺失（driver_label={target.driver_label}）",
            error_code=-1,
        )

    # 3. 执行命令序列
    #    端口命令失败（已存在/被 try-catch 吞）不视为整体失败，
    #    只有 Add-Printer 命令本身失败才算失败。
    cmds = build_add_command(target, driver_name)
    # 端口创建命令（第一条）失败可忽略
    port_proc = run_powershell(cmds[0])
    # Add-Printer 命令（最后一条）才是关键
    add_proc = run_powershell(cmds[-1])
    if add_proc.returncode != 0:
        return PrinterInstallResult(
            printer_name=target.name, ok=False,
            message=f"添加打印机失败: {add_proc.stderr.strip() or add_proc.stdout.strip() or '未知错误'}",
            raw_output=add_proc.stderr or port_proc.stderr,
            error_code=add_proc.returncode,
        )

    # 4. 最终验证（Add-Printer 返回 0 也不一定真成功，再确认一次）
    if not printer_exists(target):
        return PrinterInstallResult(
            printer_name=target.name, ok=False,
            message="添加打印机失败：命令执行但打印机未出现",
            raw_output=add_proc.stdout,
            error_code=-1,
        )

    return PrinterInstallResult(
        printer_name=target.name, ok=True,
        message=f"{target.name} 添加成功（{target.description}）",
    )
