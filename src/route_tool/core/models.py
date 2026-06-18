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
