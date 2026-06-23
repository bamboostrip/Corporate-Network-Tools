"""主窗口：组装各 panel，注入 backend 回调，管理主题。

UI 层只依赖 contracts（通过 platform 工厂获取 backend），不直接 import 后端实现。
布局：所有内容放进 CTkScrollableFrame，解决 150% 缩放下显示不全、不能滚动的问题。
顶部是"一键快捷部署"大按钮，下面是各分模块面板（高级用户和故障排查用）。
"""
from __future__ import annotations

import customtkinter as ctk

from route_tool.core.config import DEFAULT_ROUTE
from route_tool.core.contracts import PlatformBackend
from route_tool.core.deploy import DeployOrchestrator
from route_tool.core.errors import UnsupportedOSError
from route_tool.platform import get_backend
from route_tool.ui.widgets.deploy_bar import DeployBar
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
        self._orchestrator: DeployOrchestrator | None = None

        self.title("公司网络配置工具")
        # 窗口尺寸：宽度收紧到 620（内容不宽），高度 720（150% 缩放下也能显示）
        # 内容超出时靠 CTkScrollableFrame 滚动，不再依赖大窗口高度
        self.geometry("620x760")
        self.minsize(540, 560)

        # 主题：跟随系统
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # 主布局：一个可滚动容器装下全部内容
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_frame.grid(row=0, column=0, sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)
        self._scroll_frame = scroll_frame

        # === 先创建各分模块面板（部署栏和联动需要引用它们）===
        # 打印机和共享面板需先于路由面板创建（路由面板要传联动回调给它们）
        self._printer_panel = PrinterPanel(
            scroll_frame,
            on_add_printer=self._backend.add_printer,
            on_check_printer=self._backend.printer_exists,
            on_log=self._log,
        )

        self._share_panel = SharePanel(
            scroll_frame,
            on_add_share=self._backend.add_scan_share,
            on_log=self._log,
        )

        self._route_panel = RoutePanel(
            scroll_frame,
            on_get_network_info=self._backend.get_network_info,
            on_check_route=self._check_route,
            on_add_route=self._backend.add_route,
            on_log=self._log,
            on_gateway_state_change=self._on_gateway_state_change,
        )

        self._test_panel = TestPanel(
            scroll_frame,
            on_ping=self._backend.ping,
            on_log=self._log,
        )

        self._log_panel = LogPanel(scroll_frame)

        # === 一键部署栏（最顶部）===
        self._orchestrator = DeployOrchestrator(
            backend=self._backend,
            on_progress=self._on_deploy_progress,
            on_log=self._log,
        )
        self._deploy_bar = DeployBar(
            scroll_frame,
            on_deploy=self._orchestrator.run_full_deploy,
            on_log=self._log,
            on_progress=lambda *a: None,  # 进度通过 _on_deploy_progress 主线程回调更新
            on_done=self._on_deploy_done,
        )

        # === 按顺序 grid 到滚动容器 ===
        # 顺序：部署栏 → 路由 → 测试 → 打印机 → 共享 → 日志
        self._deploy_bar.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        self._route_panel.grid(row=1, column=0, padx=0, pady=(8, 0), sticky="ew")
        self._test_panel.grid(row=2, column=0, padx=0, pady=8, sticky="ew")
        self._printer_panel.grid(row=3, column=0, padx=0, pady=0, sticky="ew")
        self._share_panel.grid(row=4, column=0, padx=0, pady=8, sticky="ew")
        self._log_panel.grid(row=5, column=0, padx=0, pady=(0, 8), sticky="ew")

        # 启动后自动检测网络环境（WiFi/IP/5.22 可达性）+ 路由状态
        self.after(100, self._route_panel.check_prerequisite_async)

    def _check_route(self) -> bool:
        """路由检查的封装（route_exists 需要 RouteInfo 参数，这里固定用 DEFAULT_ROUTE）。"""
        return self._backend.route_exists(DEFAULT_ROUTE)

    def _log(self, message: str, level: str = "info") -> None:
        """日志回调，转发给 LogPanel。"""
        if self._log_panel is not None:
            self._log_panel.append(message, level)

    def _on_gateway_state_change(self, reachable: bool) -> None:
        """网络状态变化时联动打印机面板和共享面板的按钮启用状态。"""
        self._printer_panel.update_gateway_state(reachable)
        self._share_panel.update_gateway_state(reachable)

    def _on_deploy_progress(self, step: int, total: int, desc: str) -> None:
        """部署进度回调（在后台线程被调用）→ 回主线程更新 UI。"""
        self.after(0, lambda: self._deploy_bar.update_progress(step, total, desc))

    def _on_deploy_done(self, result) -> None:
        """部署完成后，刷新各分模块面板状态（让用户看到每项的实际状态）。"""
        # 重新检测路由和网络环境（更新路由面板显示 + 触发按钮联动）
        self._route_panel.check_prerequisite_async()
        # 刷新打印机面板每行的状态（已添加的显示"已添加"）
        self._refresh_printer_panel_status()

    def _refresh_printer_panel_status(self) -> None:
        """后台检查每台打印机的实际添加状态，更新 PrinterPanel UI。"""
        import threading
        from route_tool.core.config import PRINTER_DEFS

        def worker():
            for target in PRINTER_DEFS:
                exists = self._backend.printer_exists(target)
                # 用 after 回主线程更新 UI
                self.after(0, lambda t=target, e=exists: self._update_printer_row(t, e))

        threading.Thread(target=worker, daemon=True).start()

    def _update_printer_row(self, target, exists: bool) -> None:
        """主线程：根据打印机实际状态更新 PrinterPanel 的对应行。"""
        from route_tool.core.models import PrinterInstallResult
        row = self._printer_panel._rows.get(target.name)
        if row and exists:
            row.set_result(PrinterInstallResult(
                printer_name=target.name, ok=True, already_exists=True,
                message=f"{target.name} 已添加",
            ))


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
