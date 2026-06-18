"""主窗口：组装各 panel，注入 backend 回调，管理主题。

UI 层只依赖 contracts（通过 platform 工厂获取 backend），不直接 import 后端实现。
"""
from __future__ import annotations

import customtkinter as ctk

from route_tool.core.config import DEFAULT_ROUTE
from route_tool.core.contracts import PlatformBackend
from route_tool.core.errors import UnsupportedOSError
from route_tool.platform import get_backend
from route_tool.ui.widgets.route_panel import RoutePanel


class MainApp(ctk.CTk):
    """主应用窗口。"""

    def __init__(self, backend: PlatformBackend):
        super().__init__()
        self._backend = backend

        self.title("公司网络配置工具")
        self.geometry("600x700")
        self.minsize(500, 600)

        # 主题：跟随系统
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # 布局
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # 日志区可拉伸

        self._route_panel = RoutePanel(
            self,
            on_check_route=self._check_route,
            on_add_route=self._backend.add_route,
            on_log=self._log,
        )
        self._route_panel.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # TestPanel 和 LogPanel 在 Task 12 添加，先用占位
        self._test_panel = None
        self._log_panel = None

        # 启动后自动检测路由状态
        self.after(100, self._route_panel.check_route_async)

    def _check_route(self) -> bool:
        """路由检查的封装（route_exists 需要 RouteInfo 参数，这里固定用 DEFAULT_ROUTE）。"""
        return self._backend.route_exists(DEFAULT_ROUTE)

    def _log(self, message: str, level: str = "info") -> None:
        """日志回调。Task 12 实现 LogPanel 后会转发给它。"""
        # 占位：Task 12 会替换为 self._log_panel.append(message, level)
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{level}] {message}")


def run_app() -> None:
    """程序入口：创建 backend 和主窗口，启动事件循环。"""
    try:
        backend = get_backend()
    except UnsupportedOSError as e:
        # 不支持的系统，弹窗提示
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("不支持的系统", str(e))
        root.destroy()
        return

    app = MainApp(backend)
    app.mainloop()
