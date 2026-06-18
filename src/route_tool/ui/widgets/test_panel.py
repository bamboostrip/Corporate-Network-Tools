"""连通性测试面板。

显示打印机/网关列表，每个设备一行，带独立测试按钮和状态图标。
支持"全部测试"批量执行。
所有 backend.ping 调用在后台线程执行，结果通过 after() 回主线程更新 UI。
"""
from __future__ import annotations

import threading
from typing import Callable

import customtkinter as ctk

from route_tool.core.config import TEST_TARGETS, PING_COUNT
from route_tool.core.models import PingResult, PrinterInfo


class _DeviceRow(ctk.CTkFrame):
    """单个设备的一行：图标+名称+IP+状态+测试按钮。"""

    def __init__(
        self,
        master,
        device: PrinterInfo,
        on_test: Callable[[], None],
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._device = device

        self.grid_columnconfigure(2, weight=1)  # 状态列拉伸

        self._icon = ctk.CTkLabel(self, text=f"{device.icon} {device.name}", width=120, anchor="w")
        self._icon.grid(row=0, column=0, padx=(0, 10), pady=2, sticky="w")

        self._ip_label = ctk.CTkLabel(self, text=device.ip, width=120, anchor="w",
                                       font=ctk.CTkFont(family="Consolas", size=12))
        self._ip_label.grid(row=0, column=1, padx=(0, 10), pady=2, sticky="w")

        self._status = ctk.CTkLabel(self, text="未测试", anchor="w")
        self._status.grid(row=0, column=2, padx=(0, 10), pady=2, sticky="ew")

        self._btn = ctk.CTkButton(self, text="测试", width=60, height=24, command=on_test)
        self._btn.grid(row=0, column=3, padx=0, pady=2)

    def set_testing(self) -> None:
        self._status.configure(text="🔄 测试中...")

    def set_result(self, ok: bool, message: str) -> None:
        if ok:
            self._status.configure(text=f"✓ {message}")
        else:
            self._status.configure(text=f"✗ {message}")


class TestPanel(ctk.CTkFrame):
    """连通性测试区域。"""

    # 告诉 pytest：这是 UI 类不是测试类（类名以 Test 开头会被误判）
    __test__ = False

    def __init__(
        self,
        master,
        on_ping: Callable[[str, int], PingResult],
        on_log: Callable[[str, str], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._on_ping = on_ping
        self._on_log = on_log
        self._rows: dict[str, _DeviceRow] = {}

        self._title = ctk.CTkLabel(self, text="🔍 连通性测试", font=ctk.CTkFont(size=16, weight="bold"))
        self._title.pack(anchor="w", padx=15, pady=(10, 4))

        rows_frame = ctk.CTkFrame(self, fg_color="transparent")
        rows_frame.pack(fill="x", padx=15, pady=(0, 2))

        for device in TEST_TARGETS:
            row = _DeviceRow(
                rows_frame,
                device=device,
                on_test=lambda ip=device.ip: self._test_single(ip),
            )
            row.pack(fill="x", pady=1)
            self._rows[device.ip] = row

        # 批量测试按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(4, 10))

        self._test_all_btn = ctk.CTkButton(
            btn_frame, text="全部测试", command=self._test_all, height=28
        )
        self._test_all_btn.pack(side="left", padx=(0, 10))

    def _test_single(self, ip: str) -> None:
        """测试单个设备（异步）。"""
        row = self._rows.get(ip)
        if row is None:
            return
        row.set_testing()
        self._on_log(f"开始测试 {ip}...", "info")

        def worker():
            result = self._on_ping(ip, PING_COUNT)
            self.after(0, lambda: self._on_ping_done(ip, result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ping_done(self, ip: str, result: PingResult) -> None:
        row = self._rows.get(ip)
        if row:
            row.set_result(result.ok, result.message)
        if result.ok:
            latency = f" ({result.latency_ms:.0f}ms)" if result.latency_ms else ""
            self._on_log(f"✓ {ip} 可达{latency}", "success")
        else:
            self._on_log(f"✗ {ip} 不可达: {result.message}", "error")
            if result.raw_output:
                self._on_log(f"  诊断: {result.raw_output}", "debug")

    def _test_all(self) -> None:
        """批量测试所有设备。"""
        self._test_all_btn.configure(state="disabled", text="测试中...")
        self._on_log("开始批量测试所有设备...", "info")
        for ip in self._rows:
            self._test_single(ip)
        # 简单恢复：2 秒后重新启用（最慢的 ping 也就几秒）
        self.after(2000, lambda: self._test_all_btn.configure(state="normal", text="全部测试"))
