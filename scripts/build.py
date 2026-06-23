"""一键打包脚本。

产出：dist/公司网络配置工具.exe
- --onefile: 单文件
- --windowed: 无控制台（GUI 程序）
- --uac-admin: 内嵌管理员 manifest，双击即弹 UAC
- --collect-all customtkinter: CTk 主题资源必须手动收集
- --version-file: 从 pyproject.toml 读版本号生成

用法: uv run python scripts/build.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
ENTRY = ROOT / "src" / "route_tool" / "__main__.py"
ICON = ROOT / "assets" / "icon.ico"
VERSION_FILE = ROOT / "version_info.txt"
APP_NAME = "公司网络配置工具"


def read_version() -> str:
    """从 pyproject.toml 读取版本号。"""
    content = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise RuntimeError("无法从 pyproject.toml 读取 version")
    return match.group(1)


def write_version_file(version: str) -> None:
    """生成 PyInstaller 的 version_info.txt。

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
            StringStruct('FileDescription', '公司网络配置工具'),
            StringStruct('FileVersion', '{version}'),
            StringStruct('ProductName', '公司网络配置工具'),
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
    print(f"[build] 版本号: {version}")

    # 1. 同步依赖
    print("[build] 同步依赖...")
    subprocess.run(["uv", "sync"], check=True, cwd=ROOT)

    # 2. 生成 version_info.txt
    print("[build] 生成 version_info.txt...")
    write_version_file(version)

    # 3. 构建 PyInstaller 命令
    # 注意：不能用 "uv run pyinstaller"，uv 在 Windows 下传脚本路径会触发
    # PyInstaller 的 "Failed to canonicalize script path" 报错。
    # 改用当前 venv 的 python 直接调用 -m PyInstaller（sys.executable 即 venv python，
    # 因为本脚本由 uv run python 启动）。
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--uac-admin",
        "--name", APP_NAME,
        "--collect-all", "customtkinter",
        "--version-file", str(VERSION_FILE),
        # 打印机驱动（Windows 用，目录结构见 src/route_tool/drivers/README.md）
        "--add-data", "src/route_tool/drivers;route_tool/drivers",
    ]
    if ICON.exists():
        cmd.extend(["--icon", str(ICON)])
        print(f"[build] 使用图标: {ICON}")
    else:
        print("[build] 未找到 assets/icon.ico，使用默认图标")
    cmd.append(str(ENTRY))

    # 4. 执行打包
    print(f"[build] 执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"[build] ❌ 打包失败 (exit {result.returncode})", file=sys.stderr)
        return result.returncode

    exe = ROOT / "dist" / f"{APP_NAME}.exe"
    print(f"\n[build] ✅ 打包完成!")
    print(f"[build] 可执行文件: {exe}")
    if exe.exists():
        print(f"[build] 大小: {exe.stat().st_size / 1024 / 1024:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
