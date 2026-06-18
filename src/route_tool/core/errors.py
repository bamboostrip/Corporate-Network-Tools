"""工具自定义异常。"""


class RouteToolError(Exception):
    """所有工具异常的基类。"""


class UnsupportedOSError(RouteToolError):
    """当前操作系统不被支持。"""

    def __init__(self, system: str):
        self.system = system
        super().__init__(
            f"本工具暂不支持 {system} 系统，请联系 IT。"
        )
