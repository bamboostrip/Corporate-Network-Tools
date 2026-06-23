"""平台无关的数据模型。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResultLevel(Enum):
    """命令执行结果级别。"""
    SUCCESS = "success"
    FAILURE = "failure"
    UNSUPPORTED = "unsupported"


@dataclass
class Result:
    """所有系统命令调用的统一返回类型。

    level/message 给用户看，raw_output 给 IT 诊断看。
    """
    level: ResultLevel
    message: str
    raw_output: str = ""
    error_code: int = 0

    @property
    def ok(self) -> bool:
        return self.level == ResultLevel.SUCCESS


@dataclass
class RouteInfo:
    """一条持久路由的描述。"""
    network: str
    mask: str
    gateway: str
    metric: int = 1
    persistent: bool = True


@dataclass
class PingResult:
    """ping 测试结果。"""
    host: str
    ok: bool
    message: str
    raw_output: str = ""
    latency_ms: float | None = None


@dataclass
class PrinterInfo:
    """待测试的设备信息。"""
    name: str
    ip: str
    icon: str = "🖨"


@dataclass
class NetworkInfo:
    """当前网络环境信息。

    给 UI 显示用：用户能看到自己连的 WiFi、本机 IP，
    以及网关 192.168.5.22 是否可达（可达才允许配置路由）。
    """
    wifi_name: str            # SSID，未连接/无无线网卡时为 "未连接"
    local_ip: str             # 本机出口 IP，获取失败时为 "未知"
    gateway522_reachable: bool  # 192.168.5.22 是否可 ping 通
    gateway522_message: str   # 给用户看的可达性提示，如 "✓ 可达" / "✗ 超时"


@dataclass
class PrinterTarget:
    """待添加的打印机定义（公司固定，非用户输入）。"""
    name: str            # 系统打印机队列显示名："大打印机"
    description: str     # 备注："SHARP MX-M905C 彩色复合机"
    ip: str              # "192.168.0.210"
    driver_label: str    # 驱动资源定位键："big"/"small"
    port: int = 9100     # Windows 用 9100(Raw)，macOS 忽略(用 631)


@dataclass
class PrinterInstallResult:
    """添加打印机的结果。"""
    printer_name: str
    ok: bool
    already_exists: bool = False
    message: str = ""
    raw_output: str = ""
    error_code: int = 0


@dataclass
class ShareInstallResult:
    """添加扫描共享网络位置的结果。"""
    share_name: str
    ok: bool
    message: str = ""
    raw_output: str = ""
    error_code: int = 0


@dataclass
class DeployResult:
    """一键快捷部署的整体结果。"""
    total_steps: int          # 总步骤数
    completed_steps: int      # 已成功完成的步骤数
    ok: bool                  # 是否全部成功
    message: str              # 给用户看的总结消息
    failed_step: str = ""     # 失败的步骤名（全部成功时为空）
