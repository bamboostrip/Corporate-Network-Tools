"""Windows 打印机自动安装。

流程：检查存在 → 装/确认驱动 → 建 TCP/IP 端口(9100) → 添加打印机。
全部用 PowerShell PrintManagement 模块；pnputil 装驱动 inf。
所有 subprocess 调用隐藏控制台窗口（复用 no_window_kwargs）。
"""
from __future__ import annotations

import subprocess

from route_tool.core.models import PrinterInstallResult, PrinterTarget
from route_tool.platform.windows.subprocess_utils import no_window_kwargs

# 驱动名映射：driver_label → 系统中的驱动名
# 注意：big 的驱动名需用户实测夏普大.exe /S 装出的驱动名后填入；暂用型号推断值
DRIVER_NAME_MAP: dict[str, str] = {
    "big": "SHARP MX-M905C PCL6",   # TODO: 待用户实测 Task 0 后确认
    "small": "SHARP UD3 PCL6",      # 已从 sv0emenu.inf 确认
}


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
    """确保驱动已安装，返回驱动名。已装则直接返回，否则静默安装。

    返回 None 表示驱动名映射缺失（实际 inf 安装逻辑待 Task 7 接入 resource_path）。
    """
    driver_name = DRIVER_NAME_MAP.get(target.driver_label)
    if not driver_name:
        return None

    # 检查驱动是否已装
    check = run_powershell(
        f"Get-PrinterDriver -Name '{driver_name}' -ErrorAction SilentlyContinue | Out-String"
    )
    if check.stdout.strip():
        return driver_name  # 已装

    # 未装 → TODO: Task 7 接入 resource_path 后用 pnputil 装 inf
    # 暂直接返回驱动名，让 Add-Printer 尝试（若系统驱动库没有会失败，错误信息会提示）
    return driver_name


def build_add_command(target: PrinterTarget, driver_name: str) -> list[str]:
    """构造添加打印机的 PowerShell 命令序列。

    返回多条独立命令（顺序执行）。端口已存在不视为错误。
    """
    port_name = f"IP_{target.ip}"
    return [
        # 1. 创建 TCP/IP 端口（若已存在则跳过）
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
    cmds = build_add_command(target, driver_name)
    for script in cmds:
        proc = run_powershell(script)
        if proc.returncode != 0:
            # 端口创建已被 try/catch 吞掉；到这里说明 Add-Printer 本身失败
            return PrinterInstallResult(
                printer_name=target.name, ok=False,
                message=f"添加打印机失败: {proc.stderr.strip() or proc.stdout.strip()}",
                raw_output=proc.stderr,
                error_code=proc.returncode,
            )

    return PrinterInstallResult(
        printer_name=target.name, ok=True,
        message=f"{target.name} 添加成功（{target.description}）",
    )
