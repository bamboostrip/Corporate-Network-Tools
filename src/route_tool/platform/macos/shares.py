"""macOS 扫描文件共享：Finder 别名 + Keychain 凭据。

macOS 没有 Windows 的"网络位置"概念，用两种方式实现等价效果：
1. Keychain 存 SMB 凭据（security add-internet-password）→ 免每次输密码
2. 在桌面创建 .app 快捷方式（osacompile 编译 AppleScript）→ 双击打开 smb:// 共享

AppleScript 内容：on run → open location "smb://server/share"
编译成 .app 后，Finder 里显示为可双击的应用图标。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from route_tool.core.models import ShareInstallResult


def unc_to_smb(unc_path: str) -> str:
    r"""UNC 路径转 SMB URL：\\server\share\dir → smb://server/share/dir。

    macOS 访问 SMB 共享用 smb:// URL（Finder → 前往 → 连接服务器）。
    """
    # 去掉开头的反斜杠，反斜杠转正斜杠
    normalized = unc_path.replace("\\", "/").lstrip("/")
    return f"smb://{normalized}"


def save_credential(server: str, user: str, password: str) -> bool:
    """用 security 命令存 SMB 凭据到 Keychain。

    先 delete（忽略"不存在"错误），再 add，保证幂等。
    """
    # 先尝试删除旧凭据（不存在会报错，忽略）
    subprocess.run(
        ["security", "delete-internet-password", "-s", server, "-a", user],
        capture_output=True, text=True, timeout=5,
    )
    # 添加新凭据
    try:
        proc = subprocess.run(
            [
                "security", "add-internet-password",
                "-s", server,        # server（对应 SMB 主机）
                "-a", user,          # account（用户名）
                "-w", password,      # password
                "-r", "smb",         # protocol
                "-U",                # 始终在 Keychain Access 中显示
            ],
            capture_output=True, text=True, timeout=5,
        )
        return proc.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def create_finder_alias(name: str, smb_url: str, dest_dir: Path) -> bool:
    """创建 Finder 快捷方式（.app），双击打开 SMB 共享。

    用 osacompile 编译 AppleScript 到 .app。脚本内容是 open location。
    放在 dest_dir（通常桌面），用户双击即连接 SMB 共享。
    """
    app_path = dest_dir / f"{name}.app"
    # AppleScript：运行时打开 smb:// URL
    # 用单引号包裹 URL 避免 shell 转义问题
    script = (
        f'on run\n'
        f'  open location "{smb_url}"\n'
        f'end run'
    )
    try:
        proc = subprocess.run(
            ["osacompile", "-o", str(app_path), "-e", script],
            capture_output=True, text=True, timeout=10,
        )
        return proc.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def add_scan_share(
    share_path: str, user: str, password: str, display_name: str
) -> ShareInstallResult:
    """完整添加扫描共享：存凭据 + 建 Finder 别名。幂等。"""
    # 1. UNC → SMB URL
    smb_url = unc_to_smb(share_path)

    # 2. 提取 server（用于 Keychain）
    server = share_path.lstrip("\\").split("\\")[0] if "\\" in share_path else share_path

    # 3. 存凭据
    if not save_credential(server, user, password):
        return ShareInstallResult(
            share_name=display_name, ok=False,
            message=f"凭据保存失败（{server}），请检查账号密码",
            error_code=-1,
        )

    # 4. 建 Finder 别名（放在桌面）
    desktop = Path.home() / "Desktop"
    if not create_finder_alias(display_name, smb_url, desktop):
        return ShareInstallResult(
            share_name=display_name, ok=False,
            message="Finder 快捷方式创建失败",
            error_code=-1,
        )

    return ShareInstallResult(
        share_name=display_name, ok=True,
        message=f"{display_name} 已添加到桌面（{smb_url}）",
    )
