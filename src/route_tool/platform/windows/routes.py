"""Windows route 命令封装。

重要约定：
- 不用 shell=True（安全隐患）
- route print 输出是 GBK 编码，必须显式 encoding='gbk', errors='replace'
- route_exists 必须同时匹配 network + mask + gateway，不能只看 network（会误匹配注释）
"""
from __future__ import annotations

import re
import subprocess

from route_tool.core.models import Result, ResultLevel, RouteInfo
from route_tool.platform.windows.subprocess_utils import no_window_kwargs

# Windows route 命令默认输出 GBK 编码
_ENCODING = "gbk"
_ERRORS = "replace"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """统一的 subprocess 调用，强制 GBK 解码、无 shell、隐藏控制台窗口。"""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding=_ENCODING,
        errors=_ERRORS,
        shell=False,
        **no_window_kwargs(),
    )


def parse_route_exists(route_print_output: str, route: RouteInfo) -> bool:
    """解析 route print 输出，判断指定路由是否已存在。

    必须同时匹配 network + mask + gateway 三个要素，
    否则会把 192.168.0.0 出现在注释/接口行里的情况误判为已存在。
    """
    if not route_print_output:
        return False

    # 用正则匹配三列：network mask gateway（中间是任意空白/对齐空格）
    # 匹配形如 "192.168.0.0    255.255.252.0     192.168.5.22"
    pattern = re.compile(
        rf"\b{re.escape(route.network)}\s+"
        rf"{re.escape(route.mask)}\s+"
        rf"{re.escape(route.gateway)}\b"
    )
    return pattern.search(route_print_output) is not None


def route_exists(route: RouteInfo) -> bool:
    """检查 Windows 上指定路由是否已配置。"""
    try:
        result = _run(["route", "print", route.network])
        return parse_route_exists(result.stdout, route)
    except (subprocess.SubprocessError, OSError):
        return False


def add_route(route: RouteInfo) -> Result:
    """添加持久路由。

    等价命令: route -p add <network> mask <mask> <gateway> metric <metric>
    """
    cmd = [
        "route",
        "-p" if route.persistent else "",
        "add",
        route.network,
        "mask",
        route.mask,
        route.gateway,
        "metric",
        str(route.metric),
    ]
    # 过滤掉空字符串（-p 为空时）
    cmd = [c for c in cmd if c]

    try:
        proc = _run(cmd)
    except (subprocess.SubprocessError, OSError) as e:
        return Result(
            level=ResultLevel.FAILURE,
            message=f"执行 route 命令失败: {e}",
            error_code=-1,
        )

    if proc.returncode == 0:
        return Result(
            level=ResultLevel.SUCCESS,
            message="路由添加成功",
            raw_output=proc.stdout,
        )
    return Result(
        level=ResultLevel.FAILURE,
        message="路由添加失败，请查看诊断信息",
        raw_output=proc.stderr or proc.stdout,
        error_code=proc.returncode,
    )


def remove_route(route: RouteInfo) -> Result:
    """删除路由。等价: route delete <network>"""
    cmd = ["route", "delete", route.network]
    try:
        proc = _run(cmd)
    except (subprocess.SubprocessError, OSError) as e:
        return Result(
            level=ResultLevel.FAILURE,
            message=f"执行 route 命令失败: {e}",
            error_code=-1,
        )

    if proc.returncode == 0:
        return Result(
            level=ResultLevel.SUCCESS,
            message="路由删除成功",
            raw_output=proc.stdout,
        )
    return Result(
        level=ResultLevel.FAILURE,
        message="路由删除失败",
        raw_output=proc.stderr or proc.stdout,
        error_code=proc.returncode,
    )
