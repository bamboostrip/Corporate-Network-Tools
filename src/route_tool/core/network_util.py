"""平台无关的网络工具。

这里只放与平台无关、纯逻辑的网络查询函数。
平台相关的（如 netsh、networksetup）放在各自 platform 子包里。
"""
from __future__ import annotations

import socket

from route_tool.core.config import GATEWAY


def get_local_ip() -> str:
    """获取本机出口 IP。

    原理：建一个 UDP socket "连接"到网关，OS 会据此选出出口接口并填上本机 IP。
    UDP connect 不真正发包，只是让内核选路由，安全且无副作用。

    失败（无网络/异常）时返回 '未知'，不抛异常。
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect((GATEWAY, 80))
        return sock.getsockname()[0]
    except OSError:
        return "未知"
    finally:
        if sock is not None:
            sock.close()
