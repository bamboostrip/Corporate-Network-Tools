"""Windows 打印机自动安装。

流程：检查存在 → 装/确认驱动 → 建 TCP/IP 端口(9100) → 添加打印机。
全部用 PowerShell PrintManagement 模块；pnputil 装驱动 inf。
所有 subprocess 调用隐藏控制台窗口（复用 no_window_kwargs）。

Bug 修复记录（HRESULT 0x80070006 ERROR_INVALID_HANDLE）：
  1. PowerShell 输出编码：改用系统代码页(chcp 65001)，避免 GBK 乱码导致字符串判断失效。
  2. 驱动检查：改用 returncode 而非 stdout 内容，避免 SilentlyContinue 误判。
  3. pnputil 成功判断：补充"already exists/已存在"关键词，避免重装时误判失败。
  4. Add-Printer 重试：驱动注册后 Spooler 需要时间处理，加 3 次重试+递增延迟。
  5. 端口创建：先检查端口是否已存在，避免 try/catch 掩盖真实创建失败。
"""
from __future__ import annotations

import subprocess
import sys
import time
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

# Add-Printer 失败后的重试参数
_ADD_PRINTER_MAX_RETRIES = 3
_ADD_PRINTER_RETRY_DELAYS = [2, 4, 6]  # 每次重试前等待秒数（递增）


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

    修复：使用 [Console]::OutputEncoding = [Text.Encoding]::UTF8 强制 UTF-8 输出，
    避免在 GBK 系统（同事电脑）上因编码不一致导致字符串匹配失效。
    """
    # 在脚本前注入编码设置，确保在任何系统代码页下输出都是 UTF-8
    utf8_prefix = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
    full_script = utf8_prefix + script

    cmd = [
        "powershell", "-NoProfile", "-NonInteractive",
        "-Command", full_script,
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
    script = f"Get-Printer -Name '{target.name}' -ErrorAction Stop | Out-String"
    proc = run_powershell(script)
    return proc.returncode == 0 and bool(proc.stdout.strip())


def install_driver(target: PrinterTarget) -> str | None:
    """确保驱动已安装，返回驱动名。

    修复1：驱动检查改用 returncode（而非 stdout 内容），
           Get-PrinterDriver 找不到驱动会返回非 0，不受 SilentlyContinue 影响。
    修复2：pnputil 成功判断补充"already exists/已存在"关键词，
           避免驱动已在 DriverStore 时被误判为失败后重复安装。
    """
    driver_name = DRIVER_NAME_MAP.get(target.driver_label)
    if not driver_name:
        return None

    # 1. 检查驱动是否已装（用 returncode 判断，不依赖 stdout 内容）
    check = run_powershell(
        f"Get-PrinterDriver -Name '{driver_name}' -ErrorAction Stop | Out-String"
    )
    if check.returncode == 0:
        return driver_name  # 已装，直接返回

    # 2. 未装 → 定位内嵌 inf
    inf_path = find_driver_inf(target.driver_label)
    if inf_path is None:
        return None  # 驱动资源未就位

    # 3. pnputil 安装 inf 到驱动库（静默、需管理员）
    #    退出码不可靠，必须看 stdout 判断真实结果。
    #    补充 "already exists/已存在"：驱动已在 DriverStore 时也算成功。
    pnputil_script = f"& pnputil /add-driver '{inf_path}' /install 2>&1 | Out-String"
    proc = run_powershell(pnputil_script)
    success_keywords = (
        "成功", "successfully", "Published Name", "oem",
        "already exists", "已存在",          # 驱动已在 DriverStore，也是成功
        "Driver package added",              # pnputil 英文成功消息
    )
    if not any(kw.lower() in proc.stdout.lower() for kw in success_keywords):
        return None  # pnputil 真失败

    # 4. Add-PrinterDriver 注册驱动到打印子系统
    #    不带 -InfPath：pnputil 已把驱动装进 DriverStore，按名字注册即可。
    register_script = (
        f"Add-PrinterDriver -Name '{driver_name}' -ErrorAction Stop | Out-String"
    )
    proc = run_powershell(register_script)
    if proc.returncode != 0:
        return None

    # 5. 重启 Print Spooler 刷新驱动缓存
    #    Add-PrinterDriver 注册驱动后，Spooler 的内部驱动缓存可能未及时更新，
    #    导致 Add-Printer 报 0x80070006（ERROR_INVALID_HANDLE）。
    #    重启 Spooler 强制重新加载所有驱动，彻底解决缓存问题。
    #    仅在"新装驱动"时执行（驱动已装时上面已 return，不会走到这里）。
    run_powershell("Stop-Service -Name Spooler -Force -ErrorAction SilentlyContinue")
    time.sleep(1)  # 等服务完全停止
    run_powershell("Start-Service -Name Spooler -ErrorAction SilentlyContinue")
    time.sleep(1)  # 等服务完全启动并加载驱动

    return driver_name


def _ensure_printer_port(port_name: str, ip: str) -> bool:
    """确保 TCP/IP 打印机端口存在，返回是否成功。

    修复：先检查端口是否已存在，不存在才创建。
    原来用 try/catch 吞掉创建失败，导致后续 Add-Printer 因端口不存在而报错。
    """
    # 先检查端口是否已存在
    check = run_powershell(
        f"Get-PrinterPort -Name '{port_name}' -ErrorAction SilentlyContinue | Out-String"
    )
    if check.returncode == 0 and check.stdout.strip():
        return True  # 端口已存在

    # 不存在则创建
    create = run_powershell(
        f"Add-PrinterPort -Name '{port_name}' "
        f"-PrinterHostAddress '{ip}' -ErrorAction Stop | Out-String"
    )
    return create.returncode == 0


def _add_printer_with_retry(target: PrinterTarget, driver_name: str) -> subprocess.CompletedProcess:
    """执行 Add-Printer，失败时最多重试 3 次。

    修复：Add-Printer 在驱动刚注册后立即调用可能因 Spooler 未就绪而报
    0x80070006（ERROR_INVALID_HANDLE）。加重试+递增延迟可规避时序问题。
    """
    port_name = f"IP_{target.ip}"
    add_cmd = (
        f"Add-Printer -Name '{target.name}' "
        f"-DriverName '{driver_name}' "
        f"-PortName '{port_name}' -ErrorAction Stop | Out-String"
    )

    last_proc: subprocess.CompletedProcess | None = None
    for attempt in range(_ADD_PRINTER_MAX_RETRIES):
        proc = run_powershell(add_cmd)
        last_proc = proc
        if proc.returncode == 0:
            return proc
        # 判断是否是可重试的错误（0x80070006 句柄无效 / 0x80070057 参数无效）
        retryable = "0x80070006" in proc.stderr or "0x80070057" in proc.stderr
        if not retryable or attempt == _ADD_PRINTER_MAX_RETRIES - 1:
            break
        wait = _ADD_PRINTER_RETRY_DELAYS[attempt]
        time.sleep(wait)

    return last_proc  # type: ignore


def add_printer(target: PrinterTarget) -> PrinterInstallResult:
    """完整添加流程：幂等检查 → 驱动 → 端口 → 打印机（含重试）。"""
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

    # 3. 确保端口存在
    port_name = f"IP_{target.ip}"
    port_ok = _ensure_printer_port(port_name, target.ip)
    if not port_ok:
        return PrinterInstallResult(
            printer_name=target.name, ok=False,
            message=f"创建打印机端口失败（{port_name} → {target.ip}）",
            error_code=-2,
        )

    # 4. Add-Printer（含重试）
    add_proc = _add_printer_with_retry(target, driver_name)
    if add_proc.returncode != 0:
        err_msg = add_proc.stderr.strip() or add_proc.stdout.strip() or "未知错误"
        return PrinterInstallResult(
            printer_name=target.name, ok=False,
            message=f"添加打印机失败: {err_msg}",
            raw_output=add_proc.stderr or add_proc.stdout,
            error_code=add_proc.returncode,
        )

    # 5. 最终验证（Add-Printer 返回 0 也不一定真成功，再确认一次）
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
