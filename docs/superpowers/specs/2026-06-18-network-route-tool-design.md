# 公司网络路由配置工具 设计文档

- **日期**: 2026-06-18
- **状态**: 待批准
- **作者**: brainstorming 阶段产出

---

## 1. 背景与目标

### 1.1 网络现状

公司使用电信企业带宽，接入电信提供的华为路由器（不能改桥接），华为路由器下挂锐捷网关。两个网络通过有线连接，但需要手动配置路由表才能互通：

```
电信光猫 / 华为路由器 (192.168.5.1, DHCP 给 5.x 网段)
        │
        ├── WiFi 设备 (192.168.5.x)          ← 这些设备需要配置
        │
        └── 有线 ──── 锐捷网关 WAN/LAN 接口 = 192.168.5.22 (固定 IP)
                          │
                          └── 锐捷内部网络 (192.168.0.0/22, 网关 192.168.0.1)
                                ├── 大打印机 192.168.0.210
                                └── 小打印机 192.168.0.248
```

- 华为侧路由转发因电信设备限制无法配置成功
- 锐捷侧已配置路由转发（锐捷 → 华为方向通）
- **缺失方向**: 华为 WiFi 下的设备 → 锐捷网络下的设备，需要在华为侧每台终端手动添加持久路由

### 1.2 当前痛点

目前通过 bat 脚本下发，但：
1. 同事对命令行有心理负担，使用率低
2. bat 出错看不到信息，远程排查困难
3. 没有 GUI，同事不知道点哪里

### 1.3 目标

开发一个**双击即用的 GUI 工具**，让华为 WiFi 下的同事能：
- 一键配置访问锐捷网络所需的持久路由
- 一眼看到配置状态和连通性测试结果
- 出错时能看到清晰的日志，方便远程排查

### 1.4 非目标（首版明确不做）

- ❌ 一键添加打印机功能（后期再考虑）
- ❌ CLI 版本（后期再考虑，远程协助可直接用命令行）
- ❌ Linux 平台支持（用户无此需求）
- ❌ Mac 版添加打印机功能（首版 Mac 只做路由 + ping）
- ❌ 自动更新机制（内部分发，新版本重新下发即可）

---

## 2. 技术选型

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 语言 | **Python 3.10+** | 调系统命令最直接；项目已用 uv |
| GUI 框架 | **CustomTkinter** | 现代 UI、API 与 tkinter 一致、打包友好、无商用授权坑 |
| 环境管理 | **uv** | 已在用，秒级创建隔离环境 |
| 打包 | **PyInstaller --onefile** | 最成熟，单文件分发 |
| 跨平台范围 | **Windows 全功能 + Mac 路由/ping** | 实际用户分布决定，避免过度工程 |

**否决项：**
- ❌ Rust + Tauri：Rust 安全优势在"调系统命令"场景用不上；Tauri 的 UAC 提权要绕 helper exe，反而更复杂
- ❌ 原生 tkinter：UI 质感过旧，同事会质疑可靠性
- ❌ PyQt：打包体积 50MB+，商用授权有坑
- ❌ Nuitka：编译慢、偶发坑，对这个场景过度

---

## 3. 系统架构

### 3.1 分层架构

```
┌─────────────────────────────────────────┐
│  UI 层 (ui/gui.py)                       │  CustomTkinter 界面
│  只依赖 contracts.Protocol，不碰系统命令  │
├─────────────────────────────────────────┤
│  平台抽象层 (platform/)                  │  Protocol 接口
│  ├── Windows 后端（全功能）              │
│  └── macOS 后端（路由 + ping）           │
├─────────────────────────────────────────┤
│  核心层 (core/)                          │  数据类、配置常量
│  models.py / config.py                   │
└─────────────────────────────────────────┘
```

**核心原则：UI 层永远只依赖 `contracts.PlatformBackend` Protocol，从不直接 import 平台实现。** 这样增加 Mac 实现或后期改 Tauri 都不影响 UI 逻辑。

### 3.2 目录结构

```
公司网络拓扑/
├── pyproject.toml              # uv 项目配置
├── uv.lock
├── README.md                   # 维护者说明
├── 分发说明.md                  # 给同事看的极简使用说明
├── docs/
│   └── superpowers/specs/
│       └── 2026-06-18-network-route-tool-design.md
├── scripts/
│   └── build.py                # 一键打包脚本
└── src/
    └── route_tool/
        ├── __init__.py
        ├── __main__.py         # python -m route_tool 入口
        ├── core/
        │   ├── __init__.py
        │   ├── config.py       # 写死的网络常量
        │   ├── models.py       # RouteInfo / PingResult / Result / PrinterInfo
        │   └── contracts.py    # PlatformBackend Protocol
        ├── platform/
        │   ├── __init__.py     # get_backend() 工厂
        │   ├── windows/
        │   │   ├── __init__.py
        │   │   ├── backend.py  # WindowsBackend 实现
        │   │   ├── routes.py   # route -p add/print/delete
        │   │   ├── connectivity.py  # ping / Test-NetConnection
        │   │   └── admin.py    # is_admin() 检测（重启逻辑由 manifest 接管，本模块仅检测）
        │   └── macos/
        │       ├── __init__.py
        │       └── backend.py  # MacBackend 实现（route + ping）
        └── ui/
            ├── __init__.py
            ├── gui.py          # 主窗口
            └── widgets/
                ├── __init__.py
                ├── route_panel.py     # 路由配置区
                ├── test_panel.py      # 连通性测试区
                └── log_panel.py       # 操作日志区
```

---

## 4. 核心数据模型

### 4.1 `core/config.py`（写死的网络配置）

```python
# 路由配置
TARGET_NETWORK = "192.168.0.0"
SUBNET_MASK = "255.255.252.0"    # /22 的点分十进制（Windows route 命令不支持 CIDR，必须点分十进制）
GATEWAY = "192.168.5.22"
ROUTE_METRIC = 1                 # 默认 metric
ROUTE_PERSISTENT = True          # -p 持久路由

# 连通性测试目标
TEST_TARGETS = [
    PrinterInfo(name="大打印机", ip="192.168.0.210", icon="🖨"),
    PrinterInfo(name="小打印机", ip="192.168.0.248", icon="🖨"),
    PrinterInfo(name="锐捷网关", ip="192.168.0.1",   icon="🌐"),
]

# 连通性测试参数
PING_COUNT = 2
PING_TIMEOUT_SECONDS = 10
```

### 4.2 `core/models.py`

```python
from dataclasses import dataclass, field
from enum import Enum

class ResultLevel(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    UNSUPPORTED = "unsupported"

@dataclass
class RouteInfo:
    network: str        # "192.168.0.0"
    mask: str           # "255.255.252.0"
    gateway: str        # "192.168.5.22"
    metric: int = 1
    persistent: bool = True

@dataclass
class PingResult:
    host: str
    ok: bool
    message: str              # 给同事看："大打印机 可达 (2/2 包)"
    raw_output: str = ""      # 给诊断看的原始 ping 输出
    latency_ms: float | None = None

@dataclass
class PrinterInfo:
    name: str
    ip: str
    icon: str = "🖨"

@dataclass
class Result:
    """所有系统命令调用的统一返回类型"""
    level: ResultLevel
    message: str              # 给同事看的人话
    raw_output: str = ""      # 给诊断看的原始输出
    error_code: int = 0
```

### 4.3 `core/contracts.py`

```python
from typing import Protocol

class PlatformBackend(Protocol):
    """平台后端契约。所有平台实现必须满足此接口。"""
    
    def is_admin(self) -> bool:
        """当前进程是否有管理员/root 权限"""
        ...
    
    def route_exists(self, route: RouteInfo) -> bool:
        """检查路由是否已配置"""
        ...
    
    def add_route(self, route: RouteInfo) -> Result:
        """添加路由（持久化）"""
        ...
    
    def remove_route(self, route: RouteInfo) -> Result:
        """删除路由"""
        ...
    
    def ping(self, host: str, count: int = 2) -> PingResult:
        """测试主机连通性"""
        ...
```

**注意**：首版 Protocol 不包含 `add_printer`，因为该功能暂不实现。后期加打印机时再扩展 Protocol，避免 YAGNI。

---

## 5. 平台实现细节

### 5.1 Windows 后端

**路由命令（关键，易错点）：**
```python
# 添加持久路由
route -p add 192.168.0.0 mask 255.255.252.0 192.168.5.22 metric 1

# 检查路由是否存在
route print 192.168.0.0
# 然后解析输出，同时匹配 network + mask + gateway 三要素

# 删除路由
route delete 192.168.0.0
```

**命令调用规范（重要）：**
- ❌ 不用 `shell=True`（安全隐患 + 多此一举）
- ✅ 直接传 list：`subprocess.run(['route', '-p', 'add', ...], capture_output=True)`
- ✅ Windows 上 `route print` 输出是 **GBK 编码**，必须 `encoding='gbk', errors='replace'`，否则中文环境乱码崩溃

**route_exists 的健壮性：**
不能简单 `return target_network in output`（会误匹配 `192.168.0.0` 出现在注释里）。必须解析 `route print` 的表格，**同时匹配 network + mask + gateway**。

**is_admin 检测：**
```python
import ctypes
def is_admin(self) -> bool:
    return ctypes.windll.shell32.IsUserAnAdmin() != 0
```
因为 exe 内嵌管理员 manifest，理论上启动即管理员，但这个检测保留作兜底（防 manifest 配置失败）。

### 5.2 macOS 后端

**路由命令：**
```python
# 添加持久路由（macOS 持久化方式不同，通过 launchd 或 networksetup）
# 临时路由：
sudo route -n add -net 192.168.0.0/22 192.168.5.22

# 检查：
netstat -rn | grep 192.168.0.0

# ping：
ping -c 2 192.168.0.210
```

**macOS 持久路由的复杂性：** macOS 没有像 Windows `-p` 那样的简单持久化开关，需要额外配置 launchd plist。**首版 Mac 实现只做临时路由 + ping，持久化作为已知限制在 UI 上明确告知用户**（"macOS 暂只支持本次会话生效，重启需重新配置"）。

**权限：** macOS 上 `route add` 需要 sudo。由于本工具用 PyInstaller 打包，无法像 Windows 那样内嵌提权。Mac 用户需用 `sudo` 运行，UI 启动时检测 `os.geteuid()`，非 root 时明确提示退出方式。

### 5.3 平台工厂

```python
# platform/__init__.py
import platform as _platform

def get_backend() -> PlatformBackend:
    system = _platform.system()
    if system == "Windows":
        from .windows.backend import WindowsBackend
        return WindowsBackend()
    if system == "Darwin":
        from .macos.backend import MacBackend
        return MacBackend()
    raise UnsupportedOSError(
        f"本工具暂不支持 {system} 系统，请联系 IT。"
    )
```

---

## 6. GUI 设计

### 6.1 窗口布局

```
┌─────────────────────────────────────────────────┐
│  🏢 公司网络配置工具              [☀/🌙 主题]    │  标题栏 + 主题切换
├─────────────────────────────────────────────────┤
│                                                 │
│  📡 网络路由配置                                 │  RoutePanel
│  ┌───────────────────────────────────────────┐  │
│  │ 目标网段:  192.168.0.0/22                  │  │
│  │ 网关:      192.168.5.22                    │  │
│  │ 状态:      ✓ 已配置 / ⚠ 未配置 / 🔄 检测中 │  │
│  │                                           │  │
│  │           [一键配置路由]（已配置时禁用）   │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  🔍 连通性测试                                  │  TestPanel
│  ┌───────────────────────────────────────────┐  │
│  │ 🖨 大打印机 192.168.0.210  ✓ 通    [测试] │  │
│  │ 🖨 小打印机 192.168.0.248  ✗ 不通  [测试] │  │
│  │ 🌐 锐捷网关 192.168.0.1    🔄测试中 [测试]│  │
│  │                                           │  │
│  │           [全部测试]   [自定义IP测试]      │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  📋 操作日志                                    │  LogPanel
│  ┌───────────────────────────────────────────┐  │
│  │ [14:32:01] 启动工具，正在检测权限...       │  │
│  │ [14:32:01] ✓ 已获得管理员权限              │  │
│  │ [14:32:02] 正在检查路由配置...             │  │
│  │ [14:32:02] ✓ 路由已存在，无需重复配置      │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### 6.2 启动流程

```
程序启动（管理员，由 manifest 保证）
    ↓
初始化 backend（get_backend 抛异常 → 弹窗报错退出）
    ↓
显示主窗口，主题跟随系统
    ↓
后台线程：backend.is_admin() + backend.route_exists()
    ↓
更新 RoutePanel 状态：
    ├─ 路由已存在 → 状态"✓ 已配置"，按钮禁用
    └─ 路由不存在 → 状态"⚠ 未配置"，按钮可用
    ↓
写入启动日志
    ↓
等待用户操作
```

### 6.3 线程模型（避免界面卡死铁律）

**所有 backend 调用必须在子线程执行**，因为 `route`/`ping` 都是阻塞调用。UI 更新必须通过 `widget.after(0, callback)` 回到主线程。

```python
# 示意（非最终代码）
def on_test_click(self, printer: PrinterInfo):
    self._set_test_status(printer.ip, "🔄 测试中")
    self.log(f"开始测试 {printer.name} ({printer.ip})...")
    
    def worker():
        result = self.backend.ping(printer.ip)
        # 通过 after 回主线程更新 UI
        self.after(0, lambda: self._on_ping_done(printer, result))
    
    threading.Thread(target=worker, daemon=True).start()

def _on_ping_done(self, printer: PrinterInfo, result: PingResult):
    if result.ok:
        self._set_test_status(printer.ip, "✓ 通")
        self.log(f"✓ {printer.name} 可达 ({result.message})")
    else:
        self._set_test_status(printer.ip, "✗ 不通")
        self.log(f"✗ {printer.name} 不可达: {result.message}")
        if result.raw_output:
            self.log(f"  诊断信息: {result.raw_output}", level="debug")
```

**关键约束：**
- `daemon=True` 保证关窗时线程能回收
- ❌ 永远不在子线程直接改 widget（会崩或卡）
- ✅ 永远用 `after(0, ...)` 调度回主线程

### 6.4 主题

```python
customtkinter.set_appearance_mode("system")  # 跟随系统
customtkinter.set_default_color_theme("blue")
```

---

## 7. 错误处理策略

分级处理，不一刀切：

| 级别 | 场景 | 处理 |
|------|------|------|
| L1 可恢复操作错误 | ping 超时、route add 返回非 0、IP 格式错 | 日志区红字 + 状态图标变 ✗，程序继续 |
| L2 权限错误 | is_admin() 为 False、manifest 失效 | 弹窗解释 + 提示"请右键管理员运行" |
| L3 环境不支持 | Linux 运行、Mac 上未实现功能 | 弹窗"此功能暂不支持，请联系 IT" |
| L4 未预期异常 | 任何未捕获崩溃 | 写 error.log + 弹窗"出现错误，请截图发 IT" |

**全局兜底：** 主入口包 `try/except Exception`，捕获后写 `error.log`（带时间戳、traceback、系统信息）到 exe 同目录，并弹窗提示用户截图发 IT。

---

## 8. 构建与分发

### 8.1 pyproject.toml

```toml
[project]
name = "route-tool"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "customtkinter>=5.2.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pyinstaller>=6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/route_tool"]
```

### 8.2 UAC 提权：内嵌 manifest（方案 A）

PyInstaller 打包时内嵌管理员 manifest，同事双击直接弹 UAC。**省去程序内 ShellExecute 重启逻辑**，代码最简。

实现方式：通过 PyInstaller 的 `--uac-admin` 参数，或外挂 `admin.manifest` 文件 + `--uac-admin` 组合。打包脚本会生成对应的 version_info 文件嵌入版本号。

### 8.3 打包脚本 `scripts/build.py`

```python
# 伪代码
def build():
    # 1. 同步依赖
    run(["uv", "sync"])
    
    # 2. 生成 version_info.txt（从 pyproject.toml 读版本号）
    write_version_info()
    
    # 3. 打包 GUI 版（--windowed 无控制台 + --uac-admin）
    run([
        "uv", "run", "pyinstaller",
        "--onefile",
        "--windowed",
        "--uac-admin",                    # 内嵌管理员 manifest
        "--name", "公司网络配置工具",
        "--collect-all", "customtkinter", # CTk 主题资源必须手动收集
        "--version-file", "version_info.txt",
        "src/route_tool/__main__.py",
    ])
    
    # 4. 输出位置提示
    print("打包完成: dist/公司网络配置工具.exe")
```

### 8.4 打包坑预防清单

| 坑 | 预防 |
|----|------|
| CustomTkinter 主题资源丢失 | `--collect-all customtkinter` |
| UAC 不弹 | `--uac-admin` |
| 中文乱码崩溃 | subprocess 调用时显式指定 `encoding='gbk'`（Windows）|
| exe 没有图标 | 准备 `assets/icon.ico`，加 `--icon` |
| 版本号不一致 | 从 pyproject.toml 单一来源生成 version_info.txt |

---

## 9. 测试策略

### 9.1 单元测试（pytest）

- **models 测试**: `Result`/`PingResult` 数据类构造
- **route_exists 解析测试**: 用 fixture 保存真实 `route print` 输出样本，验证解析逻辑能正确识别已存在/不存在路由（防误匹配）
- **平台工厂测试**: mock `platform.system()` 返回值，验证抛 `UnsupportedOSError`
- **backend 测试**: mock `subprocess.run`，验证命令参数构造正确

### 9.2 集成测试（手动）

- 真实 Windows 机器：双击 exe → UAC → 配置路由 → ping 测试 → 全程无报错
- 路由已存在场景：重复运行，按钮应禁用
- 删除路由后重新运行：按钮应恢复可用

### 9.3 暂不实现

- Mac 集成测试（无 Mac 环境，标记为已知限制）
- 自动化 GUI 测试（CustomTkinter 测试成本高，收益低，首版靠手动）

---

## 10. 已知限制（首版）

1. **macOS 持久路由**：首版只做临时路由，重启失效，UI 明确告知
2. **macOS 权限**：需 sudo 运行，无图形化提权
3. **Linux 完全不支持**：启动即抛 `UnsupportedOSError`
4. **无自动更新**：新版本需重新下发 exe
5. **无添加打印机功能**：后期再实现
6. **无 CLI 版本**：后期再实现

---

## 11. 未来扩展点（不影响首版）

设计已为以下扩展预留接口，后期实现时**不需要改 UI 层和 core 层**：

1. **添加打印机功能**：在 `contracts.py` 加 `add_printer()` 方法，各平台 backend 实现，TestPanel 卡片加"安装"按钮
2. **CLI 版本**：新增 `ui/cli.py`，复用 core + platform，UI 层零改动
3. **Linux 支持**：新增 `platform/linux/backend.py`，实现 Protocol
4. **配置文件化**：将 `config.py` 改为从 `config.toml` 读取（若 IP 频繁变动）

---

## 12. 决策记录（Decision Log）

| 决策 | 选择 | 否决项 | 理由 |
|------|------|--------|------|
| 语言 | Python | Rust | 调系统命令场景，Rust 安全优势用不上 |
| GUI | CustomTkinter | tkinter/PyQt/Tauri | 现代 UI + 打包友好 + 无授权坑 |
| UAC | 内嵌 manifest | 程序内重启 | 代码最简，双击即弹 |
| CLI | 首版不做 | 同时出 | 减少维护面，远程协助用命令行即可 |
| 添加打印机 | 首版不做 | 立即实现 | YAGNI，先验证路由工具可用性 |
| 跨平台 | Win 全 + Mac 部分 | 全平台 | 实际用户分布决定 |
| 配置 | 写死 | 配置文件 | IP 基本不变，YAGNI |
| 主题 | 跟随系统 | 固定深/浅色 | 最自然，符合同事习惯 |
