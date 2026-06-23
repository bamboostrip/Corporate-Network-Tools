"""一键傻瓜部署编排器。

串行执行全部配置步骤，任一步失败就中断（用户选的"失败就停下"）。
步骤顺序：
  1. 网络环境检测（5.22 可达性，不可达直接中断）
  2. 路由配置（已存在则跳过）
  3. 添加大打印机
  4. 添加小打印机
  5. 添加 SMY 扫描共享

编排逻辑与 UI 解耦：通过 on_progress/on_log 回调通知进度，
UI 只负责显示，便于单元测试（mock backend）。
"""
from __future__ import annotations

from typing import Callable

from route_tool.core.config import DEFAULT_ROUTE, PRINTER_DEFS
from route_tool.core.contracts import PlatformBackend
from route_tool.core.models import DeployResult

TOTAL_STEPS = 5


class DeployOrchestrator:
    """一键部署编排器。后台线程执行，通过回调通知 UI。"""

    def __init__(
        self,
        backend: PlatformBackend,
        on_progress: Callable[[int, int, str], None],
        on_log: Callable[[str, str], None],
    ):
        self._backend = backend
        self._on_progress = on_progress
        self._on_log = on_log

    def run_full_deploy(self) -> DeployResult:
        """执行全部部署步骤。任一关键步骤失败则中断。"""
        completed = 0

        # === 步骤 1：网络环境检测 ===
        self._on_progress(1, TOTAL_STEPS, "检测网络环境")
        self._on_log("开始检测网络环境...", "info")
        info = self._backend.get_network_info()
        if not info.gateway522_reachable:
            self._on_log(
                f"✗ 网关 192.168.5.22 不可达（{info.gateway522_message}），"
                f"请确认已连接公司内网",
                "error",
            )
            return DeployResult(
                total_steps=TOTAL_STEPS, completed_steps=0, ok=False,
                message=f"网关不可达（{info.gateway522_message}），请检查网络连接",
                failed_step="网络环境检测",
            )
        self._on_log(
            f"✓ 网络环境: WiFi={info.wifi_name}, IP={info.local_ip}, 网关可达",
            "success",
        )
        completed = 1

        # === 步骤 2：路由配置 ===
        self._on_progress(2, TOTAL_STEPS, "配置路由")
        if self._backend.route_exists(DEFAULT_ROUTE):
            self._on_log("✓ 路由已配置，跳过", "info")
        else:
            self._on_log("开始配置路由...", "info")
            route_result = self._backend.add_route(DEFAULT_ROUTE)
            if not route_result.ok:
                self._on_log(f"✗ 路由配置失败: {route_result.message}", "error")
                return DeployResult(
                    total_steps=TOTAL_STEPS, completed_steps=completed, ok=False,
                    message=f"路由配置失败: {route_result.message}",
                    failed_step="配置路由",
                )
            self._on_log(f"✓ {route_result.message}", "success")
        completed = 2

        # === 步骤 3 & 4：添加两台打印机 ===
        for idx, target in enumerate(PRINTER_DEFS, start=1):
            step = 2 + idx  # 3 或 4
            self._on_progress(step, TOTAL_STEPS, f"添加{target.name}")
            already = self._backend.printer_exists(target)
            if already:
                self._on_log(f"✓ {target.name} 已添加，跳过", "info")
            else:
                self._on_log(f"开始添加 {target.name}（{target.description}）...", "info")
                printer_result = self._backend.add_printer(target)
                if not printer_result.ok:
                    self._on_log(
                        f"✗ {target.name} 添加失败: {printer_result.message}", "error"
                    )
                    return DeployResult(
                        total_steps=TOTAL_STEPS, completed_steps=completed, ok=False,
                        message=f"{target.name}添加失败: {printer_result.message}",
                        failed_step=f"添加{target.name}",
                    )
                self._on_log(f"✓ {printer_result.message}", "success")
            completed = step

        # === 步骤 5：添加扫描共享 ===
        self._on_progress(5, TOTAL_STEPS, "添加扫描共享")
        self._on_log("开始添加 SMY 扫描共享...", "info")
        share_result = self._backend.add_scan_share()
        if not share_result.ok:
            self._on_log(f"✗ 扫描共享添加失败: {share_result.message}", "error")
            return DeployResult(
                total_steps=TOTAL_STEPS, completed_steps=completed, ok=False,
                message=f"扫描共享添加失败: {share_result.message}",
                failed_step="添加扫描共享",
            )
        self._on_log(f"✓ {share_result.message}", "success")
        completed = 5

        # === 全部完成 ===
        self._on_log("一键部署全部完成！", "success")
        return DeployResult(
            total_steps=TOTAL_STEPS, completed_steps=completed, ok=True,
            message="一键部署完成，全部配置已就绪",
        )
