"""macOS 网络信息查询：获取当前连接的 WiFi SSID。

用 networksetup -getairportnetwork 解析输出。
输出形如 "Current Wi-Fi Network: <SSID>"（英文系统）或
"当前 Wi-Fi 网络: <SSID>"（中文系统）。
"""
from __future__ import annotations

import re
import subprocess

# 匹配 "Current Wi-Fi Network: <SSID>" 或 "当前 Wi-Fi 网络: <SSID>"
# 关键特征：以 "Network"/"网络" 结尾的冒号分隔行，冒号后是 SSID
_SSID_PATTERN = re.compile(r"Wi-?Fi\s+(?:Network|网络)\s*:\s*(.+?)\s*$", re.MULTILINE)

_NOT_CONNECTED = "未连接"


def parse_ssid(networksetup_output: str) -> str:
    """从 networksetup -getairportnetwork 输出解析 SSID。

    返回 SSID 字符串；未连接/无法识别时返回空字符串。
    """
    if not networksetup_output:
        return ""
    match = _SSID_PATTERN.search(networksetup_output)
    if not match:
        return ""
    return match.group(1).strip()


def get_wifi_ssid() -> str:
    """获取当前连接的 WiFi 名称。

    通过 networksetup -getairportnetwork 解析。未连接/命令失败时返回 '未连接'。
    """
    cmd = ["networksetup", "-getairportnetwork", "en0"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return _NOT_CONNECTED

    ssid = parse_ssid(proc.stdout)
    return ssid if ssid else _NOT_CONNECTED
