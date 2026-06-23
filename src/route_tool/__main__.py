"""程序入口。支持 `python -m route_tool` 和 PyInstaller 打包。

全局异常兜底：未捕获异常写 error.log + 弹窗提示用户截图发 IT。
"""
from __future__ import annotations

import datetime
import sys
import traceback
from pathlib import Path


def _write_error_log(exc: BaseException) -> Path:
    """把未捕获异常写入 exe 同目录的 error.log，返回文件路径。"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后，sys.argv[0] 是 exe 路径
        log_path = Path(sys.argv[0]).resolve().parent / "error.log"
    else:
        log_path = Path.cwd() / "error.log"
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    content = (
        f"=== {timestamp} 未捕获异常 ===\n"
        f"{traceback.format_exc()}\n"
        f"Platform: {sys.platform}\n"
        f"Python: {sys.version}\n"
        f"Executable: {sys.executable}\n"
    )
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(content + "\n")
    except OSError:
        pass  # 写日志失败不能掩盖原异常
    return log_path


def _show_fatal_error(exc: BaseException) -> None:
    """显示致命错误弹窗。"""
    log_path = _write_error_log(exc)
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "芜湖高景网络配置工具 - 出现错误",
            f"程序出现未预期错误，请联系 祁恒 处理。\n\n"
            f"错误: {exc}\n\n"
            f"诊断日志已保存到:\n{log_path}",
        )
        root.destroy()
    except Exception:
        # GUI 都起不来时，退化到控制台输出
        print(f"FATAL: {exc}", file=sys.stderr)
        traceback.print_exc()


def main() -> int:
    """程序主入口。"""
    try:
        from route_tool.ui.app import run_app
        run_app()
        return 0
    except SystemExit:
        raise
    except BaseException as exc:
        _show_fatal_error(exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
