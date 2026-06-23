"""主窗口：组装各 panel，注入 backend 回调，管理主题。

UI 层只依赖 contracts（通过 platform 工厂获取 backend），不直接 import 后端实现。
"""
from __future__ import annotations

import customtkinter as ctk

from route_tool.core.config import DEFAULT_ROUTE
from route_tool.core.contracts import PlatformBackend
from route_tool.core.errors import UnsupportedOSError
from route_tool.platform import get_backend
from route_tool.ui.widgets.log_panel import LogPanel
from route_tool.ui.widgets.printer_panel import PrinterPanel
from route_tool.ui.widgets.route_panel import RoutePanel
from route_tool.ui.widgets.share_panel import SharePanel
from route_tool.ui.widgets.test_panel import TestPanel


class MainApp(ctk.CTk):
    """主应用窗口。"""

    def __init__(self, backend: PlatformBackend):
        super().__init__()
        self._backend = backend

        self.title("公司网络配置工具")
        self.geometry("620x960")
        self.minsize(560, 820)

        # 主题：跟随系统
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # 布局：五个区域用 grid，日志区占主要可拉伸空间（weight=3），
        # 上面的路由/测试/打印机/共享区按内容高度自适应（weight=0，不抢空间）。
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # 路由面板
        self.grid_rowconfigure(1, weight=0)  # 测试面板
        self.grid_rowconfigure(2, weight=0)  # 打印机面板
        self.grid_rowconfigure(3, weight=0)  # 共享面板
        self.grid_rowconfigure(4, weight=3)  # 日志面板（拉伸）

        # 打印机和共享面板需先于路由面板创建（路由面板要传联动回调给它们）
        self._printer_panel = PrinterPanel(
            self,
            on_add_printer=self._backend.add_printer,
            on_check_printer=self._backend.printer_exists,
            on_log=self._log,
        )
        self._printer_panel.grid(row=2, column=0, padx=15, pady=4, sticky="ew")

        self._share_panel = SharePanel(
            self,
            on_add_share=self._backend.add_scan_share,
            on_log=self._log,
        )
        self._share_panel.grid(row=3, column=0, padx=15, pady=4, sticky="ew")

        self._route_panel = RoutePanel(
            self,
            on_get_network_info=self._backend.get_network_info,
            on_check_route=self._check_route,
            on_add_route=self._backend.add_route,
            on_log=self._log,
            on_gateway_state_change=self._on_gateway_state_change,
        )
        self._route_panel.grid(row=0, column=0, padx=15, pady=(12, 4), sticky="ew")

        self._test_panel = TestPanel(
            self,
            on_ping=self._backend.ping,
            on_log=self._log,
        )
        self._test_panel.grid(row=1, column=0, padx=15, pady=4, sticky="ew")

        self._log_panel = LogPanel(self)
        self._log_panel.grid(row=4, column=0, padx=15, pady=(4, 12), sticky="nsew")

        # 启动后自动检测网络环境（WiFi/IP/5.22 可达性）+ 路由状态
        self.after(100, self._route_panel.check_prerequisite_async)

    def _on_gateway_state_change(self, reachable: bool) -> None:
        """网络状态变化时联动打印机面板和共享面板的按钮启用状态。"""
        self._printer_panel.update_gateway_state(reachable)
        self._share_panel.update_gateway_state(reachable)

    def _check_route(self) -> bool:
        """路由检查的封装（route_exists 需要 RouteInfo 参数，这里固定用 DEFAULT_ROUTE）。"""
        return self._backend.route_exists(DEFAULT_ROUTE)

    def _log(self, message: str, level: str = "info") -> None:
        """日志回调，转发给 LogPanel。"""
        if self._log_panel is not None:
            self._log_panel.append(message, level)


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
