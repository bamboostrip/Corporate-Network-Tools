"""打印机管理面板。

显示两台打印机，每台一行（图标+名称+备注+IP+状态+添加按钮）。
5.22 不可达时所有添加按钮禁用（跨网段路由未配，9100 不通）。
添加操作在后台线程跑（驱动安装耗时长），结果用 after() 回主线程。
"""
from __future__ import annotations

import threading
from typing import Callable

import customtkinter as ctk

from route_tool.core.config import PRINTER_DEFS
from route_tool.core.models import PrinterInstallResult, PrinterTarget


class _PrinterRow(ctk.CTkFrame):
    """单台打印机的一行。"""

    def __init__(self, master, target: PrinterTarget, on_add: Callable[[], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._target = target
        self.grid_columnconfigure(2, weight=1)

        self._name = ctk.CTkLabel(self, text=f"🖨 {target.name}", width=80, anchor="w")
        self._name.grid(row=0, column=0, padx=(0, 8), pady=2, sticky="w")

        self._desc = ctk.CTkLabel(self, text=target.description, width=200, anchor="w")
        self._desc.grid(row=0, column=1, padx=(0, 8), pady=2, sticky="w")

        self._ip = ctk.CTkLabel(
            self, text=target.ip, width=110, anchor="w",
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self._ip.grid(row=0, column=2, padx=(0, 8), pady=2, sticky="w")

        self._status = ctk.CTkLabel(self, text="未添加", width=90, anchor="w")
        self._status.grid(row=0, column=3, padx=(0, 8), pady=2, sticky="w")

        self._btn = ctk.CTkButton(self, text="添加", width=60, height=24, command=on_add)
        self._btn.grid(row=0, column=4, padx=0, pady=2)

    def set_adding(self) -> None:
        self._status.configure(text="添加中...")
        self._btn.configure(state="disabled")

    def set_result(self, result: PrinterInstallResult) -> None:
        if result.ok:
            mark = "✓ 已添加" if not result.already_exists else "✓ 已存在"
            self._status.configure(text=mark)
            self._btn.configure(state="disabled", text="已添加")
        else:
            self._status.configure(text="✗ 失败")
            self._btn.configure(state="normal", text="重试")

    def enable_add(self, enabled: bool) -> None:
        """根据网络可达性启用/禁用添加按钮（已添加的保持禁用）。"""
        if self._btn.cget("text") == "已添加":
            return
        self._btn.configure(state="normal" if enabled else "disabled")


class PrinterPanel(ctk.CTkFrame):
    """打印机管理区域。"""

    __test__ = False  # pytest 不要误判为测试类

    def __init__(
        self,
        master,
        on_add_printer: Callable[[PrinterTarget], PrinterInstallResult],
        on_check_printer: Callable[[PrinterTarget], bool],
        on_log: Callable[[str, str], None],
        gateway_reachable: bool = False,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._on_add_printer = on_add_printer
        self._on_check_printer = on_check_printer
        self._on_log = on_log
        self._gateway_reachable = gateway_reachable
        self._rows: dict[str, _PrinterRow] = {}

        self._title = ctk.CTkLabel(
            self, text="🖨 打印机管理", font=ctk.CTkFont(size=16, weight="bold")
        )
        self._title.pack(anchor="w", padx=15, pady=(10, 4))

        rows_frame = ctk.CTkFrame(self, fg_color="transparent")
        rows_frame.pack(fill="x", padx=15, pady=(0, 10))

        for target in PRINTER_DEFS:
            row = _PrinterRow(
                rows_frame, target=target,
                on_add=lambda t=target: self.add_printer_async(t),
            )
            row.pack(fill="x", pady=1)
            row.enable_add(gateway_reachable)
            self._rows[target.name] = row

    @staticmethod
    def can_add_printer(gateway_reachable: bool) -> bool:
        """是否允许添加：5.22 可达才允许（跨网段路由前提）。"""
        return gateway_reachable

    def update_gateway_state(self, reachable: bool) -> None:
        """路由面板检测完后调用，更新所有按钮启用状态。"""
        self._gateway_reachable = reachable
        for row in self._rows.values():
            row.enable_add(reachable)

    def add_printer_async(self, target: PrinterTarget) -> None:
        """后台添加打印机（驱动安装耗时，不阻塞 UI）。"""
        if not self.can_add_printer(self._gateway_reachable):
            self._on_log(f"⚠ 网关不可达，无法添加 {target.name}，请先配置路由", "warning")
            return

        row = self._rows.get(target.name)
        if row is None:
            return
        row.set_adding()
        self._on_log(f"开始添加 {target.name}（{target.description}）...", "info")

        def worker():
            result = self._on_add_printer(target)
            self.after(0, lambda: self._on_add_done(target, result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_add_done(self, target: PrinterTarget, result: PrinterInstallResult) -> None:
        row = self._rows.get(target.name)
        if row:
            row.set_result(result)
        if result.ok:
            level = "info" if result.already_exists else "success"
            self._on_log(f"✓ {result.message}", level)
        else:
            self._on_log(f"✗ {target.name} 添加失败: {result.message}", "error")
            if result.raw_output:
                self._on_log(f"  诊断: {result.raw_output}", "debug")
