r"""Windows 扫描文件共享的"网络位置"添加。

两步：
1. cmdkey 存凭据（admin/admin）→ 用户访问共享不弹密码框
2. 在 %AppData%\Microsoft\Windows\Network Shortcuts\ 下创建文件夹
   （含 desktop.ini + target.lnk）→ 资源管理器导航栏出现"网络位置"

这就是 Windows "添加网络位置向导"做的事，不占盘符。
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from route_tool.core.models import ShareInstallResult
from route_tool.platform.windows.subprocess_utils import no_window_kwargs


def network_shortcuts_dir() -> Path:
    r"""返回当前用户的"网络位置"目录。

    位置：%AppData%\Microsoft\Windows\Network Shortcuts
    放在这里的文件夹会出现在资源管理器导航栏的"网络位置"下。
    """
    appdata = os.environ.get("APPDATA", "")
    return Path(appdata) / "Microsoft" / "Windows" / "Network Shortcuts"


def build_cmdkey_command(server: str, user: str, password: str) -> str:
    """构造 cmdkey 存凭据的命令字符串。

    用字符串形式（由 run_powershell 或直接 subprocess 执行）。
    """
    # 注意：密码含特殊字符时用单引号包裹；server 用主机名/IP
    return f"cmdkey /add:{server} /user:{user} /pass:{password}"


def save_credential(server: str, user: str, password: str) -> bool:
    """用 cmdkey 存凭据到 Windows 凭据管理器。

    成功返回 True。之后访问 \\\\server\\share 不会弹密码框。
    """
    cmd = ["cmdkey", f"/add:{server}", f"/user:{user}", f"/pass:{password}"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            **no_window_kwargs(),
        )
        return proc.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def create_network_location(name: str, target: str) -> bool:
    """在资源管理器"网络位置"下创建一个快捷方式。

    name: 显示名（如 "SMY扫描"）
    target: UNC 路径（如 \\\\192.168.0.210\\shared\\SMY）

    实现：在 Network Shortcuts 目录直接创建 <name>.lnk 快捷方式文件，
    TargetPath 指向 UNC。双击直接打开 UNC 路径（和 Windows "添加网络位置向导"
    行为一致），不是文件夹套 target.lnk。
    """
    shortcuts_dir = network_shortcuts_dir()
    try:
        shortcuts_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    lnk_path = shortcuts_dir / f"{name}.lnk"
    try:
        # 用 WScript.Shell COM 对象创建 .lnk 快捷方式
        # 必须用 PowerShell 执行（COM 调用），路径含中文/反斜杠用单引号包裹
        ps_script = (
            f"$ws = New-Object -ComObject WScript.Shell; "
            f"$lnk = $ws.CreateShortcut('{lnk_path}'); "
            f"$lnk.TargetPath = '{target}'; "
            f"$lnk.WindowStyle = 1; "
            f"$lnk.Description = 'SMY scan share'; "
            f"$lnk.Save()"
        )
        cmd = [
            "powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            **no_window_kwargs(),
        )
        if proc.returncode != 0:
            return False
    except (subprocess.SubprocessError, OSError):
        return False

    return True


def add_scan_share(
    share_path: str, user: str, password: str, display_name: str
) -> ShareInstallResult:
    """完整添加扫描共享：存凭据 + 建网络位置。

    幂等：网络位置同名时覆盖（不报错）。
    """
    # 1. 从 UNC 路径提取 server（用于 cmdkey）
    # \\\\192.168.0.210\\shared\\SMY → 192.168.0.210
    server = share_path.lstrip("\\").split("\\")[0] if "\\" in share_path else share_path

    # 2. 存凭据
    if not save_credential(server, user, password):
        return ShareInstallResult(
            share_name=display_name, ok=False,
            message=f"凭据保存失败（{server}），请检查账号密码或权限",
            error_code=-1,
        )

    # 3. 建网络位置
    if not create_network_location(display_name, share_path):
        return ShareInstallResult(
            share_name=display_name, ok=False,
            message="网络位置创建失败",
            error_code=-1,
        )

    return ShareInstallResult(
        share_name=display_name, ok=True,
        message=f"{display_name} 已添加到网络位置（{share_path}）",
    )
