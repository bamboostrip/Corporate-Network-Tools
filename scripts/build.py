"""一键打包脚本（跨平台：Windows 产出 .exe，macOS 产出 .app）。

通用参数：
- --onefile: 单文件
- --windowed: 无控制台（GUI 程序）
- --collect-all customtkinter: CTk 主题资源必须手动收集
- --add-data: 打印机驱动目录

平台差异：
- Windows: --uac-admin（UAC manifest）+ --version-file + .ico 图标 + --add-data 用 ; 分隔
- macOS: 无提权参数（用 osascript 运行时弹授权框）+ .icns 图标(可选) + --add-data 用 : 分隔

注意：PyInstaller 不支持交叉编译，必须在目标平台上运行本脚本。
  - 打 Windows 版：在 Windows 上运行
  - 打 macOS 版：在 Mac 上运行

用法: uv run python scripts/build.py
"""
from __future__ import annotations

import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
ENTRY = ROOT / "src" / "route_tool" / "__main__.py"
ICON_WIN = ROOT / "assets" / "icon.ico"      # Windows 图标
ICON_MAC = ROOT / "assets" / "icon.icns"      # macOS 图标（可选）
VERSION_FILE = ROOT / "version_info.txt"
DRIVERS_DIR = ROOT / "src" / "route_tool" / "drivers"  # 打印机驱动目录（绝对路径）
APP_NAME = "芜湖高景网络配置工具"

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
# --add-data 分隔符：Windows 用 ;，macOS/Linux 用 :
DATA_SEP = ";" if IS_WINDOWS else ":"


def read_version() -> str:
    """从 pyproject.toml 读取版本号。"""
    content = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise RuntimeError("无法从 pyproject.toml 读取 version")
    return match.group(1)


def write_version_file(version: str) -> None:
    """生成 PyInstaller 的 version_info.txt（仅 Windows 用）。

    Windows 版本号必须是 4 段数字（x.y.z.w），不足补 0。
    """
    parts = (version.split(".") + ["0"] * 4)[:4]
    numeric_tuple = ", ".join(parts)
    content = f"""# UTF-8
#
# PyInstaller 版本信息文件
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({numeric_tuple}),
    prodvers=({numeric_tuple}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', '公司 IT 部'),
            StringStruct('FileDescription', '芜湖高景网络配置工具'),
            StringStruct('FileVersion', '{version}'),
            StringStruct('ProductName', '芜湖高景网络配置工具'),
            StringStruct('ProductVersion', '{version}'),


          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [0x409, 1200])])
  ]
)
"""
    VERSION_FILE.write_text(content, encoding="utf-8")


def main() -> int:
    version = read_version()
    current_os = platform.system()
    print(f"[build] 版本号: {version}")
    print(f"[build] 当前平台: {current_os} ({'Windows .exe' if IS_WINDOWS else 'macOS .app' if IS_MACOS else '未知'})")

    # 1. 同步依赖
    print("[build] 同步依赖...")
    subprocess.run(["uv", "sync"], check=True, cwd=ROOT)

    # 2. 生成 version_info.txt（仅 Windows）
    if IS_WINDOWS:
        print("[build] 生成 version_info.txt...")
        write_version_file(version)

    # 3. 删除旧 .spec 文件，避免 PyInstaller 读取旧配置里的 datas 覆盖 --add-data 参数
    old_spec = ROOT / f"{APP_NAME}.spec"
    if old_spec.exists():
        old_spec.unlink()
        print(f"[build] 已删除旧 .spec 文件: {old_spec.name}")

    # 4. 构建 PyInstaller 命令（平台通用部分）
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--clean",
        "--name", APP_NAME,
        "--collect-all", "customtkinter",
        # 打印机驱动（分隔符按平台区分）
        "--add-data", f"{DRIVERS_DIR}{DATA_SEP}route_tool/drivers",
    ]

    # 5. 平台专有参数
    if IS_WINDOWS:
        # Windows: UAC 提权 + 版本信息 + 图标
        cmd.extend([
            "--uac-admin",
            "--version-file", str(VERSION_FILE),
        ])
        if ICON_WIN.exists():
            cmd.extend(["--icon", str(ICON_WIN)])
            print(f"[build] 使用图标: {ICON_WIN}")
        else:
            print("[build] 未找到 assets/icon.ico，使用默认图标")
    elif IS_MACOS:
        # macOS: 无 UAC（运行时用 osascript 弹授权框），可选 .icns 图标
        if ICON_MAC.exists():
            cmd.extend(["--icon", str(ICON_MAC)])
            print(f"[build] 使用图标: {ICON_MAC}")
        else:
            print("[build] 未找到 assets/icon.icns，使用默认图标")
        # macOS 打包成 .app 需要额外参数（osx-bundle-identifier）
        cmd.extend(["--osx-bundle-identifier", "com.company.network-config-tool"])

    cmd.append(str(ENTRY))

    # 6. 执行打包前验证驱动目录
    if not DRIVERS_DIR.is_dir():
        print(f"[build] [FAIL] 驱动目录不存在: {DRIVERS_DIR}", file=sys.stderr)
        return 1
    driver_files = list(DRIVERS_DIR.rglob("*"))
    driver_mb = sum(f.stat().st_size for f in driver_files if f.is_file()) / 1024 / 1024
    print(f"[build] 驱动目录已确认: {DRIVERS_DIR} ({driver_mb:.1f} MB, {len(driver_files)} 个文件)")

    # 7. 执行打包
    print(f"[build] 执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"[build] [FAIL] 打包失败 (exit {result.returncode})", file=sys.stderr)
        return result.returncode

    # 8. 验证产出
    if IS_WINDOWS:
        exe = ROOT / "dist" / f"{APP_NAME}.exe"
        print(f"\n[build] [OK] 打包完成!")
        print(f"[build] 可执行文件: {exe}")
        if exe.exists():
            size_mb = exe.stat().st_size / 1024 / 1024
            print(f"[build] 大小: {size_mb:.1f} MB")
    else:
        app = ROOT / "dist" / f"{APP_NAME}.app"
        print(f"\n[build] [OK] 打包完成!")
        print(f"[build] 应用程序: {app}")
        if app.exists():
            print(f"[build] [OK] .app 已生成")

    return 0


if __name__ == "__main__":
    sys.exit(main())
