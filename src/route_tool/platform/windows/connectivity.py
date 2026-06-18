"""Windows ping 连通性测试。

重要：
- Windows ping 用 -n 指定次数（不是 Linux 的 -c）
- 输出是 GBK 编码
- 超时用 subprocess 的 timeout 参数控制
"""
from __future__ import annotations

import re
import subprocess

from route_tool.core.config import PING_TIMEOUT_SECONDS
from route_tool.core.models import PingResult
from route_tool.platform.windows.subprocess_utils import no_window_kwargs


def parse_ping_result(host: str, output: str) -> PingResult:
    """解析 Windows ping 输出，构造 PingResult。"""
    if not output:
        return PingResult(host=host, ok=False, message="无输出")

    # 判断成功：找 "已接收 = N" 且 N > 0，或者 "时间=Xms"
    received_match = re.search(r"已接收\s*=\s*(\d+)", output)
    has_reply = "时间=" in output or "time=" in output.lower()

    if received_match:
        received = int(received_match.group(1))
        ok = received > 0
    else:
        # 没有统计行时，看是否有回复
        ok = has_reply

    if not ok:
        return PingResult(host=host, ok=False, message=f"{host} 不可达", raw_output=output)

    # 提取平均延迟
    latency = None
    avg_match = re.search(r"平均\s*=\s*(\d+)\s*ms", output)
    if avg_match:
        latency = float(avg_match.group(1))
    else:
        # 没有平均行时，取单次时间
        times = re.findall(r"时间=(\d+)\s*ms", output)
        if times:
            latency = sum(int(t) for t in times) / len(times)

    # 提取收包数
    sent_match = re.search(r"已发送\s*=\s*(\d+)", output)
    received_count = received_match.group(1) if received_match else "?"
    sent_count = sent_match.group(1) if sent_match else "?"

    return PingResult(
        host=host,
        ok=True,
        message=f"{host} 可达 ({received_count}/{sent_count} 包)",
        raw_output=output,
        latency_ms=latency,
    )


def ping(host: str, count: int = 2) -> PingResult:
    """执行 Windows ping 命令。"""
    cmd = ["ping", host, "-n", str(count)]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="replace",
            timeout=PING_TIMEOUT_SECONDS,
            **no_window_kwargs(),
        )
        return parse_ping_result(host, proc.stdout)
    except subprocess.TimeoutExpired:
        return PingResult(host=host, ok=False, message=f"{host} ping 超时")
    except (subprocess.SubprocessError, OSError) as e:
        return PingResult(host=host, ok=False, message=f"ping 执行失败: {e}")
