"""扫描共享网络位置面板。

显示"添加 SMY 扫描"按钮，点击后存凭据 + 建网络位置。
5.22 不可达时按钮禁用（跨网段路由未配，SMB 访问不通）。
操作在后台线程跑，结果用 after() 回主线程。
"""
from __future__ import annotations

import threading
from typing import Callable

import customtkinter as ctk

from route_tool.core.config import SCAN_SHARE_PATH
from route_tool.core.models import ShareInstallResult


class SharePanel(ctk.CTkFrame):
    """扫描共享管理区域。"""

    __test__ = False  # pytest 不要误判为测试类

    def __init__(
        self,
        master,
        on_add_share: Callable[[], ShareInstallResult],
        on_log: Callable[[str, str], None],
        gateway_reachable: bool = False,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._on_add_share = on_add_share
        self._on_log = on_log
        self._gateway_reachable = gateway_reachable

        self._title = ctk.CTkLabel(
            self, text="📁 扫描文件共享", font=ctk.CTkFont(size=16, weight="bold")
        )
        self._title.pack(anchor="w", padx=15, pady=(10, 4))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=(0, 10))
        row.grid_columnconfigure(1, weight=1)

        self._desc = ctk.CTkLabel(
            row, text=f"SMY扫描共享  {SCAN_SHARE_PATH}", anchor="w",
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self._desc.grid(row=0, column=0, columnspan=2, padx=(0, 8), pady=2, sticky="w")

        self._status = ctk.CTkLabel(row, text="未添加", width=90, anchor="w")
        self._status.grid(row=1, column=0, padx=(0, 8), pady=2, sticky="w")

        self._btn = ctk.CTkButton(
            row, text="添加", width=80, height=28,
            command=self.add_share_async,
        )
        self._btn.grid(row=1, column=1, padx=0, pady=2, sticky="e")

        self._update_button_state()

    @staticmethod
    def can_add_share(gateway_reachable: bool) -> bool:
        """是否允许添加：5.22 可达才允许（跨网段 SMB 访问前提）。"""
        return gateway_reachable

    def update_gateway_state(self, reachable: bool) -> None:
        """路由面板检测完后调用，更新按钮启用状态。"""
        self._gateway_reachable = reachable
        self._update_button_state()

    def _update_button_state(self) -> None:
        if self._btn.cget("text") == "已添加":
            return  # 已添加的保持禁用
        self._btn.configure(state="normal" if self._gateway_reachable else "disabled")

    def add_share_async(self) -> None:
        """后台添加扫描共享。"""
        if not self.can_add_share(self._gateway_reachable):
            self._on_log("⚠ 网关不可达，无法添加扫描共享，请先配置路由", "warning")
            return

        self._status.configure(text="添加中...")
        self._btn.configure(state="disabled")
        self._on_log(f"开始添加扫描共享（{SCAN_SHARE_PATH}）...", "info")

        def worker():
            result = self._on_add_share()
            self.after(0, lambda: self._on_add_done(result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_add_done(self, result: ShareInstallResult) -> None:
        if result.ok:
            self._status.configure(text="✓ 已添加")
            self._btn.configure(state="disabled", text="已添加")
            self._on_log(f"✓ {result.message}", "success")
        else:
            self._status.configure(text="✗ 失败")
            self._btn.configure(state="normal", text="重试")
            self._on_log(f"✗ 扫描共享添加失败: {result.message}", "error")
