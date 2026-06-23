"""macOS 打印机自动安装。

用 lpadmin + IPP Everywhere（driverless）。
注意：210/241 的 urf 不完整，渲染可能异常，UI 会提示用户。
"""
from __future__ import annotations

import subprocess

from route_tool.core.models import PrinterInstallResult, PrinterTarget


def printer_exists(target: PrinterTarget) -> bool:
    """检查打印机是否已添加（lpstat -p）。"""
    try:
        proc = subprocess.run(
            ["lpstat", "-p", target.name],
            capture_output=True, text=True, timeout=5,
        )
        return proc.returncode == 0 and bool(proc.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        return False


def build_lpadmin_command(target: PrinterTarget) -> list[str]:
    """构造 lpadmin 命令（IPP driverless）。

    -E: 启用打印机
    -m everywhere: 让 CUPS 用 IPP Everywhere driverless
    -v: 打印机 URI（IPP）
    """
    uri = f"ipp://{target.ip}:631/ipp/print"
    return [
        "lpadmin",
        "-p", target.name,
        "-E",
        "-v", uri,
        "-m", "everywhere",
        "-L", "公司",
        "-D", target.description,
    ]


def add_printer(target: PrinterTarget) -> PrinterInstallResult:
    """添加打印机（IPP driverless 尝试）。幂等。"""
    if printer_exists(target):
        return PrinterInstallResult(
            printer_name=target.name, ok=True, already_exists=True,
            message=f"{target.name} 已添加过",
        )

    cmd = build_lpadmin_command(target)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (subprocess.SubprocessError, OSError) as e:
        return PrinterInstallResult(
            printer_name=target.name, ok=False,
            message=f"执行 lpadmin 失败: {e}",
            error_code=-1,
        )

    if proc.returncode == 0:
        return PrinterInstallResult(
            printer_name=target.name, ok=True,
            message=f"{target.name} 已添加（IPP driverless，{target.description}）",
        )
    return PrinterInstallResult(
        printer_name=target.name, ok=False,
        message="添加失败，请尝试从夏普官网下载 macOS 驱动手动添加",
        raw_output=proc.stderr,
        error_code=proc.returncode,
    )
