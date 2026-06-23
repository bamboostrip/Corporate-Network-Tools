"""Windows 扫描共享网络位置添加测试。全部 mock subprocess。"""
from unittest.mock import patch, MagicMock
from pathlib import Path

from route_tool.platform.windows.shares import (
    save_credential, create_network_location, add_scan_share,
    network_shortcuts_dir, build_cmdkey_command,
)


# === build_cmdkey_command：构造凭据命令 ===

def test_build_cmdkey_command():
    """构造 cmdkey 命令存凭据。"""
    cmd = build_cmdkey_command(
        server="192.168.0.210", user="admin", password="admin"
    )
    assert "cmdkey" in cmd
    assert "/add" in cmd
    assert "192.168.0.210" in cmd
    assert "admin" in cmd  # 用户名
    # 密码在 /pass 参数里
    assert "/pass" in cmd


# === save_credential ===

def test_save_credential_success():
    """cmdkey 成功存凭据。"""
    mock = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.windows.shares.subprocess.run", return_value=mock) as mock_run:
        ok = save_credential("192.168.0.210", "admin", "admin")
    assert ok is True
    mock_run.assert_called_once()


def test_save_credential_failure():
    """cmdkey 失败返回 False。"""
    mock = MagicMock(returncode=1, stdout="", stderr="拒绝访问")
    with patch("route_tool.platform.windows.shares.subprocess.run", return_value=mock):
        ok = save_credential("192.168.0.210", "admin", "wrong")
    assert ok is False


def test_save_credential_hides_console():
    """cmdkey 调用必须隐藏控制台窗口。"""
    import sys
    if sys.platform != "win32":
        import pytest
        pytest.skip("仅验证 Windows")
    mock = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.windows.shares.subprocess.run", return_value=mock) as mock_run:
        save_credential("1.2.3.4", "u", "p")
    kwargs = mock_run.call_args[1]
    assert "creationflags" in kwargs or "startupinfo" in kwargs


# === network_shortcuts_dir ===

def test_network_shortcuts_dir_under_appdata():
    r"""网络位置目录在 %AppData%\Microsoft\Windows\Network Shortcuts。"""
    import os
    d = network_shortcuts_dir()
    assert "Network Shortcuts" in str(d)
    # 应该基于 APPDATA 环境变量
    appdata = os.environ.get("APPDATA", "")
    assert appdata.lower() in str(d).lower()


# === create_network_location ===

def test_create_network_location_creates_lnk_file(tmp_path):
    """创建网络位置：直接生成 .lnk 快捷方式文件（双击直接打开 UNC）。

    不是文件夹套 target.lnk，而是 Network Shortcuts 目录下直接的 .lnk。
    这是 Windows "添加网络位置向导"的实际行为。
    """
    with patch("route_tool.platform.windows.shares.network_shortcuts_dir", return_value=tmp_path):
        ok = create_network_location(
            name="SMY扫描", target=r"\\192.168.0.210\shared\SMY"
        )
    assert ok is True
    # 直接是 .lnk 文件（不是文件夹）
    lnk = tmp_path / "SMY扫描.lnk"
    assert lnk.is_file()
    # 不应有 desktop.ini（那是文件夹方式才有的）
    assert not (tmp_path / "SMY扫描").is_dir()


def test_create_network_location_idempotent(tmp_path):
    """重复创建同名网络位置应成功（幂等，.lnk 覆盖）。"""
    with patch("route_tool.platform.windows.shares.network_shortcuts_dir", return_value=tmp_path):
        ok1 = create_network_location("SMY扫描", r"\\192.168.0.210\shared\SMY")
        ok2 = create_network_location("SMY扫描", r"\\192.168.0.210\shared\SMY")
    assert ok1 is True
    assert ok2 is True
    # 只有一个 lnk 文件
    assert (tmp_path / "SMY扫描.lnk").is_file()


# === add_scan_share：完整流程 ===

def test_add_scan_share_success():
    """完整添加：存凭据 + 建网络位置。"""
    with patch("route_tool.platform.windows.shares.save_credential", return_value=True) as mock_cred, \
         patch("route_tool.platform.windows.shares.create_network_location", return_value=True) as mock_loc:
        result = add_scan_share(
            share_path=r"\\192.168.0.210\shared\SMY",
            user="admin", password="admin", display_name="SMY扫描",
        )
    assert result.ok is True
    mock_cred.assert_called_once()
    mock_loc.assert_called_once()


def test_add_scan_share_credential_failure():
    """凭据失败时整体失败。"""
    with patch("route_tool.platform.windows.shares.save_credential", return_value=False), \
         patch("route_tool.platform.windows.shares.create_network_location", return_value=True) as mock_loc:
        result = add_scan_share(r"\\x\y", "u", "p", "name")
    assert result.ok is False
    mock_loc.assert_not_called()  # 凭据失败不应继续建网络位置
