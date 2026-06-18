"""路由配置面板。

职责：
1. 显示当前网络环境（WiFi 名、本机 IP、网关 5.22 可达性）—— "当前网络"信息区
2. 显示目标路由信息（目标网段、网关）和路由状态
3. 提供"一键配置路由"按钮；5.22 不可达或路由已配置时禁用
4. 提供"重新检测"按钮，重新拉取网络环境

所有 backend 调用通过回调注入（避免 panel 直接依赖 backend 实例，便于测试）。
后台耗时操作（get_network_info、route_exists）在子线程跑，结果用 after() 回主线程。
"""
from __future__ import annotations

import threading
from typing import Callable

import customtkinter as ctk

from route_tool.core.config import DEFAULT_ROUTE, TARGET_CIDR, GATEWAY
from route_tool.core.models import NetworkInfo, Result, RouteInfo


class RoutePanel(ctk.CTkFrame):
    """路由配置区域。"""

    def __init__(
        self,
        master,
        on_get_network_info: Callable[[], NetworkInfo],
        on_check_route: Callable[[], bool],
        on_add_route: Callable[[RouteInfo], Result],
        on_log: Callable[[str, str], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._on_get_network_info = on_get_network_info
        self._on_check_route = on_check_route
        self._on_add_route = on_add_route
        self._on_log = on_log

        # 最近一次的网络信息与路由状态（用于联动判断按钮是否可用）
        self._network_info: NetworkInfo | None = None
        self._route_exists: bool | None = None

        # 标题
        self._title = ctk.CTkLabel(self, text="📡 网络路由配置", font=ctk.CTkFont(size=16, weight="bold"))
        self._title.pack(anchor="w", padx=20, pady=(15, 5))

        # === 当前网络信息区 ===
        net_frame = ctk.CTkFrame(self, fg_color="transparent")
        net_frame.pack(fill="x", padx=20, pady=5)

        self._wifi_label = ctk.CTkLabel(net_frame, text="WiFi:    检测中...", anchor="w")
        self._wifi_label.pack(anchor="w", pady=1)

        self._ip_label = ctk.CTkLabel(net_frame, text="本机IP:  检测中...", anchor="w")
        self._ip_label.pack(anchor="w", pady=1)

        # 5.22 状态行 + 重新检测按钮（同一行）
        gw_row = ctk.CTkFrame(net_frame, fg_color="transparent")
        gw_row.pack(fill="x", pady=1)
        gw_row.grid_columnconfigure(0, weight=1)

        self._gw_label = ctk.CTkLabel(
            gw_row, text=f"网关:    {GATEWAY}  🔄 检测中...", anchor="w"
        )
        self._gw_label.grid(row=0, column=0, sticky="w")

        self._recheck_btn = ctk.CTkButton(
            gw_row, text="重新检测", width=80, command=self.recheck_prerequisite
        )
        self._recheck_btn.grid(row=0, column=1, padx=(10, 0))

        # === 目标路由信息区 ===
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=(10, 5))

        self._net_label = ctk.CTkLabel(info_frame, text=f"目标网段:  {TARGET_CIDR}", anchor="w")
        self._net_label.pack(anchor="w", pady=2)

        self._gw2_label = ctk.CTkLabel(info_frame, text=f"网关:      {GATEWAY}", anchor="w")
        self._gw2_label.pack(anchor="w", pady=2)

        self._status_label = ctk.CTkLabel(info_frame, text="状态:      🔄 检测中...", anchor="w")
        self._status_label.pack(anchor="w", pady=2)

        # === 配置按钮 ===
        self._config_btn = ctk.CTkButton(
            self,
            text="一键配置路由",
            command=self._on_config_click,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            state="disabled",  # 初始禁用，预检 + 路由检测完成后决定
        )
        self._config_btn.pack(pady=15)

    # === 业务规则（纯逻辑，便于测试）===

    @staticmethod
    def can_configure(info: NetworkInfo, route_exists: bool) -> bool:
        """判断是否允许用户点击"一键配置路由"。

        规则：5.22 可达 且 路由尚未配置 才允许。
        """
        return info.gateway522_reachable and not route_exists

    # === 网络预检（异步）===

    def check_prerequisite_async(self) -> None:
        """启动时调用：后台拉取网络信息 + 路由状态，完成后更新 UI（必须主线程调用）。"""
        def worker():
            info = self._on_get_network_info()
            exists = self._on_check_route()
            self.after(0, lambda: self._on_prerequisite_done(info, exists))

        threading.Thread(target=worker, daemon=True).start()

    def recheck_prerequisite(self) -> None:
        """用户点"重新检测"：重新拉取网络信息和路由状态。"""
        self._recheck_btn.configure(state="disabled", text="检测中...")
        self._gw_label.configure(text=f"网关:    {GATEWAY}  🔄 检测中...")
        self._on_log("重新检测网络环境...", "info")
        self.check_prerequisite_async()

    def _on_prerequisite_done(self, info: NetworkInfo, route_exists: bool) -> None:
        self._network_info = info
        self._route_exists = route_exists
        self._update_network_info(info)
        self._update_route_status(route_exists)
        self._recheck_btn.configure(state="normal", text="重新检测")

    def _update_network_info(self, info: NetworkInfo) -> None:
        """更新当前网络信息区的显示（主线程调用）。"""
        self._wifi_label.configure(text=f"WiFi:    {info.wifi_name}")
        self._ip_label.configure(text=f"本机IP:  {info.local_ip}")
        gw_mark = "✓" if info.gateway522_reachable else "✗"
        self._gw_label.configure(
            text=f"网关:    {GATEWAY}  {gw_mark} {info.gateway522_message}"
        )
        if info.gateway522_reachable:
            self._on_log(
                f"网络环境: WiFi={info.wifi_name}, IP={info.local_ip}, 网关 {GATEWAY} 可达",
                "info",
            )
        else:
            self._on_log(
                f"⚠ 网关 {GATEWAY} 不可达（{info.gateway522_message}），"
                f"请确认已连接公司内网后重试",
                "warning",
            )

    def _update_route_status(self, exists: bool) -> None:
        """更新路由状态行，并据此 + 网络可达性决定按钮是否可用。"""
        if exists:
            self._status_label.configure(text="状态:      ✓ 已配置")
        else:
            self._status_label.configure(text="状态:      ⚠ 未配置")

        # 按钮启用 = can_configure（5.22 可达 且 路由未配置）
        if self._network_info is not None and self._route_exists is not None:
            if self.can_configure(self._network_info, self._route_exists):
                self._config_btn.configure(state="normal", text="一键配置路由")
                self._on_log("可配置路由，等待用户操作", "info")
            elif self._network_info.gateway522_reachable and exists:
                self._config_btn.configure(state="disabled", text="已配置，无需重复操作")
            elif not self._network_info.gateway522_reachable:
                self._config_btn.configure(state="disabled", text="网关不可达，无法配置")
            else:
                self._config_btn.configure(state="disabled", text="一键配置路由")

    # 兼容旧入口（app.py 可能调用 check_route_async）
    def check_route_async(self) -> None:
        """仅检测路由状态（不重新拉网络信息）。保留向后兼容。"""
        def worker():
            exists = self._on_check_route()
            self.after(0, lambda: self._update_route_status(exists))

        threading.Thread(target=worker, daemon=True).start()

    # === 配置路由（异步）===

    def _on_config_click(self) -> None:
        self._config_btn.configure(state="disabled", text="⏳ 配置中...")
        self._on_log("开始配置路由...", "info")

        def worker():
            result = self._on_add_route(DEFAULT_ROUTE)
            self.after(0, lambda: self._on_config_done(result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_config_done(self, result: Result) -> None:
        if result.ok:
            self._route_exists = True
            self._status_label.configure(text="状态:      ✓ 已配置")
            self._config_btn.configure(state="disabled", text="已配置，无需重复操作")
            self._on_log(f"✓ {result.message}", "success")
        else:
            self._status_label.configure(text="状态:      ✗ 配置失败")
            # 失败后恢复按钮（前提是 5.22 仍可达）
            if self._network_info and self._network_info.gateway522_reachable:
                self._config_btn.configure(state="normal", text="重新尝试配置")
            else:
                self._config_btn.configure(state="disabled", text="网关不可达")
            self._on_log(f"✗ {result.message}", "error")
            if result.raw_output:
                self._on_log(f"  诊断: {result.raw_output}", "debug")
