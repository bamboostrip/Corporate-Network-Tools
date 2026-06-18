"""Windows 网络信息查询：获取当前连接的 WiFi SSID。

用 netsh wlan show interfaces 解析输出。
注意 netsh 输出是 GBK 编码；中文系统 SSID 行仍是 "SSID" 关键字（非全角）。
"""
from __future__ import annotations

import re
import subprocess

from route_tool.platform.windows.subprocess_utils import no_window_kwargs

_ENCODING = "gbk"
_ERRORS = "replace"

# 匹配 "    SSID                   : Corp-WiFi"
# 大小写不敏感，兼容中英文系统（中文系统 SSID 行无 BSSID 前缀）
_SSID_PATTERN = re.compile(r"^\s*SSID\s*:\s*(.*?)\s*$", re.IGNORECASE | re.MULTILINE)

# 连接失败/无无线网卡时的展示文案
_NOT_CONNECTED = "未连接"


def parse_ssid(netsh_output: str) -> str:
    """从 netsh wlan show interfaces 输出中解析当前 SSID。

    返回 SSID 字符串；未连接/无 SSID 行时返回空字符串。
    注意：解析层返回空串，由调用层（get_wifi_ssid）转换为展示文案。
    """
    if not netsh_output:
        return ""
    match = _SSID_PATTERN.search(netsh_output)
    if not match:
        return ""
    return match.group(1).strip()


def get_wifi_ssid() -> str:
    """获取当前连接的 WiFi 名称。

    通过 netsh wlan show interfaces 解析。未连接/无无线网卡/命令失败时
    返回 '未连接'，绝不抛异常（UI 显示需要稳定）。
    """
    cmd = ["netsh", "wlan", "show", "interfaces"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding=_ENCODING,
            errors=_ERRORS,
            **no_window_kwargs(),
        )
    except OSError:
        return _NOT_CONNECTED

    ssid = parse_ssid(proc.stdout)
    return ssid if ssid else _NOT_CONNECTED
