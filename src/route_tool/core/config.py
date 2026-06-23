"""写死的网络配置常量。

如未来需要频繁变更，可改为从 config.toml 读取；当前按 YAGNI 保持写死。
"""
from route_tool.core.models import PrinterInfo, PrinterTarget, RouteInfo

# === 路由配置 ===
TARGET_NETWORK = "192.168.0.0"
SUBNET_MASK = "255.255.252.0"  # /22 的点分十进制（Windows route 命令不支持 CIDR）
TARGET_CIDR = "192.168.0.0/22"
GATEWAY = "192.168.5.22"
ROUTE_METRIC = 1
ROUTE_PERSISTENT = True

DEFAULT_ROUTE = RouteInfo(
    network=TARGET_NETWORK,
    mask=SUBNET_MASK,
    gateway=GATEWAY,
    metric=ROUTE_METRIC,
    persistent=ROUTE_PERSISTENT,
)

# === 连通性测试目标 ===
TEST_TARGETS: list[PrinterInfo] = [
    PrinterInfo(name="大打印机", ip="192.168.0.210", icon="🖨"),
    PrinterInfo(name="小打印机", ip="192.168.0.241", icon="🖨"),  # 修正：原 248 错误
    PrinterInfo(name="锐捷网关", ip="192.168.0.1", icon="🌐"),
]

# === ping 参数 ===
PING_COUNT = 2
PING_TIMEOUT_SECONDS = 10

# === 打印机定义（用于自动添加） ===
BIG_PRINTER = PrinterTarget(
    name="大打印机",
    description="SHARP MX-M905C 彩色复合机",
    ip="192.168.0.210",
    driver_label="big",
    port=9100,
)
SMALL_PRINTER = PrinterTarget(
    name="小打印机",
    description="SHARP MX-C6082D",
    ip="192.168.0.241",
    driver_label="small",
    port=9100,
)
PRINTER_DEFS: list[PrinterTarget] = [BIG_PRINTER, SMALL_PRINTER]

# === 扫描文件共享配置 ===
# 用户扫描文档统一存到这里，程序自动添加为网络位置（免每次输密码）。
SCAN_SHARE_PATH = r"\\192.168.0.210\shared\SMY"
SCAN_SHARE_USER = "admin"
SCAN_SHARE_PASSWORD = "admin"
