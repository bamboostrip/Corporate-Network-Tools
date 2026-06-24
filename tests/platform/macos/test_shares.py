"""macOS 扫描共享测试（Finder 别名 + Keychain 凭据）。全部 mock subprocess。"""
from unittest.mock import patch, MagicMock
from pathlib import Path

from route_tool.platform.macos.shares import (
    unc_to_smb, save_credential, create_finder_alias, add_scan_share,
)


# === unc_to_smb：UNC 路径转 SMB URL ===

def test_unc_to_smb_basic():
    r"""UNC 路径转 SMB URL：\\server\share → smb://server/share。"""
    assert unc_to_smb(r"\\192.168.0.210\shared\SMY") == "smb://192.168.0.210/shared/SMY"


def test_unc_to_smb_simple():
    assert unc_to_smb(r"\\server\share") == "smb://server/share"


# === save_credential：Keychain 凭据 ===

def test_save_credential_calls_security_command():
    """用 security add-internet-password 存凭据到 Keychain。"""
    with patch("route_tool.platform.macos.shares.subprocess.run",
               return_value=MagicMock(returncode=0)) as mock_run:
        ok = save_credential("192.168.0.210", "admin", "admin")
    assert ok is True
    args = mock_run.call_args[0][0]
    assert "security" in args
    assert "add-internet-password" in args
    assert "192.168.0.210" in args
    assert "admin" in args


def test_save_credential_updates_existing():
    """凭据已存在时先 delete 再 add（避免重复报错）。"""
    add_ok = MagicMock(returncode=0)
    with patch("route_tool.platform.macos.shares.subprocess.run",
               side_effect=[MagicMock(returncode=0), add_ok]):
        ok = save_credential("192.168.0.210", "admin", "admin")
    assert ok is True


def test_save_credential_failure():
    """security 命令失败返回 False。"""
    with patch("route_tool.platform.macos.shares.subprocess.run",
               return_value=MagicMock(returncode=1, stderr="拒绝访问")):
        ok = save_credential("192.168.0.210", "admin", "wrong")
    assert ok is False


# === create_finder_alias：创建 .app 快捷方式 ===

def test_create_finder_alias_uses_osacompile(tmp_path):
    """用 osacompile 编译 AppleScript 到 .app，双击 open smb://。"""
    with patch("route_tool.platform.macos.shares.subprocess.run",
               return_value=MagicMock(returncode=0)) as mock_run:
        ok = create_finder_alias("SMY扫描", "smb://192.168.0.210/shared/SMY", tmp_path)
    assert ok is True
    args = mock_run.call_args[0][0]
    assert "osacompile" in args
    # 产出 .app 路径
    app_path = tmp_path / "SMY扫描.app"
    assert any(str(app_path) in str(a) for a in args), "应指向 SMY扫描.app"


def test_create_finder_alias_failure(tmp_path):
    with patch("route_tool.platform.macos.shares.subprocess.run",
               return_value=MagicMock(returncode=1)):
        ok = create_finder_alias("SMY扫描", "smb://x/y", tmp_path)
    assert ok is False


# === add_scan_share：完整流程 ===

def test_add_scan_share_success():
    """完整添加：存凭据 + 建 Finder 别名。"""
    with patch("route_tool.platform.macos.shares.save_credential", return_value=True) as mock_cred, \
         patch("route_tool.platform.macos.shares.create_finder_alias", return_value=True) as mock_alias:
        result = add_scan_share(
            share_path=r"\\192.168.0.210\shared\SMY",
            user="admin", password="admin", display_name="SMY扫描",
        )
    assert result.ok is True
    mock_cred.assert_called_once()
    mock_alias.assert_called_once()


def test_add_scan_share_credential_failure():
    """凭据失败时整体失败，不建别名。"""
    with patch("route_tool.platform.macos.shares.save_credential", return_value=False), \
         patch("route_tool.platform.macos.shares.create_finder_alias", return_value=True) as mock_alias:
        result = add_scan_share(r"\\x\y", "u", "p", "name")
    assert result.ok is False
    mock_alias.assert_not_called()
