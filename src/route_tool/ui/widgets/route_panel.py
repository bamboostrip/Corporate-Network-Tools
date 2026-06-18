"""路由配置面板。

负责显示路由配置信息和状态，提供"一键配置路由"按钮。
所有 backend 调用通过回调注入（避免 panel 直接依赖 backend 实例，便于测试）。
"""
from __future__ import annotations

import threading
from typing import Callable

import customtkinter as ctk

from route_tool.core.config import DEFAULT_ROUTE, TARGET_CIDR, GATEWAY
from route_tool.core.models import Result, RouteInfo


class RoutePanel(ctk.CTkFrame):
    """路由配置区域。"""

    def __init__(
        self,
        master,
        on_check_route: Callable[[], bool],
        on_add_route: Callable[[RouteInfo], Result],
        on_log: Callable[[str, str], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._on_check_route = on_check_route
        self._on_add_route = on_add_route
        self._on_log = on_log

        # 标题
        self._title = ctk.CTkLabel(self, text="📡 网络路由配置", font=ctk.CTkFont(size=16, weight="bold"))
        self._title.pack(anchor="w", padx=20, pady=(15, 5))

        # 信息容器
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=5)

        self._net_label = ctk.CTkLabel(info_frame, text=f"目标网段:  {TARGET_CIDR}", anchor="w")
        self._net_label.pack(anchor="w", pady=2)

        self._gw_label = ctk.CTkLabel(info_frame, text=f"网关:      {GATEWAY}", anchor="w")
        self._gw_label.pack(anchor="w", pady=2)

        self._status_label = ctk.CTkLabel(info_frame, text="状态:      🔄 检测中...", anchor="w")
        self._status_label.pack(anchor="w", pady=2)

        # 配置按钮
        self._config_btn = ctk.CTkButton(
            self,
            text="一键配置路由",
            command=self._on_config_click,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            state="disabled",  # 初始禁用，检测完路由状态后再决定
        )
        self._config_btn.pack(pady=15)

    def check_route_async(self) -> None:
        """在后台线程检查路由状态，完成后更新 UI（必须从主线程调用）。"""
        def worker():
            exists = self._on_check_route()
            self.after(0, lambda: self._update_status(exists))

        threading.Thread(target=worker, daemon=True).start()

    def _update_status(self, exists: bool) -> None:
        if exists:
            self._status_label.configure(text="状态:      ✓ 已配置")
            self._config_btn.configure(state="disabled", text="已配置，无需重复操作")
            self._on_log("✓ 路由已存在，无需重复配置", "info")
        else:
            self._status_label.configure(text="状态:      ⚠ 未配置")
            self._config_btn.configure(state="normal", text="一键配置路由")
            self._on_log("⚠ 路由未配置，可点击按钮添加", "warning")

    def _on_config_click(self) -> None:
        self._config_btn.configure(state="disabled", text="⏳ 配置中...")
        self._on_log("开始配置路由...", "info")

        def worker():
            result = self._on_add_route(DEFAULT_ROUTE)
            self.after(0, lambda: self._on_config_done(result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_config_done(self, result: Result) -> None:
        if result.ok:
            self._status_label.configure(text="状态:      ✓ 已配置")
            self._config_btn.configure(state="disabled", text="已配置，无需重复操作")
            self._on_log(f"✓ {result.message}", "success")
        else:
            self._status_label.configure(text="状态:      ✗ 配置失败")
            self._config_btn.configure(state="normal", text="重新尝试配置")
            self._on_log(f"✗ {result.message}", "error")
            if result.raw_output:
                self._on_log(f"  诊断: {result.raw_output}", "debug")
