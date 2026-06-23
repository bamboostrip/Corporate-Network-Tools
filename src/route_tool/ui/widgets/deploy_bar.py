"""一键部署按钮栏。

界面最顶部最醒目的一个大按钮，点击后后台串行执行全部部署步骤。
部署中按钮禁用（避免重复触发），文字显示进度。
结果通过回调通知主窗口（用于同步更新各分模块面板状态）。
"""
from __future__ import annotations

import threading
from typing import Callable

import customtkinter as ctk

from route_tool.core.models import DeployResult


class DeployBar(ctk.CTkFrame):
    """一键部署栏。"""

    __test__ = False

    # 按钮状态常量
    STATE_IDLE = "idle"           # 待机：可点击
    STATE_DEPLOYING = "deploying"  # 部署中：禁用
    STATE_DONE = "done"           # 完成：禁用（用户可重新点"重新部署"）

    def __init__(
        self,
        master,
        on_deploy: Callable[[], DeployResult],  # 后台执行编排，返回 DeployResult
        on_log: Callable[[str, str], None],
        on_progress: Callable[[int, int, str], None],  # (step, total, desc)
        on_done: Callable[[DeployResult], None] | None = None,  # 完成后通知主窗口
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._on_deploy = on_deploy
        self._on_log = on_log
        self._on_progress = on_progress
        self._on_done = on_done

        self.grid_columnconfigure(0, weight=1)

        # 大按钮（最显眼）
        self._btn = ctk.CTkButton(
            self,
            text="🚀 一键快捷部署\n(自动配置路由/打印机/扫描共享)",
            command=self.deploy_async,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=56,
        )
        self._btn.grid(row=0, column=0, padx=15, pady=(12, 4), sticky="ew")

        # 进度/状态文字
        self._status = ctk.CTkLabel(
            self, text="点击上方按钮，自动完成全部配置", anchor="center",
            font=ctk.CTkFont(size=12),
        )
        self._status.grid(row=1, column=0, padx=15, pady=(0, 8), sticky="ew")

    def deploy_async(self) -> None:
        """后台执行一键部署。"""
        if self._btn.cget("state") == "disabled":
            return  # 部署中，忽略重复点击

        self._btn.configure(state="disabled")
        self._status.configure(text="部署中... 请稍候")
        self._on_log("=== 开始一键快捷部署 ===", "info")

        def worker():
            result = self._on_deploy()
            self.after(0, lambda: self._on_deploy_done(result))

        threading.Thread(target=worker, daemon=True).start()

    def update_progress(self, step: int, total: int, desc: str) -> None:
        """主线程调用：更新进度文字（由 on_progress 回调转发）。"""
        self._status.configure(text=f"部署中 [{step}/{total}] {desc}...")
        self._btn.configure(text=f"🚀 部署中 [{step}/{total}] {desc}...")

    def _on_deploy_done(self, result: DeployResult) -> None:
        """部署完成（主线程）。更新按钮和状态。"""
        if result.ok:
            self._btn.configure(
                text="✓ 一键部署完成\n(如需重新配置可再次点击)",
                state="normal",
            )
            self._status.configure(text=result.message)
        else:
            # 中断：显示完成步数，允许重试
            self._btn.configure(
                text=f"⚠ 部署中断（{result.completed_steps}/{result.total_steps} 完成）\n点击重新部署",
                state="normal",
            )
            self._status.configure(text=result.message)

        # 通知主窗口（用于刷新各分模块面板状态）
        if self._on_done:
            self._on_done(result)
