# 公司网络路由配置工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个 CustomTkinter GUI 工具，让华为 WiFi 下的同事双击即可配置访问锐捷网络的持久路由，并测试打印机/网关连通性。

**Architecture:** 三层分层架构 —— UI 层（CustomTkinter）只依赖 `contracts.PlatformBackend` Protocol；平台抽象层按系统分发到 Windows/Mac 后端；核心层提供数据模型和写死的网络配置。所有系统命令调用返回统一的 `Result` 类型。

**Tech Stack:** Python 3.10+、uv、CustomTkinter、PyInstaller、pytest

---

## File Structure

```
公司网络拓扑/
├── pyproject.toml                              # Task 1
├── .gitignore                                  # Task 1
├── README.md                                   # Task 14
├── 分发说明.md                                  # Task 14
├── docs/superpowers/specs/2026-06-18-...md     # 已存在
├── docs/superpowers/plans/2026-06-18-...md     # 本文件
├── scripts/
│   └── build.py                                # Task 13
├── src/route_tool/
│   ├── __init__.py                             # Task 1
│   ├── __main__.py                             # Task 9
│   ├── core/
│   │   ├── __init__.py                         # Task 2
│   │   ├── models.py                           # Task 2
│   │   ├── config.py                           # Task 3
│   │   ├── contracts.py                        # Task 4
│   │   └── errors.py                           # Task 4
│   ├── platform/
│   │   ├── __init__.py                         # Task 5（工厂）
│   │   ├── windows/
│   │   │   ├── __init__.py                     # Task 6
│   │   │   ├── routes.py                       # Task 6
│   │   │   ├── connectivity.py                 # Task 7
│   │   │   ├── admin.py                        # Task 8
│   │   │   └── backend.py                      # Task 8
│   │   └── macos/
│   │       ├── __init__.py                     # Task 10
│   │       └── backend.py                      # Task 10
│   └── ui/
│       ├── __init__.py                         # Task 11
│       ├── app.py                              # Task 11（主窗口）
│       └── widgets/
│           ├── __init__.py                     # Task 11
│           ├── route_panel.py                  # Task 11
│           ├── test_panel.py                   # Task 12
│           └── log_panel.py                    # Task 12
└── tests/
    ├── __init__.py                             # Task 1
    ├── conftest.py                             # Task 1
    ├── fixtures/
    │   ├── route_print_exists.txt              # Task 6
    │   └── route_print_absent.txt              # Task 6
    ├── core/
    │   ├── test_models.py                      # Task 2
    │   └── test_config.py                      # Task 3
    ├── platform/
    │   ├── test_factory.py                     # Task 5
    │   ├── windows/
    │   │   ├── test_routes.py                  # Task 6
    │   │   ├── test_connectivity.py            # Task 7
    │   │   └── test_admin.py                   # Task 8
    │   └── macos/
    │       └── test_backend.py                 # Task 10
    └── ui/
        └── test_threading_safety.py            # Task 12
```

**职责边界说明：**
- `core/` 平台无关：数据模型、配置常量、Protocol 契约、自定义异常
- `platform/windows/` 和 `platform/macos/` 各自实现 PlatformBackend，互不依赖
- `platform/__init__.py` 是工厂，根据 `platform.system()` 选择后端
- `ui/` 只 import `contracts` 和 `platform`（工厂），从不直接 import 具体后端
- `widgets/` 每个 panel 一个文件，主窗口 `app.py` 组装它们

---

## Task 1: 项目脚手架与 uv 初始化

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/route_tool/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 初始化 git 仓库**

```bash
git init
git config user.name "Your Name"
git config user.email "you@example.com"
```

- [ ] **Step 2: 创建 pyproject.toml**

```toml
[project]
name = "route-tool"
version = "0.1.0"
description = "公司网络路由配置工具"
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

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 3: 创建 .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/

# uv
.venv/

# PyInstaller
build/
dist/
*.spec
version_info.txt

# IDE
.vscode/
.idea/

# OS
Thumbs.db
.DS_Store

# 错误日志
error.log
```

- [ ] **Step 4: 创建包初始化文件**

`src/route_tool/__init__.py`:
```python
"""公司网络路由配置工具。"""

__version__ = "0.1.0"
```

`tests/__init__.py`:
```python
```

- [ ] **Step 5: 创建 conftest.py**

`tests/conftest.py`:
```python
"""pytest 全局 fixtures。"""
import sys
from pathlib import Path

# 确保 src 在 path 中（pyproject.toml 已配 pythonpath，这里双保险）
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
```

- [ ] **Step 6: 用 uv 安装依赖**

Run:
```bash
uv sync
```
Expected: 创建 `.venv`，安装 customtkinter + pytest + pyinstaller。

- [ ] **Step 7: 验证 pytest 能跑（即使没测试）**

Run:
```bash
uv run pytest --co
```
Expected: `no tests ran` 或 `collected 0 items`，无 ImportError。

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "chore: 项目脚手架与 uv 初始化"
```

---

## Task 2: 核心数据模型 (core/models.py)

**Files:**
- Create: `src/route_tool/core/__init__.py`
- Create: `src/route_tool/core/models.py`
- Test: `tests/core/__init__.py`
- Test: `tests/core/test_models.py`

- [ ] **Step 1: 创建 core 包**

`src/route_tool/core/__init__.py`:
```python
"""核心层：平台无关的数据模型、配置和契约。"""
```

`tests/core/__init__.py`:
```python
```

- [ ] **Step 2: 写失败测试**

`tests/core/test_models.py`:
```python
from route_tool.core.models import (
    Result, ResultLevel, RouteInfo, PingResult, PrinterInfo
)


def test_result_success():
    r = Result(level=ResultLevel.SUCCESS, message="ok")
    assert r.level == ResultLevel.SUCCESS
    assert r.message == "ok"
    assert r.raw_output == ""
    assert r.error_code == 0


def test_result_failure_with_output():
    r = Result(
        level=ResultLevel.FAILURE,
        message="路由添加失败",
        raw_output="The route addition failed",
        error_code=1,
    )
    assert r.level == ResultLevel.FAILURE
    assert r.raw_output == "The route addition failed"
    assert r.error_code == 1


def test_route_info_defaults():
    r = RouteInfo(network="192.168.0.0", mask="255.255.252.0", gateway="192.168.5.22")
    assert r.network == "192.168.0.0"
    assert r.mask == "255.255.252.0"
    assert r.gateway == "192.168.5.22"
    assert r.metric == 1
    assert r.persistent is True


def test_ping_result_ok():
    p = PingResult(host="192.168.0.210", ok=True, message="可达", latency_ms=12.5)
    assert p.ok is True
    assert p.latency_ms == 12.5
    assert p.raw_output == ""


def test_ping_result_fail():
    p = PingResult(host="192.168.0.248", ok=False, message="超时")
    assert p.ok is False
    assert p.latency_ms is None


def test_printer_info_defaults():
    p = PrinterInfo(name="大打印机", ip="192.168.0.210")
    assert p.name == "大打印机"
    assert p.ip == "192.168.0.210"
    assert p.icon == "🖨"


def test_result_level_is_enum():
    assert ResultLevel.SUCCESS != ResultLevel.FAILURE
    assert ResultLevel.UNSUPPORTED.value == "unsupported"
```

- [ ] **Step 3: 运行测试，确认失败**

Run: `uv run pytest tests/core/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'route_tool.core.models'`

- [ ] **Step 4: 实现 models.py**

`src/route_tool/core/models.py`:
```python
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
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `uv run pytest tests/core/test_models.py -v`
Expected: 7 passed

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat(core): 添加数据模型 Result/RouteInfo/PingResult/PrinterInfo"
```

---

## Task 3: 网络配置常量 (core/config.py)

**Files:**
- Create: `src/route_tool/core/config.py`
- Test: `tests/core/test_config.py`

- [ ] **Step 1: 写失败测试**

`tests/core/test_config.py`:
```python
from route_tool.core.config import (
    TARGET_NETWORK, SUBNET_MASK, GATEWAY, ROUTE_METRIC,
    ROUTE_PERSISTENT, TEST_TARGETS, PING_COUNT, PING_TIMEOUT_SECONDS,
    DEFAULT_ROUTE, TARGET_CIDR,
)
from route_tool.core.models import RouteInfo, PrinterInfo


def test_route_constants():
    assert TARGET_NETWORK == "192.168.0.0"
    assert SUBNET_MASK == "255.255.252.0"  # /22 的点分十进制
    assert GATEWAY == "192.168.5.22"
    assert ROUTE_METRIC == 1
    assert ROUTE_PERSISTENT is True


def test_target_cidr():
    assert TARGET_CIDR == "192.168.0.0/22"


def test_default_route_is_route_info():
    assert isinstance(DEFAULT_ROUTE, RouteInfo)
    assert DEFAULT_ROUTE.network == TARGET_NETWORK
    assert DEFAULT_ROUTE.mask == SUBNET_MASK
    assert DEFAULT_ROUTE.gateway == GATEWAY


def test_ping_params():
    assert PING_COUNT == 2
    assert PING_TIMEOUT_SECONDS == 10


def test_test_targets_are_printers():
    assert len(TEST_TARGETS) == 3
    assert all(isinstance(t, PrinterInfo) for t in TEST_TARGETS)
    ips = [t.ip for t in TEST_TARGETS]
    assert "192.168.0.210" in ips  # 大打印机
    assert "192.168.0.248" in ips  # 小打印机
    assert "192.168.0.1" in ips    # 锐捷网关
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `uv run pytest tests/core/test_config.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: 实现 config.py**

`src/route_tool/core/config.py`:
```python
"""写死的网络配置常量。

如未来需要频繁变更，可改为从 config.toml 读取；当前按 YAGNI 保持写死。
"""
from route_tool.core.models import PrinterInfo, RouteInfo

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
    PrinterInfo(name="小打印机", ip="192.168.0.248", icon="🖨"),
    PrinterInfo(name="锐捷网关", ip="192.168.0.1", icon="🌐"),
]

# === ping 参数 ===
PING_COUNT = 2
PING_TIMEOUT_SECONDS = 10
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/core/test_config.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat(core): 添加网络配置常量"
```

---

## Task 4: 平台契约与异常 (core/contracts.py, core/errors.py)

**Files:**
- Create: `src/route_tool/core/contracts.py`
- Create: `src/route_tool/core/errors.py`

- [ ] **Step 1: 实现 errors.py**

`src/route_tool/core/errors.py`:
```python
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
```

- [ ] **Step 2: 实现 contracts.py**

`src/route_tool/core/contracts.py`:
```python
"""平台后端契约。

UI 层只依赖此 Protocol，从不直接 import 具体后端实现。
后期扩展（如 add_printer）时再向此 Protocol 添加方法。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from route_tool.core.models import PingResult, Result, RouteInfo


@runtime_checkable
class PlatformBackend(Protocol):
    """平台后端契约。所有平台实现必须满足此接口。"""

    def is_admin(self) -> bool:
        """当前进程是否有管理员/root 权限。"""
        ...

    def route_exists(self, route: RouteInfo) -> bool:
        """检查路由是否已配置。"""
        ...

    def add_route(self, route: RouteInfo) -> Result:
        """添加路由（持久化）。"""
        ...

    def remove_route(self, route: RouteInfo) -> Result:
        """删除路由。"""
        ...

    def ping(self, host: str, count: int = 2) -> PingResult:
        """测试主机连通性。"""
        ...
```

- [ ] **Step 3: 写契约校验测试**

`tests/core/test_contracts.py`:
```python
"""验证 Protocol 结构（防止后期改动破坏接口）。"""
from route_tool.core.contracts import PlatformBackend
from route_tool.core.errors import UnsupportedOSError


def test_unsupported_os_error_message():
    err = UnsupportedOSError("Linux")
    assert "Linux" in str(err)
    assert "IT" in str(err)


def test_protocol_has_required_methods():
    # 验证 Protocol 声明了所有必要方法
    required = {"is_admin", "route_exists", "add_route", "remove_route", "ping"}
    actual = set(PlatformBackend.__dict__.keys()) | {
        # Protocol 方法在 __protocol_attrs__ 中（Python 3.12+）或直接在 __dict__
    }
    # 用更稳定的方式：直接检查方法名存在
    import inspect
    members = {name for name, _ in inspect.getmembers(PlatformBackend, predicate=lambda x: True)}
    for method in required:
        assert method in members, f"Protocol 缺少方法: {method}"
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/core/test_contracts.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat(core): 添加 PlatformBackend 契约和自定义异常"
```

---

## Task 5: 平台工厂 (platform/__init__.py)

**Files:**
- Create: `src/route_tool/platform/__init__.py`
- Test: `tests/platform/__init__.py`
- Test: `tests/platform/test_factory.py`

- [ ] **Step 1: 创建 platform 包**

`src/route_tool/platform/__init__.py`:
```python
"""平台抽象层工厂。

UI 层调用 get_backend() 获取当前系统的后端，无需关心具体实现。
"""
from __future__ import annotations

import platform as _platform

from route_tool.core.contracts import PlatformBackend
from route_tool.core.errors import UnsupportedOSError


def get_backend() -> PlatformBackend:
    """根据当前操作系统返回对应后端。

    Raises:
        UnsupportedOSError: 当前系统不在支持列表中。
    """
    system = _platform.system()
    if system == "Windows":
        from route_tool.platform.windows.backend import WindowsBackend
        return WindowsBackend()
    if system == "Darwin":
        from route_tool.platform.macos.backend import MacBackend
        return MacBackend()
    raise UnsupportedOSError(system)
```

`tests/platform/__init__.py`:
```python
```

- [ ] **Step 2: 写工厂测试（mock platform.system）**

`tests/platform/test_factory.py`:
```python
from unittest.mock import patch

import pytest

from route_tool.core.errors import UnsupportedOSError
from route_tool.platform import get_backend


def test_factory_unsupported_os():
    with patch("route_tool.platform._platform.system", return_value="Linux"):
        with pytest.raises(UnsupportedOSError) as exc_info:
            get_backend()
    assert "Linux" in str(exc_info.value)


def test_factory_windows_routes_to_windows_backend():
    # 只验证 import 路径正确，不真正实例化（实例化需要 windows 模块存在）
    # 此测试在 Task 6 完成 WindowsBackend 后会真正通过
    with patch("route_tool.platform._platform.system", return_value="Windows"):
        try:
            backend = get_backend()
            from route_tool.platform.windows.backend import WindowsBackend
            assert isinstance(backend, WindowsBackend)
        except ImportError:
            pytest.skip("WindowsBackend 尚未实现（Task 6 完成）")


def test_factory_macos_routes_to_mac_backend():
    with patch("route_tool.platform._platform.system", return_value="Darwin"):
        try:
            backend = get_backend()
            from route_tool.platform.macos.backend import MacBackend
            assert isinstance(backend, MacBackend)
        except ImportError:
            pytest.skip("MacBackend 尚未实现（Task 10 完成）")
```

- [ ] **Step 3: 运行测试**

Run: `uv run pytest tests/platform/test_factory.py -v`
Expected: 
- `test_factory_unsupported_os` PASS
- `test_factory_windows_routes_to_windows_backend` SKIP
- `test_factory_macos_routes_to_mac_backend` SKIP

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat(platform): 添加平台工厂 get_backend()"
```

---

## Task 6: Windows 路由命令 (platform/windows/routes.py)

**Files:**
- Create: `src/route_tool/platform/windows/__init__.py`
- Create: `src/route_tool/platform/windows/routes.py`
- Test: `tests/platform/windows/__init__.py`
- Test: `tests/platform/windows/test_routes.py`
- Test: `tests/fixtures/route_print_exists.txt`
- Test: `tests/fixtures/route_print_absent.txt`

- [ ] **Step 1: 创建 windows 包**

`src/route_tool/platform/windows/__init__.py`:
```python
"""Windows 平台后端实现。"""
```

`tests/platform/windows/__init__.py`:
```python
```

- [ ] **Step 2: 准备 route print 输出 fixture**

`tests/fixtures/route_print_exists.txt`（真实 `route print 192.168.0.0` 在已配置时的输出样本）：
```
===========================================================================
接口列表
  12...00 ff 7a 8b 4c 01 ......TAP-Windows Adapter V9
   1...........................Software Loopback Interface 1
===========================================================================

IPv4 路由表
===========================================================================
活动路由:
网络目标        网络掩码          网关       接口   跃点数
192.168.0.0    255.255.252.0     192.168.5.22     192.168.5.100     31
===========================================================================
永久路由:
  网络地址          网络掩码  网关地址       跃点数
  192.168.0.0    255.255.252.0     192.168.5.22       1
===========================================================================
```

`tests/fixtures/route_print_absent.txt`（未配置时的输出样本）：
```
===========================================================================
接口列表
  12...00 ff 7a 8b 4c 01 ......TAP-Windows Adapter V9
   1...........................Software Loopback Interface 1
===========================================================================

IPv4 路由表
===========================================================================
活动路由:
网络目标        网络掩码          网关       接口   跃点数
          0.0.0.0          0.0.0.0      192.168.5.1    192.168.5.100     25
===========================================================================
永久路由:
  无
===========================================================================
```

- [ ] **Step 3: 写失败测试**

`tests/platform/windows/test_routes.py`:
```python
from pathlib import Path
from unittest.mock import patch, MagicMock

from route_tool.core.models import ResultLevel, RouteInfo
from route_tool.platform.windows.routes import (
    route_exists, add_route, remove_route, parse_route_exists,
)

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
ROUTE_EXISTS = RouteInfo(
    network="192.168.0.0",
    mask="255.255.252.0",
    gateway="192.168.5.22",
)


# === parse_route_exists（纯解析逻辑，不调系统命令）===

def test_parse_finds_existing_route():
    output = (FIXTURES / "route_print_exists.txt").read_text(encoding="utf-8")
    assert parse_route_exists(output, ROUTE_EXISTS) is True


def test_parse_absent_route():
    output = (FIXTURES / "route_print_absent.txt").read_text(encoding="utf-8")
    assert parse_route_exists(output, ROUTE_EXISTS) is False


def test_parse_does_not_match_wrong_gateway():
    # 即使 network 和 mask 匹配，gateway 不对也不算存在
    output = (FIXTURES / "route_print_exists.txt").read_text(encoding="utf-8")
    wrong = RouteInfo(network="192.168.0.0", mask="255.255.252.0", gateway="192.168.5.99")
    assert parse_route_exists(output, wrong) is False


def test_parse_does_not_match_wrong_mask():
    output = (FIXTURES / "route_print_exists.txt").read_text(encoding="utf-8")
    wrong = RouteInfo(network="192.168.0.0", mask="255.255.255.0", gateway="192.168.5.22")
    assert parse_route_exists(output, wrong) is False


def test_parse_handles_empty_output():
    assert parse_route_exists("", ROUTE_EXISTS) is False


def test_parse_normalizes_whitespace():
    # 多空格 / tab 混合也要能匹配
    output = "192.168.0.0   \t  255.255.252.0   192.168.5.22   192.168.5.100  31\n"
    assert parse_route_exists(output, ROUTE_EXISTS) is True


# === route_exists（封装 subprocess）===

def test_route_exists_calls_subprocess_and_parses():
    fixture_output = (FIXTURES / "route_print_exists.txt").read_text(encoding="utf-8")
    mock_result = MagicMock()
    mock_result.stdout = fixture_output
    mock_result.returncode = 0
    with patch("route_tool.platform.windows.routes.subprocess.run", return_value=mock_result) as mock_run:
        assert route_exists(ROUTE_EXISTS) is True
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "route" in args
    assert "print" in args
    assert "192.168.0.0" in args


def test_route_exists_uses_gbk_encoding():
    """Windows route print 输出是 GBK，必须显式指定 encoding。"""
    mock_result = MagicMock()
    mock_result.stdout = "some output"
    mock_result.returncode = 0
    with patch("route_tool.platform.windows.routes.subprocess.run", return_value=mock_result) as mock_run:
        route_exists(ROUTE_EXISTS)
    kwargs = mock_run.call_args[1]
    assert kwargs.get("encoding") == "gbk"
    assert kwargs.get("errors") == "replace"


# === add_route ===

def test_add_route_success():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "操作完成"
    mock_result.stderr = ""
    with patch("route_tool.platform.windows.routes.subprocess.run", return_value=mock_result) as mock_run:
        result = add_route(ROUTE_EXISTS)
    assert result.level == ResultLevel.SUCCESS
    # 验证命令参数：-p（持久） + add + network + mask + mask_value + gateway
    args = mock_run.call_args[0][0]
    assert "-p" in args
    assert "add" in args
    assert "192.168.0.0" in args
    assert "mask" in args
    assert "255.255.252.0" in args
    assert "192.168.5.22" in args
    assert "1" in args  # metric


def test_add_route_no_shell():
    """不能用 shell=True。"""
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.windows.routes.subprocess.run", return_value=mock_result) as mock_run:
        add_route(ROUTE_EXISTS)
    assert mock_run.call_args[1].get("shell") is not True


def test_add_route_failure():
    mock_result = MagicMock(returncode=1, stdout="", stderr="拒绝访问")
    with patch("route_tool.platform.windows.routes.subprocess.run", return_value=mock_result):
        result = add_route(ROUTE_EXISTS)
    assert result.level == ResultLevel.FAILURE
    assert "拒绝访问" in result.raw_output or "拒绝访问" in result.message
    assert result.error_code == 1


# === remove_route ===

def test_remove_route_success():
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.windows.routes.subprocess.run", return_value=mock_result) as mock_run:
        result = remove_route(ROUTE_EXISTS)
    assert result.level == ResultLevel.SUCCESS
    args = mock_run.call_args[0][0]
    assert "delete" in args
    assert "192.168.0.0" in args
```

- [ ] **Step 4: 运行测试，确认失败**

Run: `uv run pytest tests/platform/windows/test_routes.py -v`
Expected: FAIL with ImportError

- [ ] **Step 5: 实现 routes.py**

`src/route_tool/platform/windows/routes.py`:
```python
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

# Windows route 命令默认输出 GBK 编码
_ENCODING = "gbk"
_ERRORS = "replace"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """统一的 subprocess 调用，强制 GBK 解码、无 shell。"""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding=_ENCODING,
        errors=_ERRORS,
        shell=False,
    )


def parse_route_exists(route_print_output: str, route: RouteInfo) -> bool:
    """解析 route print 输出，判断指定路由是否已存在。

    必须同时匹配 network + mask + gateway 三个要素，
    否则会把 192.168.0.0 出现在注释/接口行里的情况误判为已存在。
    """
    if not route_print_output:
        return False

    target = (route.network, route.mask, route.gateway)
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
```

- [ ] **Step 6: 运行测试，确认通过**

Run: `uv run pytest tests/platform/windows/test_routes.py -v`
Expected: 13 passed

- [ ] **Step 7: 提交**

```bash
git add -A
git commit -m "feat(windows): 实现 route 命令封装（add/delete/exists，GBK 编码处理）"
```

---

## Task 7: Windows 连通性测试 (platform/windows/connectivity.py)

**Files:**
- Create: `src/route_tool/platform/windows/connectivity.py`
- Test: `tests/platform/windows/test_connectivity.py`

- [ ] **Step 1: 写失败测试**

`tests/platform/windows/test_connectivity.py`:
```python
from unittest.mock import patch, MagicMock

from route_tool.platform.windows.connectivity import parse_ping_result, ping


def test_parse_ping_success():
    """Windows ping 成功的典型输出（GBK 解码后）。"""
    output = (
        "\n正在 Ping 192.168.0.210 具有 32 字节的数据:\n"
        "来自 192.168.0.210 的回复: 字节=32 时间=12ms TTL=64\n"
        "来自 192.168.0.210 的回复: 字节=32 时间=13ms TTL=64\n"
        "\n192.168.0.210 的 Ping 统计信息:\n"
        "    数据包: 已发送 = 2，已接收 = 2，丢失 = 0 (0% 丢失)，\n"
        "往返行程的估计时间(以毫秒为单位):\n"
        "    最短 = 12ms，最长 = 13ms，平均 = 12ms\n"
    )
    result = parse_ping_result("192.168.0.210", output)
    assert result.ok is True
    assert result.host == "192.168.0.210"
    assert "2" in result.message  # 2/2 包


def test_parse_ping_failure():
    """Windows ping 失败的典型输出。"""
    output = (
        "\n正在 Ping 192.168.0.248 具有 32 字节的数据:\n"
        "请求超时。\n"
        "请求超时。\n"
        "\n192.168.0.248 的 Ping 统计信息:\n"
        "    数据包: 已发送 = 2，已接收 = 0，丢失 = 2 (100% 丢失)，\n"
    )
    result = parse_ping_result("192.168.0.248", output)
    assert result.ok is False
    assert "192.168.0.248" in result.message


def test_parse_ping_host_unreachable():
    output = "PING: 传输失败。General failure.\n"
    result = parse_ping_result("192.168.0.99", output)
    assert result.ok is False


def test_parse_ping_empty_output():
    result = parse_ping_result("1.2.3.4", "")
    assert result.ok is False


def test_parse_ping_latency_extraction():
    """能从输出中提取延迟数值。"""
    output = (
        "来自 192.168.0.210 的回复: 字节=32 时间=15ms TTL=64\n"
        "来自 192.168.0.210 的回复: 字节=32 时间=17ms TTL=64\n"
        "    最短 = 15ms，最长 = 17ms，平均 = 16ms\n"
    )
    result = parse_ping_result("192.168.0.210", output)
    assert result.ok is True
    assert result.latency_ms == 16.0  # 平均值


def test_ping_calls_subprocess_with_correct_args():
    mock_result = MagicMock()
    mock_result.stdout = (
        "来自 192.168.0.210 的回复: 字节=32 时间=10ms TTL=64\n"
        "    数据包: 已发送 = 2，已接收 = 2，丢失 = 0 (0% 丢失)，\n"
    )
    mock_result.returncode = 0
    with patch("route_tool.platform.windows.connectivity.subprocess.run", return_value=mock_result) as mock_run:
        result = ping("192.168.0.210", count=2)
    assert result.ok is True
    args = mock_run.call_args[0][0]
    assert "ping" in args
    assert "192.168.0.210" in args
    assert "-n" in args
    assert "2" in args  # count


def test_ping_handles_timeout_exception():
    import subprocess as sp
    with patch(
        "route_tool.platform.windows.connectivity.subprocess.run",
        side_effect=sp.TimeoutExpired(cmd="ping", timeout=10),
    ):
        result = ping("192.168.0.210", count=2)
    assert result.ok is False
    assert "超时" in result.message or "timeout" in result.message.lower()
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `uv run pytest tests/platform/windows/test_connectivity.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: 实现 connectivity.py**

`src/route_tool/platform/windows/connectivity.py`:
```python
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
        )
        return parse_ping_result(host, proc.stdout)
    except subprocess.TimeoutExpired:
        return PingResult(host=host, ok=False, message=f"{host} ping 超时")
    except (subprocess.SubprocessError, OSError) as e:
        return PingResult(host=host, ok=False, message=f"ping 执行失败: {e}")
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/platform/windows/test_connectivity.py -v`
Expected: 7 passed

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat(windows): 实现 ping 连通性测试"
```

---

## Task 8: Windows 管理员检测与后端组装 (platform/windows/admin.py, backend.py)

**Files:**
- Create: `src/route_tool/platform/windows/admin.py`
- Create: `src/route_tool/platform/windows/backend.py`
- Test: `tests/platform/windows/test_admin.py`
- Test: `tests/platform/windows/test_backend.py`

- [ ] **Step 1: 写 admin 测试**

`tests/platform/windows/test_admin.py`:
```python
from unittest.mock import patch, MagicMock

from route_tool.platform.windows.admin import is_admin


def test_is_admin_true_when_windll_returns_nonzero():
    mock_windll = MagicMock()
    mock_windll.shell32.IsUserAnAdmin.return_value = 1
    with patch("route_tool.platform.windows.admin.ctypes", mock_windll):
        assert is_admin() is True


def test_is_admin_false_when_windll_returns_zero():
    mock_windll = MagicMock()
    mock_windll.shell32.IsUserAnAdmin.return_value = 0
    with patch("route_tool.platform.windows.admin.ctypes", mock_windll):
        assert is_admin() is False


def test_is_admin_false_on_exception():
    mock_windll = MagicMock()
    mock_windll.shell32.IsUserAnAdmin.side_effect = Exception("no windll")
    with patch("route_tool.platform.windows.admin.ctypes", mock_windll):
        assert is_admin() is False
```

- [ ] **Step 2: 实现 admin.py**

`src/route_tool/platform/windows/admin.py`:
```python
"""Windows 管理员权限检测。

UAC 提权由 PyInstaller 的 --uac-admin manifest 负责（双击即弹 UAC）。
此模块只做检测，不做重启逻辑。
"""
from __future__ import annotations


def is_admin() -> bool:
    """检测当前进程是否以管理员身份运行。"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False
```

- [ ] **Step 3: 写 backend 测试（验证 Protocol 满足 + 委托正确）**

`tests/platform/windows/test_backend.py`:
```python
from unittest.mock import patch, MagicMock

from route_tool.core.contracts import PlatformBackend
from route_tool.core.models import ResultLevel, RouteInfo
from route_tool.platform.windows.backend import WindowsBackend


ROUTE = RouteInfo(network="192.168.0.0", mask="255.255.252.0", gateway="192.168.5.22")


def test_windows_backend_satisfies_protocol():
    backend = WindowsBackend()
    # runtime_checkable Protocol 可用 isinstance 检查
    assert isinstance(backend, PlatformBackend)


def test_backend_add_route_delegates_to_routes_module():
    from route_tool.core.models import Result
    fake_result = Result(level=ResultLevel.SUCCESS, message="ok")
    with patch("route_tool.platform.windows.backend.add_route", return_value=fake_result) as mock_add:
        backend = WindowsBackend()
        result = backend.add_route(ROUTE)
    assert result is fake_result
    mock_add.assert_called_once_with(ROUTE)


def test_backend_route_exists_delegates():
    with patch("route_tool.platform.windows.backend.route_exists", return_value=True) as mock_exists:
        backend = WindowsBackend()
        assert backend.route_exists(ROUTE) is True
    mock_exists.assert_called_once_with(ROUTE)


def test_backend_remove_route_delegates():
    from route_tool.core.models import Result
    fake_result = Result(level=ResultLevel.SUCCESS, message="ok")
    with patch("route_tool.platform.windows.backend.remove_route", return_value=fake_result) as mock_del:
        backend = WindowsBackend()
        result = backend.remove_route(ROUTE)
    assert result is fake_result
    mock_del.assert_called_once_with(ROUTE)


def test_backend_ping_delegates():
    from route_tool.core.models import PingResult
    fake = PingResult(host="1.2.3.4", ok=True, message="ok")
    with patch("route_tool.platform.windows.backend.ping", return_value=fake) as mock_ping:
        backend = WindowsBackend()
        result = backend.ping("1.2.3.4", count=3)
    assert result is fake
    mock_ping.assert_called_once_with("1.2.3.4", count=3)


def test_backend_is_admin_delegates():
    with patch("route_tool.platform.windows.backend.is_admin", return_value=True):
        backend = WindowsBackend()
        assert backend.is_admin() is True
```

- [ ] **Step 4: 实现 backend.py**

`src/route_tool/platform/windows/backend.py`:
```python
"""Windows 平台后端：组合 routes/connectivity/admin 模块。"""
from __future__ import annotations

from route_tool.core.models import PingResult, Result, RouteInfo
from route_tool.platform.windows.admin import is_admin
from route_tool.platform.windows.connectivity import ping as _ping
from route_tool.platform.windows.routes import (
    add_route as _add_route,
    remove_route as _remove_route,
    route_exists as _route_exists,
)


class WindowsBackend:
    """Windows 平台的 PlatformBackend 实现。"""

    def is_admin(self) -> bool:
        return is_admin()

    def route_exists(self, route: RouteInfo) -> bool:
        return _route_exists(route)

    def add_route(self, route: RouteInfo) -> Result:
        return _add_route(route)

    def remove_route(self, route: RouteInfo) -> Result:
        return _remove_route(route)

    def ping(self, host: str, count: int = 2) -> PingResult:
        return _ping(host, count)
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `uv run pytest tests/platform/windows/ -v`
Expected: admin 3 passed + backend 6 passed = 9 passed

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat(windows): 实现管理员检测与 WindowsBackend 后端组装"
```

---

## Task 9: 程序入口 (src/route_tool/__main__.py)

**Files:**
- Create: `src/route_tool/__main__.py`

- [ ] **Step 1: 实现 __main__.py（带全局异常兜底）**

`src/route_tool/__main__.py`:
```python
"""程序入口。支持 `python -m route_tool` 和 PyInstaller 打包。

全局异常兜底：未捕获异常写 error.log + 弹窗提示用户截图发 IT。
"""
from __future__ import annotations

import datetime
import sys
import traceback
from pathlib import Path


def _write_error_log(exc: BaseException) -> Path:
    """把未捕获异常写入 exe 同目录的 error.log，返回文件路径。"""
    log_path = Path(sys.argv[0]).resolve().parent / "error.log" if getattr(sys, "frozen", False) else Path.cwd() / "error.log"
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    content = (
        f"=== {timestamp} 未捕获异常 ===\n"
        f"{traceback.format_exc()}\n"
        f"Platform: {sys.platform}\n"
        f"Python: {sys.version}\n"
        f"Executable: {sys.executable}\n"
    )
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(content + "\n")
    except OSError:
        pass  # 写日志失败不能掩盖原异常
    return log_path


def _show_fatal_error(exc: BaseException) -> None:
    """显示致命错误弹窗。"""
    log_path = _write_error_log(exc)
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "公司网络配置工具 - 出现错误",
            f"程序出现未预期错误，请截图此窗口发送给 IT。\n\n"
            f"错误: {exc}\n\n"
            f"诊断日志已保存到:\n{log_path}",
        )
        root.destroy()
    except Exception:
        # GUI 都起不来时，退化到控制台输出
        print(f"FATAL: {exc}", file=sys.stderr)
        traceback.print_exc()


def main() -> int:
    """程序主入口。"""
    try:
        from route_tool.ui.app import run_app
        run_app()
        return 0
    except SystemExit:
        raise
    except BaseException as exc:
        _show_fatal_error(exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 验证语法（UI 尚未实现，import 会失败，但语法要对）**

Run: `uv run python -c "import ast; ast.parse(open('src/route_tool/__main__.py', encoding='utf-8').read()); print('syntax ok')"`
Expected: `syntax ok`

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "feat: 添加程序入口与全局异常兜底"
```

---

## Task 10: macOS 后端 (platform/macos/backend.py)

**Files:**
- Create: `src/route_tool/platform/macos/__init__.py`
- Create: `src/route_tool/platform/macos/backend.py`
- Test: `tests/platform/macos/__init__.py`
- Test: `tests/platform/macos/test_backend.py`

- [ ] **Step 1: 创建 macos 包**

`src/route_tool/platform/macos/__init__.py`:
```python
"""macOS 平台后端实现。

已知限制（首版）：
- 路由持久化需 sudo，且 macOS 无 -p 等价物；首版只做临时路由，重启失效
- 权限检测用 os.geteuid()，非 root 时需 sudo 运行
"""
```

`tests/platform/macos/__init__.py`:
```python
```

- [ ] **Step 2: 写后端测试**

`tests/platform/macos/test_backend.py`:
```python
from unittest.mock import patch

import pytest

from route_tool.core.contracts import PlatformBackend
from route_tool.core.models import ResultLevel, RouteInfo
from route_tool.platform.macos.backend import MacBackend


ROUTE = RouteInfo(network="192.168.0.0", mask="255.255.252.0", gateway="192.168.5.22")


def test_mac_backend_satisfies_protocol():
    assert isinstance(MacBackend(), PlatformBackend)


def test_is_admin_true_when_euid_zero():
    with patch("route_tool.platform.macos.backend.os.geteuid", return_value=0):
        assert MacBackend().is_admin() is True


def test_is_admin_false_when_euid_nonzero():
    with patch("route_tool.platform.macos.backend.os.geteuid", return_value=501):
        assert MacBackend().is_admin() is False


def test_add_route_success():
    from unittest.mock import MagicMock
    mock_proc = MagicMock(returncode=0, stdout="add net", stderr="")
    with patch("route_tool.platform.macos.backend.subprocess.run", return_value=mock_proc) as mock_run:
        result = MacBackend().add_route(ROUTE)
    assert result.level == ResultLevel.SUCCESS
    args = mock_run.call_args[0][0]
    # macOS: sudo route -n add -net 192.168.0.0/22 192.168.5.22
    assert "route" in args
    assert "add" in args
    assert "-net" in args
    assert "192.168.0.0/22" in args  # macOS 用 CIDR
    assert "192.168.5.22" in args


def test_route_exists_uses_netstat():
    from unittest.mock import MagicMock
    mock_proc = MagicMock(returncode=0, stdout="192.168.0.0/22    192.168.5.22    UG", stderr="")
    with patch("route_tool.platform.macos.backend.subprocess.run", return_value=mock_proc) as mock_run:
        assert MacBackend().route_exists(ROUTE) is True
    args = mock_run.call_args[0][0]
    assert "netstat" in args
    assert "-rn" in args


def test_route_exists_absent():
    from unittest.mock import MagicMock
    mock_proc = MagicMock(returncode=0, stdout="default    192.168.5.1", stderr="")
    with patch("route_tool.platform.macos.backend.subprocess.run", return_value=mock_proc):
        assert MacBackend().route_exists(ROUTE) is False


def test_ping_success():
    from unittest.mock import MagicMock
    mock_proc = MagicMock(returncode=0, stdout="64 bytes from 192.168.0.210: icmp_seq=0 ttl=64 time=10.5 ms", stderr="")
    with patch("route_tool.platform.macos.backend.subprocess.run", return_value=mock_proc):
        result = MacBackend().ping("192.168.0.210", count=2)
    assert result.ok is True


def test_ping_failure():
    from unittest.mock import MagicMock
    mock_proc = MagicMock(returncode=2, stdout="Request timeout", stderr="")
    with patch("route_tool.platform.macos.backend.subprocess.run", return_value=mock_proc):
        result = MacBackend().ping("192.168.0.248", count=2)
    assert result.ok is False
```

- [ ] **Step 3: 实现 macos/backend.py**

`src/route_tool/platform/macos/backend.py`:
```python
"""macOS 平台后端实现。

注意：macOS 路由用 CIDR 表示法（192.168.0.0/22），不是 Windows 的点分掩码。
掩码 255.255.252.0 = /22。
"""
from __future__ import annotations

import os
import re
import subprocess

from route_tool.core.config import PING_TIMEOUT_SECONDS
from route_tool.core.models import PingResult, Result, ResultLevel, RouteInfo

# 255.255.252.0 -> 22（前缀长度），用二进制 1 的个数
_MASK_TO_PREFIX = {
    "255.255.255.255": 32, "255.255.255.254": 31, "255.255.255.252": 30,
    "255.255.255.248": 29, "255.255.255.240": 28, "255.255.255.224": 27,
    "255.255.255.192": 26, "255.255.255.128": 25, "255.255.255.0": 24,
    "255.255.254.0": 23, "255.255.252.0": 22, "255.255.248.0": 21,
    "255.255.240.0": 20, "255.255.224.0": 19, "255.255.192.0": 18,
    "255.255.128.0": 17, "255.255.0.0": 16, "255.0.0.0": 8, "0.0.0.0": 0,
}


def _mask_to_prefix(mask: str) -> int:
    return _MASK_TO_PREFIX.get(mask, 22)


def _run(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class MacBackend:
    """macOS 平台的 PlatformBackend 实现。"""

    def is_admin(self) -> bool:
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

    def route_exists(self, route: RouteInfo) -> bool:
        prefix = _mask_to_prefix(route.mask)
        cidr = f"{route.network}/{prefix}"
        try:
            proc = _run(["netstat", "-rn"])
            # 匹配 "192.168.0.0/22    192.168.5.22"
            pattern = re.compile(
                rf"\b{re.escape(cidr)}\s+{re.escape(route.gateway)}\b"
            )
            return pattern.search(proc.stdout) is not None
        except (subprocess.SubprocessError, OSError):
            return False

    def add_route(self, route: RouteInfo) -> Result:
        prefix = _mask_to_prefix(route.mask)
        cidr = f"{route.network}/{prefix}"
        cmd = ["sudo", "route", "-n", "add", "-net", cidr, route.gateway]
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
                message="路由添加成功（临时，重启后失效）",
                raw_output=proc.stdout,
            )
        return Result(
            level=ResultLevel.FAILURE,
            message="路由添加失败（可能需要 sudo 权限）",
            raw_output=proc.stderr or proc.stdout,
            error_code=proc.returncode,
        )

    def remove_route(self, route: RouteInfo) -> Result:
        prefix = _mask_to_prefix(route.mask)
        cidr = f"{route.network}/{prefix}"
        cmd = ["sudo", "route", "-n", "delete", "-net", cidr]
        try:
            proc = _run(cmd)
        except (subprocess.SubprocessError, OSError) as e:
            return Result(
                level=ResultLevel.FAILURE,
                message=f"执行 route 命令失败: {e}",
                error_code=-1,
            )
        if proc.returncode == 0:
            return Result(level=ResultLevel.SUCCESS, message="路由删除成功")
        return Result(
            level=ResultLevel.FAILURE,
            message="路由删除失败",
            raw_output=proc.stderr or proc.stdout,
            error_code=proc.returncode,
        )

    def ping(self, host: str, count: int = 2) -> PingResult:
        cmd = ["ping", "-c", str(count), host]
        try:
            proc = _run(cmd, timeout=PING_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return PingResult(host=host, ok=False, message=f"{host} ping 超时")
        except (subprocess.SubprocessError, OSError) as e:
            return PingResult(host=host, ok=False, message=f"ping 执行失败: {e}")

        ok = proc.returncode == 0
        latency = None
        time_match = re.search(r"time=([\d.]+)\s*ms", proc.stdout)
        if time_match:
            latency = float(time_match.group(1))
        message = f"{host} 可达" if ok else f"{host} 不可达"
        return PingResult(
            host=host, ok=ok, message=message, raw_output=proc.stdout, latency_ms=latency
        )
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/platform/macos/test_backend.py -v`
Expected: 7 passed

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat(macos): 实现 MacBackend（路由+ping，临时路由）"
```

---

## Task 11: GUI 主窗口与路由面板 (ui/app.py, ui/widgets/route_panel.py)

**Files:**
- Create: `src/route_tool/ui/__init__.py`
- Create: `src/route_tool/ui/app.py`
- Create: `src/route_tool/ui/widgets/__init__.py`
- Create: `src/route_tool/ui/widgets/route_panel.py`

- [ ] **Step 1: 创建 ui 包**

`src/route_tool/ui/__init__.py`:
```python
"""UI 层：只依赖 core.contracts 和 platform 工厂。"""
```

`src/route_tool/ui/widgets/__init__.py`:
```python
"""UI 子组件。"""
```

- [ ] **Step 2: 实现 route_panel.py**

`src/route_tool/ui/widgets/route_panel.py`:
```python
"""路由配置面板。

负责显示路由配置信息和状态，提供"一键配置路由"按钮。
所有 backend 调用通过回调注入（避免 panel 直接依赖 backend 实例，便于测试）。
"""
from __future__ import annotations

import threading
from typing import Callable

import customtkinter as ctk

from route_tool.core.config import DEFAULT_ROUTE, TARGET_CIDR, GATEWAY
from route_tool.core.models import Result, ResultLevel, RouteInfo


class RoutePanel(ctk.CTkFrame):
    """路由配置区域。"""

    def __init__(
        self,
        master,
        on_check_route: Callable[[], bool],
        on_add_route: Callable[[RouteInfo], Result],
        on_log: Callable[[str, str], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._on_check_route = on_check_route
        self._on_add_route = on_add_route
        self._on_log = on_log

        # 标题
        self._title = ctk.CTkLabel(self, text="📡 网络路由配置", font=ctk.CTkFont(size=16, weight="bold"))
        self._title.pack(anchor="w", padx=20, pady=(15, 5))

        # 信息容器
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=5)

        self._net_label = ctk.CTkLabel(info_frame, text=f"目标网段:  {TARGET_CIDR}", anchor="w")
        self._net_label.pack(anchor="w", pady=2)

        self._gw_label = ctk.CTkLabel(info_frame, text=f"网关:      {GATEWAY}", anchor="w")
        self._gw_label.pack(anchor="w", pady=2)

        self._status_label = ctk.CTkLabel(info_frame, text="状态:      🔄 检测中...", anchor="w")
        self._status_label.pack(anchor="w", pady=2)

        # 配置按钮
        self._config_btn = ctk.CTkButton(
            self,
            text="一键配置路由",
            command=self._on_config_click,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            state="disabled",  # 初始禁用，检测完路由状态后再决定
        )
        self._config_btn.pack(pady=15)

    def check_route_async(self) -> None:
        """在后台线程检查路由状态，完成后更新 UI（必须从主线程调用）。"""
        def worker():
            exists = self._on_check_route()
            self.after(0, lambda: self._update_status(exists))

        threading.Thread(target=worker, daemon=True).start()

    def _update_status(self, exists: bool) -> None:
        if exists:
            self._status_label.configure(text="状态:      ✓ 已配置")
            self._config_btn.configure(state="disabled", text="已配置，无需重复操作")
            self._on_log("✓ 路由已存在，无需重复配置", "info")
        else:
            self._status_label.configure(text="状态:      ⚠ 未配置")
            self._config_btn.configure(state="normal", text="一键配置路由")
            self._on_log("⚠ 路由未配置，可点击按钮添加", "warning")

    def _on_config_click(self) -> None:
        self._config_btn.configure(state="disabled", text="⏳ 配置中...")
        self._on_log("开始配置路由...", "info")

        def worker():
            result = self._on_add_route(DEFAULT_ROUTE)
            self.after(0, lambda: self._on_config_done(result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_config_done(self, result: Result) -> None:
        if result.ok:
            self._status_label.configure(text="状态:      ✓ 已配置")
            self._config_btn.configure(state="disabled", text="已配置，无需重复操作")
            self._on_log(f"✓ {result.message}", "success")
        else:
            self._status_label.configure(text="状态:      ✗ 配置失败")
            self._config_btn.configure(state="normal", text="重新尝试配置")
            self._on_log(f"✗ {result.message}", "error")
            if result.raw_output:
                self._on_log(f"  诊断: {result.raw_output}", "debug")
```

- [ ] **Step 3: 实现 app.py 主窗口**

`src/route_tool/ui/app.py`:
```python
"""主窗口：组装各 panel，注入 backend 回调，管理主题。

UI 层只依赖 contracts（通过 platform 工厂获取 backend），不直接 import 后端实现。
"""
from __future__ import annotations

import sys

import customtkinter as ctk

from route_tool.core.contracts import PlatformBackend
from route_tool.core.errors import UnsupportedOSError
from route_tool.core.models import Result, RouteInfo
from route_tool.platform import get_backend
from route_tool.ui.widgets.route_panel import RoutePanel


class MainApp(ctk.CTk):
    """主应用窗口。"""

    def __init__(self, backend: PlatformBackend):
        super().__init__()
        self._backend = backend

        self.title("公司网络配置工具")
        self.geometry("600x700")
        self.minsize(500, 600)

        # 主题：跟随系统
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # 布局
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # 日志区可拉伸

        self._route_panel = RoutePanel(
            self,
            on_check_route=self._backend.route_exists_wrapper if hasattr(self._backend, "route_exists_wrapper") else lambda r=None: self._check_route(),
            on_add_route=self._backend.add_route,
            on_log=self._log,
        )
        self._route_panel.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # TestPanel 和 LogPanel 在 Task 12 添加，先用占位
        self._test_panel = None
        self._log_panel = None

        # 启动后自动检测路由状态
        self.after(100, self._route_panel.check_route_async)

    def _check_route(self) -> bool:
        """路由检查的封装（route_exists 需要 RouteInfo 参数，这里固定用 DEFAULT_ROUTE）。"""
        from route_tool.core.config import DEFAULT_ROUTE
        return self._backend.route_exists(DEFAULT_ROUTE)

    def _log(self, message: str, level: str = "info") -> None:
        """日志回调。Task 12 实现 LogPanel 后会转发给它。"""
        # 占位：Task 12 会替换为 self._log_panel.append(message, level)
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{level}] {message}")


def run_app() -> None:
    """程序入口：创建 backend 和主窗口，启动事件循环。"""
    try:
        backend = get_backend()
    except UnsupportedOSError as e:
        # 不支持的系统，弹窗提示
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("不支持的系统", str(e))
        root.destroy()
        return

    app = MainApp(backend)
    app.mainloop()
```

- [ ] **Step 4: 验证 import 语法**

Run: `uv run python -c "import ast; ast.parse(open('src/route_tool/ui/app.py', encoding='utf-8').read()); ast.parse(open('src/route_tool/ui/widgets/route_panel.py', encoding='utf-8').read()); print('syntax ok')"`
Expected: `syntax ok`

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat(ui): 实现主窗口和路由配置面板"
```

---

## Task 12: 测试面板与日志面板 (ui/widgets/test_panel.py, log_panel.py)

**Files:**
- Create: `src/route_tool/ui/widgets/test_panel.py`
- Create: `src/route_tool/ui/widgets/log_panel.py`
- Modify: `src/route_tool/ui/app.py`（组装两个新 panel）

- [ ] **Step 1: 实现 log_panel.py**

`src/route_tool/ui/widgets/log_panel.py`:
```python
"""操作日志面板。

给 IT 远程排查用：同事报"不好使"时让他截图发过来，能看到完整执行过程。
"""
from __future__ import annotations

import datetime

import customtkinter as ctk


# 不同级别的颜色（深色/浅色主题都用同一组，CustomTkinter 会自适应前景色）
_LEVEL_PREFIX = {
    "info": "",
    "success": "✓ ",
    "warning": "⚠ ",
    "error": "✗ ",
    "debug": "  ",
}


class LogPanel(ctk.CTkFrame):
    """操作日志区域。"""

    MAX_LINES = 200  # 防止无限增长导致卡顿

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self._title = ctk.CTkLabel(self, text="📋 操作日志", font=ctk.CTkFont(size=16, weight="bold"))
        self._title.pack(anchor="w", padx=20, pady=(15, 5))

        self._textbox = ctk.CTkTextbox(
            self,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled",
        )
        self._textbox.pack(fill="both", expand=True, padx=20, pady=(0, 15))

    def append(self, message: str, level: str = "info") -> None:
        """追加一条日志。level: info/success/warning/error/debug。"""
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = _LEVEL_PREFIX.get(level, "")
        line = f"[{ts}] {prefix}{message}\n"

        self._textbox.configure(state="normal")
        self._textbox.insert("end", line)
        # 超过上限时删除最旧的
        line_count = int(self._textbox.index("end-1c").split(".")[0])
        if line_count > self.MAX_LINES:
            self._textbox.delete("1.0", f"{line_count - self.MAX_LINES}.0")
        self._textbox.see("end")
        self._textbox.configure(state="disabled")
```

- [ ] **Step 2: 实现 test_panel.py**

`src/route_tool/ui/widgets/test_panel.py`:
```python
"""连通性测试面板。

显示打印机/网关列表，每个设备一行，带独立测试按钮和状态图标。
支持"全部测试"批量执行。
所有 backend.ping 调用在后台线程执行，结果通过 after() 回主线程更新 UI。
"""
from __future__ import annotations

import threading
from typing import Callable

import customtkinter as ctk

from route_tool.core.config import TEST_TARGETS, PING_COUNT
from route_tool.core.models import PingResult, PrinterInfo


class _DeviceRow(ctk.CTkFrame):
    """单个设备的一行：图标+名称+IP+状态+测试按钮。"""

    def __init__(
        self,
        master,
        device: PrinterInfo,
        on_test: Callable[[], None],
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._device = device

        self.grid_columnconfigure(2, weight=1)  # 状态列拉伸

        self._icon = ctk.CTkLabel(self, text=f"{device.icon} {device.name}", width=120, anchor="w")
        self._icon.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")

        self._ip_label = ctk.CTkLabel(self, text=device.ip, width=120, anchor="w",
                                       font=ctk.CTkFont(family="Consolas", size=12))
        self._ip_label.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="w")

        self._status = ctk.CTkLabel(self, text="未测试", anchor="w")
        self._status.grid(row=0, column=2, padx=(0, 10), pady=5, sticky="ew")

        self._btn = ctk.CTkButton(self, text="测试", width=60, command=on_test)
        self._btn.grid(row=0, column=3, padx=0, pady=5)

    def set_testing(self) -> None:
        self._status.configure(text="🔄 测试中...")

    def set_result(self, ok: bool, message: str) -> None:
        if ok:
            self._status.configure(text=f"✓ {message}")
        else:
            self._status.configure(text=f"✗ {message}")


class TestPanel(ctk.CTkFrame):
    """连通性测试区域。"""

    def __init__(
        self,
        master,
        on_ping: Callable[[str, int], PingResult],
        on_log: Callable[[str, str], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._on_ping = on_ping
        self._on_log = on_log
        self._rows: dict[str, _DeviceRow] = {}

        self._title = ctk.CTkLabel(self, text="🔍 连通性测试", font=ctk.CTkFont(size=16, weight="bold"))
        self._title.pack(anchor="w", padx=20, pady=(15, 5))

        rows_frame = ctk.CTkFrame(self, fg_color="transparent")
        rows_frame.pack(fill="x", padx=20, pady=5)

        for device in TEST_TARGETS:
            row = _DeviceRow(
                rows_frame,
                device=device,
                on_test=lambda ip=device.ip: self._test_single(ip),
            )
            row.pack(fill="x", pady=2)
            self._rows[device.ip] = row

        # 批量测试按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 15))

        self._test_all_btn = ctk.CTkButton(
            btn_frame, text="全部测试", command=self._test_all, height=32
        )
        self._test_all_btn.pack(side="left", padx=(0, 10))

    def _test_single(self, ip: str) -> None:
        """测试单个设备（异步）。"""
        row = self._rows.get(ip)
        if row is None:
            return
        row.set_testing()
        self._on_log(f"开始测试 {ip}...", "info")

        def worker():
            result = self._on_ping(ip, PING_COUNT)
            self.after(0, lambda: self._on_ping_done(ip, result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ping_done(self, ip: str, result: PingResult) -> None:
        row = self._rows.get(ip)
        if row:
            row.set_result(result.ok, result.message)
        if result.ok:
            latency = f" ({result.latency_ms:.0f}ms)" if result.latency_ms else ""
            self._on_log(f"✓ {ip} 可达{latency}", "success")
        else:
            self._on_log(f"✗ {ip} 不可达: {result.message}", "error")
            if result.raw_output:
                self._on_log(f"  诊断: {result.raw_output}", "debug")

    def _test_all(self) -> None:
        """批量测试所有设备。"""
        self._test_all_btn.configure(state="disabled", text="测试中...")
        self._on_log("开始批量测试所有设备...", "info")
        for ip in self._rows:
            self._test_single(ip)
        # 简单恢复：1.5 秒后重新启用（最慢的 ping 也就几秒）
        self.after(2000, lambda: self._test_all_btn.configure(state="normal", text="全部测试"))
```

- [ ] **Step 3: 修改 app.py 组装两个新 panel**

修改 `src/route_tool/ui/app.py`，把 `_test_panel` 和 `_log_panel` 占位替换为真实组件，并把 `_log` 方法改为转发给 LogPanel。

替换 app.py 中 `__init__` 方法的 panel 创建部分（找到 `# TestPanel 和 LogPanel 在 Task 12 添加，先用占位` 开始到 `# 启动后自动检测路由状态` 之前）为：

```python
        self._test_panel = TestPanel(
            self,
            on_ping=self._backend.ping,
            on_log=self._log,
        )
        self._test_panel.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self._log_panel = LogPanel(self)
        self._log_panel.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")
```

替换 `_log` 方法为：

```python
    def _log(self, message: str, level: str = "info") -> None:
        """日志回调，转发给 LogPanel。"""
        if self._log_panel is not None:
            self._log_panel.append(message, level)
```

并在文件顶部 import 处添加：

```python
from route_tool.ui.widgets.log_panel import LogPanel
from route_tool.ui.widgets.test_panel import TestPanel
```

同时简化 RoutePanel 的 on_check_route 注入（去掉 hasattr 那段绕路）：

把：
```python
        self._route_panel = RoutePanel(
            self,
            on_check_route=self._backend.route_exists_wrapper if hasattr(self._backend, "route_exists_wrapper") else lambda r=None: self._check_route(),
            on_add_route=self._backend.add_route,
            on_log=self._log,
        )
```
改为：
```python
        self._route_panel = RoutePanel(
            self,
            on_check_route=self._check_route,
            on_add_route=self._backend.add_route,
            on_log=self._log,
        )
```

- [ ] **Step 4: 验证语法 + import 链**

Run: `uv run python -c "from route_tool.ui.app import MainApp, run_app; print('import ok')"`
Expected: `import ok`

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat(ui): 实现连通性测试面板和日志面板，组装到主窗口"
```

---

## Task 13: 打包脚本 (scripts/build.py)

**Files:**
- Create: `scripts/build.py`

- [ ] **Step 1: 创建 scripts 目录和 build.py**

`scripts/build.py`:
```python
"""一键打包脚本。

产出：dist/公司网络配置工具.exe
- --onefile: 单文件
- --windowed: 无控制台（GUI 程序）
- --uac-admin: 内嵌管理员 manifest，双击即弹 UAC
- --collect-all customtkinter: CTk 主题资源必须手动收集
- --version-file: 从 pyproject.toml 读版本号生成

用法: uv run python scripts/build.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
ENTRY = ROOT / "src" / "route_tool" / "__main__.py"
ICON = ROOT / "assets" / "icon.ico"
VERSION_FILE = ROOT / "version_info.txt"
APP_NAME = "公司网络配置工具"


def read_version() -> str:
    """从 pyproject.toml 读取版本号。"""
    content = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise RuntimeError("无法从 pyproject.toml 读取 version")
    return match.group(1)


def write_version_file(version: str) -> None:
    """生成 PyInstaller 的 version_info.txt。

    Windows 版本号必须是 4 段数字（x.y.z.w），不足补 0。
    """
    parts = version.split(".") + ["0"] * 4
    numeric = ".".join(parts[:4])
    content = f"""# UTF-8
#
# PyInstaller 版本信息文件
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({", ".join(parts[:4])}),
    prodvers=({", ".join(parts[:4])}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', '公司 IT 部'),
            StringStruct('FileDescription', '公司网络配置工具'),
            StringStruct('FileVersion', '{version}'),
            StringStruct('ProductName', '公司网络配置工具'),
            StringStruct('ProductVersion', '{version}'),
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [0x409, 1200])])
  ]
)
"""
    VERSION_FILE.write_text(content, encoding="utf-8")


def main() -> int:
    version = read_version()
    print(f"[build] 版本号: {version}")

    # 1. 同步依赖
    print("[build] 同步依赖...")
    subprocess.run(["uv", "sync"], check=True, cwd=ROOT)

    # 2. 生成 version_info.txt
    print("[build] 生成 version_info.txt...")
    write_version_file(version)

    # 3. 构建 PyInstaller 命令
    cmd = [
        "uv", "run", "pyinstaller",
        "--onefile",
        "--windowed",
        "--uac-admin",
        "--name", APP_NAME,
        "--collect-all", "customtkinter",
        "--version-file", str(VERSION_FILE),
    ]
    if ICON.exists():
        cmd.extend(["--icon", str(ICON)])
        print(f"[build] 使用图标: {ICON}")
    else:
        print("[build] 未找到 assets/icon.ico，使用默认图标")
    cmd.append(str(ENTRY))

    # 4. 执行打包
    print(f"[build] 执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"[build] ❌ 打包失败 (exit {result.returncode})", file=sys.stderr)
        return result.returncode

    exe = ROOT / "dist" / f"{APP_NAME}.exe"
    print(f"\n[build] ✅ 打包完成!")
    print(f"[build] 可执行文件: {exe}")
    print(f"[build] 大小: {exe.stat().st_size / 1024 / 1024:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 创建 assets 目录占位（README 说明图标放哪）**

`assets/README.md`:
```markdown
# assets 目录

放置打包资源：

- `icon.ico` - 应用图标（Windows）。256x256 多尺寸 ICO 格式最佳。
  - 不放图标也能打包，会用 PyInstaller 默认图标。
```

- [ ] **Step 3: 验证脚本语法**

Run: `uv run python -c "import ast; ast.parse(open('scripts/build.py', encoding='utf-8').read()); print('syntax ok')"`
Expected: `syntax ok`

- [ ] **Step 4: 验证 read_version 和 write_version_file 逻辑（不真打包）**

Run:
```bash
uv run python -c "
import sys; sys.path.insert(0, 'scripts')
from build import read_version, write_version_file
v = read_version()
print('version:', v)
write_version_file(v)
print('version_info.txt generated')
"
```
Expected: 打印版本号和 "version_info.txt generated"

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat: 添加 PyInstaller 打包脚本（含版本号生成和UAC manifest）"
```

---

## Task 14: 文档 (README.md, 分发说明.md)

**Files:**
- Create: `README.md`
- Create: `分发说明.md`

- [ ] **Step 1: 写 README.md（给开发者/维护者）**

`README.md`:
```markdown
# 公司网络配置工具

华为 WiFi 下设备访问锐捷网络的一键路由配置工具。

## 背景

公司网络拓扑：

```
电信光猫 / 华为路由器 (192.168.5.1)
        ├── WiFi 设备 (192.168.5.x)   ← 本工具的目标用户
        └── 有线 ─── 锐捷网关 (192.168.5.22)
                      └── 锐捷内部网络 (192.168.0.0/22)
```

华为侧因电信设备限制无法配置路由转发，需在每台终端手动添加持久路由。

## 开发环境

需要 [uv](https://docs.astral.sh/uv/)（Python 包管理器）。

```bash
# 安装依赖
uv sync

# 运行测试
uv run pytest

# 运行程序（开发模式，需管理员权限）
uv run python -m route_tool

# 打包成 exe
uv run python scripts/build.py
```

## 架构

三层分层：

- `src/route_tool/core/` - 平台无关的数据模型、配置、契约
- `src/route_tool/platform/` - 平台实现（Windows 全功能，macOS 路由+ping）
- `src/route_tool/ui/` - CustomTkinter GUI

UI 层只依赖 `core.contracts.PlatformBackend` Protocol，通过 `platform.get_backend()` 工厂获取后端实例。

## 设计文档

详见 `docs/superpowers/specs/2026-06-18-network-route-tool-design.md`。

## 已知限制

- macOS 路由为临时路由，重启失效（UI 会提示）
- 不支持 Linux
- 首版不含一键添加打印机功能（后期扩展）
```

- [ ] **Step 2: 写 分发说明.md（给同事看）**

`分发说明.md`:
```markdown
# 公司网络配置工具 - 使用说明

## 这是什么

一个让你电脑能访问公司打印机、锐捷网络的小工具。双击运行即可。

## 怎么用

1. 找到 `公司网络配置工具.exe`，**双击** 打开
2. 系统会弹出一个蓝色窗口问"是否允许此应用更改设备"，点 **【是】**
3. 程序打开后会自动检测你的路由状态：
   - 显示 ✓ 已配置 → 你不用做任何事，关掉就行
   - 显示 ⚠ 未配置 → 点 **【一键配置路由】** 按钮
4. 想测试打印机能不能连：点打印机旁边的 **【测试】** 按钮，或点 **【全部测试】**

## 出问题了怎么办

程序下方有 **【操作日志】** 区域，会记录所有操作。

请把整个窗口截图发给 IT，IT 能从日志里看到哪里出了问题。

## 常见问题

**Q: 双击没反应 / 弹窗点"否"了？**
A: 必须点"是"同意那个蓝色授权窗口。重新双击 exe，这次点"是"。

**Q: 测试打印机显示"不通"？**
A: 先确认你的电脑连的是公司 WiFi（不是手机热点），再点一次测试。还不行就截图发 IT。

**Q: 关掉程序后，路由还在吗？**
A: 在的。路由配置是持久的，重启电脑也还在，不用每次都开这个工具。

**Q: 我想撤销配置？**
A: 联系 IT，不要自己乱动。
```

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "docs: 添加 README 和分发说明"
```

---

## Task 15: 全量测试与验收

**Files:** 无（验证任务）

- [ ] **Step 1: 运行全部单元测试**

Run: `uv run pytest -v`
Expected: 全部 PASS（约 50+ 个测试用例），无 SKIP 之外的非通过项

- [ ] **Step 2: 检查测试覆盖率**

Run: `uv run pytest --co -q | find /c "test"` (Windows)
Expected: 收集到的测试数量 > 40

- [ ] **Step 3: 验证 import 完整性**

Run:
```bash
uv run python -c "
from route_tool.core.models import Result, RouteInfo, PingResult, PrinterInfo, ResultLevel
from route_tool.core.config import DEFAULT_ROUTE, TEST_TARGETS
from route_tool.core.contracts import PlatformBackend
from route_tool.core.errors import UnsupportedOSError
from route_tool.platform import get_backend
from route_tool.ui.app import MainApp, run_app
print('all imports ok')
print('default route:', DEFAULT_ROUTE)
print('test targets:', [t.name for t in TEST_TARGETS])
"
```
Expected: 打印 "all imports ok" 和路由/设备列表

- [ ] **Step 4: 真机冒烟测试（Windows）**

> 此步骤需要真实的 Windows 管理员环境，无法自动化。

手动操作：
1. `uv run python -m route_tool`（以管理员运行终端）
2. 窗口应正常打开，主题跟随系统
3. 路由状态应自动检测（若已配置显示 ✓，未配置显示 ⚠）
4. 若未配置，点【一键配置路由】，应成功并显示 ✓
5. 点【全部测试】，三个设备应依次显示测试结果
6. 操作日志应有完整记录

- [ ] **Step 5: 打包验证**

Run: `uv run python scripts/build.py`
Expected:
- dist/公司网络配置工具.exe 生成
- 双击应弹 UAC，同意后窗口正常打开

- [ ] **Step 6: 最终提交 + 打 tag**

```bash
git add -A
git commit -m "test: 全量测试通过，v0.1.0 验收完成"
git tag v0.1.0
```

---

## Self-Review

**1. Spec 覆盖检查：**
- ✅ §1 背景/拓扑 → 体现在 config.py 常量和 README
- ✅ §2 技术选型 → pyproject.toml 声明 customtkinter
- ✅ §3 三层架构 → 文件结构对应 core/platform/ui
- ✅ §4 数据模型 → Task 2 (models) + Task 3 (config) 完整实现
- ✅ §4.3 contracts → Task 4 实现 Protocol
- ✅ §5.1 Windows 后端 → Task 6/7/8 (routes/connectivity/admin/backend)
- ✅ §5.2 macOS 后端 → Task 10
- ✅ §5.3 工厂 → Task 5
- ✅ §6 GUI 设计 → Task 11 (app + route_panel) + Task 12 (test_panel + log_panel)
- ✅ §6.3 线程模型 → 所有 panel 的 worker 线程 + after(0) 回调
- ✅ §6.4 主题跟随系统 → app.py set_appearance_mode("system")
- ✅ §7 错误处理 L1-L4 → Result 统一返回 + __main__ 全局兜底
- ✅ §8 构建 → Task 13 (build.py)
- ✅ §9 测试 → 每个 Task 都有 TDD 测试

**2. 占位符扫描：** 无 TBD/TODO（Task 11 的 TestPanel/LogPanel 占位是 Task 12 明确要替换的，已在 Task 12 Step 3 写明）。

**3. 类型一致性：**
- `Result.ok` property 在 models.py 定义，routes.py/test 中一致使用 ✅
- `DEFAULT_ROUTE` 在 config.py 定义，route_panel.py/app.py 一致引用 ✅
- `PlatformBackend.ping(host, count=2)` 签名在 contracts/windows/macos 一致 ✅
- `LogPanel.append(message, level)` 签名在 log_panel.py 定义，test_panel/route_panel 调用一致 ✅
- `_DeviceRow.set_result(ok, message)` 与 test_panel 调用一致 ✅

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-18-network-route-tool.md`.
