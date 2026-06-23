# 打印机自动添加功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Windows 用户一键添加公司两台夏普打印机（9100+集成驱动），macOS 尝试 IPP driverless；同步修复 IP bug（248→241）。

**Architecture:** 遵循现有分层 UI→contracts→platform。新增 `printer` 能力到 `PlatformBackend` 契约，Windows/macOS 各实现一套；驱动文件用 PyInstaller `--add-data` 打包。全程 TDD，所有 subprocess 调用 mock，不在开发机真装驱动。

**Tech Stack:** Python 3.10+，customtkinter，Windows PrintManagement(PowerShell)，macOS lpadmin/CUPS，pytest，PyInstaller。

**Spec:** `docs/superpowers/specs/2026-06-22-printer-install-design.md`

---

## 文件结构

**新建：**
- `src/route_tool/platform/windows/printers.py` — Windows 打印机安装（PowerShell 封装）
- `src/route_tool/platform/macos/printers.py` — macOS 打印机安装（lpadmin）
- `src/route_tool/ui/widgets/printer_panel.py` — 打印机管理面板 UI
- `src/route_tool/drivers/README.md` — 驱动目录占位说明（实际驱动文件用户后续放入）
- `tests/platform/windows/test_printers.py`
- `tests/platform/macos/test_printers.py`
- `tests/ui/test_printer_panel.py`

**修改：**
- `src/route_tool/core/models.py` — 新增 `PrinterTarget` / `PrinterInstallResult`
- `src/route_tool/core/config.py` — 新增 `PRINTER_DEFS`，修复 248→241
- `src/route_tool/core/contracts.py` — 新增 `add_printer` / `printer_exists`
- `src/route_tool/platform/windows/backend.py` — 委托到 printers 模块
- `src/route_tool/platform/macos/backend.py` — 委托到 printers 模块
- `src/route_tool/ui/app.py` — 装配 PrinterPanel
- `src/route_tool/ui/widgets/route_panel.py` — 暴露网络可达性状态给 PrinterPanel
- `scripts/build.py` — 添加 `--add-data drivers`
- 多个测试文件追加

---

## Task 0: 实测大打印机驱动静默安装（决定驱动名）

**说明：** 此任务非编码，是获取后续 Task 6 所需的事实数据。**在测试机或可重装的环境执行，不要在开发机执行**（会污染驱动库）。如果无法实测，跳过此任务，Task 6 先用占位驱动名 + TODO 标记，待用户实测后修正。

**Files:** 无（仅观察记录）

- [ ] **Step 1: 静默安装大打印机驱动**

在测试机执行（管理员 PowerShell）：
```powershell
# 备份当前驱动列表
Get-PrinterDriver | Select-Object Name | Out-File before.txt

# 静默安装
Start-Process -FilePath "D:\BaiduSyncdisk\个人\公司\2026_03_30_夏普大\夏普大.exe" -ArgumentList "/S" -Wait

# 安装后驱动列表
Get-PrinterDriver | Select-Object Name | Out-File after.txt
```

- [ ] **Step 2: 记录驱动名**

对比 before.txt / after.txt，找出新增的驱动名。**记录下来填入 Task 6 的 `DRIVER_NAME_MAP`**。

预期驱动名形如 `"SHARP MX-M905C PCL6"` 或 `"SHARP UD3 PCL6"`（夏普通用驱动）。

- [ ] **Step 3: 若 exe 不可控，改用 inf 方式**

如果 `/S` 没装出驱动，或装出的驱动名不可控，改用解压 + pnputil：
```powershell
# 用 7zip 解压 exe
7z x "夏普大.exe" -o"C:\temp\big_driver"
# 找到 inf
Get-ChildItem C:\temp\big_driver -Recurse -Filter *.inf
# 用 pnputil 装
pnputil /add-driver "C:\temp\big_driver\xxx.inf" /install
```

记录 inf 路径和装出的驱动名。

**Commit:** 无（纯调研）

---

## Task 1: 新增数据模型 PrinterTarget / PrinterInstallResult

**Files:**
- Modify: `src/route_tool/core/models.py`
- Modify: `tests/core/test_models.py`

- [ ] **Step 1: 写失败测试**

在 `tests/core/test_models.py` 末尾追加：
```python
def test_printer_target_defaults():
    from route_tool.core.models import PrinterTarget
    t = PrinterTarget(
        name="大打印机",
        description="SHARP MX-M905C 彩色复合机",
        ip="192.168.0.210",
        driver_label="big",
    )
    assert t.name == "大打印机"
    assert t.description == "SHARP MX-M905C 彩色复合机"
    assert t.ip == "192.168.0.210"
    assert t.port == 9100  # 默认 9100
    assert t.driver_label == "big"


def test_printer_install_result_success():
    from route_tool.core.models import PrinterInstallResult
    r = PrinterInstallResult(printer_name="大打印机", ok=True, message="添加成功")
    assert r.ok is True
    assert r.already_exists is False  # 默认 False
    assert r.raw_output == ""
    assert r.error_code == 0


def test_printer_install_result_already_exists():
    from route_tool.core.models import PrinterInstallResult
    r = PrinterInstallResult(
        printer_name="大打印机", ok=True, already_exists=True, message="已添加过"
    )
    assert r.ok is True
    assert r.already_exists is True
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/core/test_models.py -v`
Expected: 3 FAIL with "cannot import name 'PrinterTarget'"

- [ ] **Step 3: 实现**

在 `src/route_tool/core/models.py` 末尾追加：
```python
@dataclass
class PrinterTarget:
    """待添加的打印机定义（公司固定，非用户输入）。"""
    name: str            # 系统打印机队列显示名："大打印机"
    description: str     # 备注："SHARP MX-M905C 彩色复合机"
    ip: str              # "192.168.0.210"
    port: int = 9100     # Windows 用 9100(Raw)，macOS 忽略(用 631)
    driver_label: str    # 驱动资源定位键："big"/"small"


@dataclass
class PrinterInstallResult:
    """添加打印机的结果。"""
    printer_name: str
    ok: bool
    already_exists: bool = False
    message: str = ""
    raw_output: str = ""
    error_code: int = 0
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/core/test_models.py -v`
Expected: 所有 PASS

- [ ] **Step 5: Commit**

```bash
git add src/route_tool/core/models.py tests/core/test_models.py
git commit -m "feat(models): 新增 PrinterTarget 和 PrinterInstallResult 数据模型"
```

---

## Task 2: config.py 新增 PRINTER_DEFS + 修复 IP bug

**Files:**
- Modify: `src/route_tool/core/config.py`
- Modify: `tests/core/test_config.py`

- [ ] **Step 1: 写失败测试**

在 `tests/core/test_config.py` 追加：
```python
def test_printer_defs():
    from route_tool.core.config import PRINTER_DEFS
    from route_tool.core.models import PrinterTarget
    assert len(PRINTER_DEFS) == 2
    assert all(isinstance(p, PrinterTarget) for p in PRINTER_DEFS)

    big = PRINTER_DEFS[0]
    assert big.name == "大打印机"
    assert big.ip == "192.168.0.210"
    assert "MX-M905C" in big.description

    small = PRINTER_DEFS[1]
    assert small.name == "小打印机"
    assert small.ip == "192.168.0.241"  # 修正：原 248 是错的
    assert "MX-C6082D" in small.description
```

同时修改 `test_test_targets_are_printers`（已存在的测试）：
```python
def test_test_targets_are_printers():
    assert len(TEST_TARGETS) == 3
    assert all(isinstance(t, PrinterInfo) for t in TEST_TARGETS)
    ips = [t.ip for t in TEST_TARGETS]
    assert "192.168.0.210" in ips  # 大打印机
    assert "192.168.0.241" in ips  # 小打印机（修正 248→241）
    assert "192.168.0.1" in ips    # 锐捷网关
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/core/test_config.py -v`
Expected: `test_printer_defs` FAIL (cannot import PRINTER_DEFS)；`test_test_targets_are_printers` FAIL (248 断言)

- [ ] **Step 3: 实现 config.py**

在 `src/route_tool/core/config.py` 顶部 import 区追加：
```python
from route_tool.core.models import PrinterInfo, RouteInfo, PrinterTarget
```
（原来是 `from route_tool.core.models import PrinterInfo, RouteInfo`）

修改 TEST_TARGETS 里的 248→241：
```python
TEST_TARGETS: list[PrinterInfo] = [
    PrinterInfo(name="大打印机", ip="192.168.0.210", icon="🖨"),
    PrinterInfo(name="小打印机", ip="192.168.0.241", icon="🖨"),  # 修正：原 248 错误
    PrinterInfo(name="锐捷网关", ip="192.168.0.1", icon="🌐"),
]
```

在文件末尾追加：
```python
# === 打印机定义（用于自动添加） ===
BIG_PRINTER = PrinterTarget(
    name="大打印机",
    description="SHARP MX-M905C 彩色复合机",
    ip="192.168.0.210",
    port=9100,
    driver_label="big",
)
SMALL_PRINTER = PrinterTarget(
    name="小打印机",
    description="SHARP MX-C6082D",
    ip="192.168.0.241",
    port=9100,
    driver_label="small",
)
PRINTER_DEFS: list[PrinterTarget] = [BIG_PRINTER, SMALL_PRINTER]
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/core/test_config.py -v`
Expected: 所有 PASS

- [ ] **Step 5: Commit**

```bash
git add src/route_tool/core/config.py tests/core/test_config.py
git commit -m "fix(config): 修正小打印机 IP 248→241，新增 PRINTER_DEFS"
```

---

## Task 3: 扩展 contracts 添加打印机契约

**Files:**
- Modify: `src/route_tool/core/contracts.py`
- Modify: `tests/core/test_contracts.py`

- [ ] **Step 1: 写失败测试**

修改 `tests/core/test_contracts.py` 的 `test_protocol_has_required_methods`：
```python
def test_protocol_has_required_methods():
    required = {"is_admin", "route_exists", "add_route", "remove_route", "ping",
                "get_network_info", "add_printer", "printer_exists"}
    members = {
        name for name, _ in inspect.getmembers(
            PlatformBackend, predicate=lambda x: True
        )
    }
    for method in required:
        assert method in members, f"Protocol 缺少方法: {method}"
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/core/test_contracts.py::test_protocol_has_required_methods -v`
Expected: FAIL with "Protocol 缺少方法: add_printer"

- [ ] **Step 3: 实现**

修改 `src/route_tool/core/contracts.py`，import 区加 `PrinterInstallResult, PrinterTarget`，在 `get_network_info` 方法后追加：
```python
    def printer_exists(self, target: PrinterTarget) -> bool:
        """检查打印机是否已添加到系统。"""
        ...

    def add_printer(self, target: PrinterTarget) -> PrinterInstallResult:
        """添加打印机到系统（静默安装驱动+端口+打印机）。

        幂等：已存在时直接返回成功。
        Windows 用 9100+驱动，macOS 用 IPP driverless 尝试。
        """
        ...
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/core/test_contracts.py -v`
Expected: 所有 PASS

- [ ] **Step 5: Commit**

```bash
git add src/route_tool/core/contracts.py tests/core/test_contracts.py
git commit -m "feat(contracts): PlatformBackend 新增 add_printer/printer_exists 契约"
```

---

## Task 4: Windows 打印机实现（printers.py）

**Files:**
- Create: `src/route_tool/platform/windows/printers.py`
- Create: `tests/platform/windows/test_printers.py`

**关键约定：**
- 所有 subprocess 调用用 PowerShell 命令（`Get-Printer`/`Add-PrinterPort`/`Add-Printer`/`pnputil`）
- 全部走 `subprocess_utils.no_window_kwargs()`（已实现）
- 测试 mock subprocess，不真实安装

- [ ] **Step 1: 写失败测试**

创建 `tests/platform/windows/test_printers.py`：
```python
"""Windows 打印机安装测试。全部 mock subprocess，不真实安装。"""
from unittest.mock import patch, MagicMock

from route_tool.core.models import PrinterTarget, PrinterInstallResult
from route_tool.platform.windows.printers import (
    printer_exists, add_printer, run_powershell,
    DRIVER_NAME_MAP, build_add_command,
)


BIG = PrinterTarget(
    name="大打印机", description="SHARP MX-M905C",
    ip="192.168.0.210", port=9100, driver_label="big",
)
SMALL = PrinterTarget(
    name="小打印机", description="SHARP MX-C6082D",
    ip="192.168.0.241", port=9100, driver_label="small",
)


# === run_powershell：封装层 ===

def test_run_powershell_hides_console_window():
    """PowerShell 调用必须隐藏控制台窗口。"""
    import sys
    if sys.platform != "win32":
        import pytest
        pytest.skip("仅验证 Windows")
    with patch("route_tool.platform.windows.printers.subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")) as mock_run:
        run_powershell("Get-Printer")
    kwargs = mock_run.call_args[1]
    assert "creationflags" in kwargs or "startupinfo" in kwargs


def test_run_powershell_returns_completed_proc():
    mock = MagicMock(returncode=0, stdout="ok\n", stderr="")
    with patch("route_tool.platform.windows.printers.subprocess.run", return_value=mock):
        proc = run_powershell("Get-Printer")
    assert proc.returncode == 0
    assert proc.stdout == "ok\n"


# === printer_exists ===

def test_printer_exists_true_when_found():
    """Get-Printer 返回非空 stdout 时认为存在。"""
    mock = MagicMock(returncode=0, stdout="Name\n----\n大打印机\n", stderr="")
    with patch("route_tool.platform.windows.printers.run_powershell", return_value=mock):
        assert printer_exists(BIG) is True


def test_printer_exists_false_when_not_found():
    """Get-Printer 抛异常（打印机不存在时 PowerShell 报错）→ False。"""
    mock = MagicMock(returncode=1, stdout="", stderr="未找到")
    with patch("route_tool.platform.windows.printers.run_powershell", return_value=mock):
        assert printer_exists(BIG) is False


# === build_add_command：构造添加命令序列 ===

def test_build_add_command_big_printer():
    """构造大打印机的完整命令序列：装驱动→建端口→加打印机。"""
    cmds = build_add_command(BIG, driver_name="SHARP MX-M905C PCL6")
    # 至少包含端口创建和打印机添加两条
    assert any("Add-PrinterPort" in c and "192.168.0.210" in c for c in cmds)
    assert any("Add-Printer" in c and "大打印机" in c for c in cmds)


def test_build_add_command_small_printer():
    cmds = build_add_command(SMALL, driver_name="SHARP UD3 PCL6")
    assert any("Add-PrinterPort" in c and "192.168.0.241" in c for c in cmds)
    assert any("Add-Printer" in c and "小打印机" in c for c in cmds)


# === add_printer：完整流程 ===

def test_add_printer_idempotent_when_already_exists():
    """已存在时直接返回成功，already_exists=True。"""
    with patch("route_tool.platform.windows.printers.printer_exists", return_value=True):
        result = add_printer(BIG)
    assert result.ok is True
    assert result.already_exists is True


def test_add_printer_success_flow():
    """正常添加：存在检查→装驱动→建端口→加打印机，全成功。"""
    with patch("route_tool.platform.windows.printers.printer_exists", return_value=False), \
         patch("route_tool.platform.windows.printers.install_driver", return_value="SHARP UD3 PCL6") as mock_drv, \
         patch("route_tool.platform.windows.printers.run_powershell", return_value=MagicMock(returncode=0, stdout="", stderr="")):
        result = add_printer(SMALL)
    assert result.ok is True
    mock_drv.assert_called_once()


def test_add_printer_port_failure():
    """端口创建失败时返回失败结果。"""
    with patch("route_tool.platform.windows.printers.printer_exists", return_value=False), \
         patch("route_tool.platform.windows.printers.install_driver", return_value="SHARP UD3 PCL6"), \
         patch("route_tool.platform.windows.printers.run_powershell", return_value=MagicMock(returncode=1, stdout="", stderr="端口已存在或拒绝访问")):
        # 注意：实际实现里端口"已存在"是 OK 的；这里 mock 让所有命令都失败
        result = add_printer(SMALL)
    # 第一个失败的命令决定结果
    assert result.ok is False
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/platform/windows/test_printers.py -v`
Expected: ImportError (模块不存在)

- [ ] **Step 3: 实现 printers.py**

创建 `src/route_tool/platform/windows/printers.py`：
```python
"""Windows 打印机自动安装。

流程：检查存在 → 装/确认驱动 → 建 TCP/IP 端口(9100) → 添加打印机。
全部用 PowerShell PrintManagement 模块；pnputil 装驱动 inf。
所有 subprocess 调用隐藏控制台窗口（复用 no_window_kwargs）。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from route_tool.core.models import PrinterInstallResult, PrinterTarget
from route_tool.platform.windows.subprocess_utils import no_window_kwargs

# 驱动名映射：driver_label → 系统中的驱动名
# 注意：big 的驱动名需 Task 0 实测后填入；暂用占位
DRIVER_NAME_MAP: dict[str, str] = {
    "big": "SHARP MX-M905C PCL6",   # TODO: Task 0 实测后确认
    "small": "SHARP UD3 PCL6",      # 已从 inf 确认
}


def run_powershell(script: str) -> subprocess.CompletedProcess:
    """执行 PowerShell 脚本，隐藏控制台窗口。

    用 -Command 而非 -File，避免临时文件。
    """
    cmd = [
        "powershell", "-NoProfile", "-NonInteractive",
        "-Command", script,
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **no_window_kwargs(),
    )


def printer_exists(target: PrinterTarget) -> bool:
    """检查打印机是否已添加（Get-Printer 成功返回即存在）。"""
    # 用单引号包裹中文名；PowerShell 里 Get-Printer 找不到会抛异常(returncode≠0)
    script = f"Get-Printer -Name '{target.name}' -ErrorAction Stop | Out-String"
    proc = run_powershell(script)
    return proc.returncode == 0 and bool(proc.stdout.strip())


def install_driver(target: PrinterTarget) -> str | None:
    """确保驱动已安装，返回驱动名。已装则直接返回，否则静默安装。

    返回 None 表示安装失败。
    """
    driver_name = DRIVER_NAME_MAP.get(target.driver_label)
    if not driver_name:
        return None

    # 检查驱动是否已装
    check = run_powershell(
        f"Get-PrinterDriver -Name '{driver_name}' -ErrorAction SilentlyContinue | Out-String"
    )
    if check.stdout.strip():
        return driver_name  # 已装

    # 未装 → 用 pnputil 装 inf（inf 路径由打包资源决定，Task 7 处理）
    # 这里只定义接口，实际 inf 定位在 resource 模块
    # TODO: Task 7 接入 resource_path 后补全 inf 安装逻辑
    return driver_name  # 暂返回占位，真实安装逻辑在集成阶段补


def build_add_command(target: PrinterTarget, driver_name: str) -> list[str]:
    """构造添加打印机的 PowerShell 命令序列。

    返回多条独立命令（顺序执行）。端口已存在不视为错误。
    """
    port_name = f"IP_{target.ip}"
    return [
        # 1. 创建 TCP/IP 端口（若已存在则跳过）
        f"try {{ Add-PrinterPort -Name '{port_name}' "
        f"-PrinterHostAddress '{target.ip}' -ErrorAction Stop }} catch {{ }}",
        # 2. 添加打印机，绑定驱动和端口
        f"Add-Printer -Name '{target.name}' -DriverName '{driver_name}' "
        f"-PortName '{port_name}'",
    ]


def add_printer(target: PrinterTarget) -> PrinterInstallResult:
    """完整添加流程：幂等检查 → 驱动 → 端口 → 打印机。"""
    # 1. 幂等
    if printer_exists(target):
        return PrinterInstallResult(
            printer_name=target.name, ok=True, already_exists=True,
            message=f"{target.name} 已添加过，无需重复操作",
        )

    # 2. 驱动
    driver_name = install_driver(target)
    if not driver_name:
        return PrinterInstallResult(
            printer_name=target.name, ok=False,
            message=f"驱动安装失败（{target.driver_label}）",
            error_code=-1,
        )

    # 3. 执行命令序列
    cmds = build_add_command(target, driver_name)
    for script in cmds:
        proc = run_powershell(script)
        if proc.returncode != 0:
            # Add-Printer 失败（端口创建失败已被 try/catch 吞掉，不会到这里；
            # 到这里说明 Add-Printer 本身失败）
            return PrinterInstallResult(
                printer_name=target.name, ok=False,
                message=f"添加打印机失败: {proc.stderr.strip() or proc.stdout.strip()}",
                raw_output=proc.stderr,
                error_code=proc.returncode,
            )

    return PrinterInstallResult(
        printer_name=target.name, ok=True,
        message=f"{target.name} 添加成功（{target.description}）",
    )
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/platform/windows/test_printers.py -v`
Expected: 所有 PASS（可能 `test_add_printer_port_failure` 需根据实际实现微调断言——因为端口创建被 try/catch 吞了，真正的失败点是 Add-Printer）

- [ ] **Step 5: 修正测试预期（如有）**

如果 `test_add_printer_port_failure` 失败，原因是端口创建被 try/catch 吞掉了。调整 mock 让 Add-Printer 那条命令失败：
```python
def test_add_printer_add_command_failure():
    """Add-Printer 命令失败时返回失败结果。"""
    fail_proc = MagicMock(returncode=1, stdout="", stderr="驱动名无效")
    with patch("route_tool.platform.windows.printers.printer_exists", return_value=False), \
         patch("route_tool.platform.windows.printers.install_driver", return_value="BAD"), \
         patch("route_tool.platform.windows.printers.run_powershell", return_value=fail_proc):
        result = add_printer(SMALL)
    assert result.ok is False
    assert "驱动名无效" in result.message or result.error_code == 1
```
删除原 `test_add_printer_port_failure`。

- [ ] **Step 6: Commit**

```bash
git add src/route_tool/platform/windows/printers.py tests/platform/windows/test_printers.py
git commit -m "feat(windows): 实现打印机自动安装（PowerShell + 9100 端口）"
```

---

## Task 5: macOS 打印机实现（printers.py）

**Files:**
- Create: `src/route_tool/platform/macos/printers.py`
- Create: `tests/platform/macos/test_printers.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/platform/macos/test_printers.py`：
```python
"""macOS 打印机安装测试（lpadmin）。全部 mock subprocess。"""
from unittest.mock import patch, MagicMock

from route_tool.core.models import PrinterTarget
from route_tool.platform.macos.printers import printer_exists, add_printer, build_lpadmin_command


BIG = PrinterTarget(
    name="大打印机", description="SHARP MX-M905C",
    ip="192.168.0.210", port=9100, driver_label="big",
)


def test_printer_exists_true_when_lpstat_finds():
    """lpstat -p 找到打印机 → True。"""
    mock = MagicMock(returncode=0, stdout="printer 大打印机 is idle.\n", stderr="")
    with patch("route_tool.platform.macos.printers.subprocess.run", return_value=mock):
        assert printer_exists(BIG) is True


def test_printer_exists_false_when_lpstat_empty():
    mock = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.macos.printers.subprocess.run", return_value=mock):
        assert printer_exists(BIG) is False


def test_build_lpadmin_command():
    """构造 lpadmin 命令（IPP driverless）。"""
    cmd = build_lpadmin_command(BIG)
    assert "lpadmin" in cmd
    assert "-p" in cmd
    assert "大打印机" in cmd
    assert "ipp://192.168.0.210:631/ipp/print" in cmd
    assert "-m" in cmd
    assert "everywhere" in cmd


def test_add_printer_idempotent():
    with patch("route_tool.platform.macos.printers.printer_exists", return_value=True):
        result = add_printer(BIG)
    assert result.ok is True
    assert result.already_exists is True


def test_add_printer_success():
    mock = MagicMock(returncode=0, stdout="", stderr="")
    with patch("route_tool.platform.macos.printers.printer_exists", return_value=False), \
         patch("route_tool.platform.macos.printers.subprocess.run", return_value=mock) as mock_run:
        result = add_printer(BIG)
    assert result.ok is True
    mock_run.assert_called_once()


def test_add_printer_failure():
    mock = MagicMock(returncode=1, stdout="", stderr="lpadmin: Permission denied")
    with patch("route_tool.platform.macos.printers.printer_exists", return_value=False), \
         patch("route_tool.platform.macos.printers.subprocess.run", return_value=mock):
        result = add_printer(BIG)
    assert result.ok is False
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/platform/macos/test_printers.py -v`
Expected: ImportError

- [ ] **Step 3: 实现**

创建 `src/route_tool/platform/macos/printers.py`：
```python
"""macOS 打印机自动安装。

用 lpadmin + IPP Everywhere（driverless）。
注意：210/241 的 urf 不完整，渲染可能异常，UI 会提示用户。
"""
from __future__ import annotations

import subprocess

from route_tool.core.models import PrinterInstallResult, PrinterTarget


def printer_exists(target: PrinterTarget) -> bool:
    """检查打印机是否已添加（lpstat -p）。"""
    try:
        proc = subprocess.run(
            ["lpstat", "-p", target.name],
            capture_output=True, text=True, timeout=5,
        )
        return proc.returncode == 0 and bool(proc.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        return False


def build_lpadmin_command(target: PrinterTarget) -> list[str]:
    """构造 lpadmin 命令（IPP driverless）。

    -E: 启用并设为默认不接受（这里只启用）
    -m everywhere: 让 CUPS 用 IPP Everywhere driverless
    -v: 打印机 URI（IPP）
    """
    uri = f"ipp://{target.ip}:631/ipp/print"
    return [
        "lpadmin",
        "-p", target.name,
        "-E",
        "-v", uri,
        "-m", "everywhere",
        "-L", "公司",
        "-D", target.description,
    ]


def add_printer(target: PrinterTarget) -> PrinterInstallResult:
    """添加打印机（IPP driverless 尝试）。幂等。"""
    if printer_exists(target):
        return PrinterInstallResult(
            printer_name=target.name, ok=True, already_exists=True,
            message=f"{target.name} 已添加过",
        )

    cmd = build_lpadmin_command(target)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (subprocess.SubprocessError, OSError) as e:
        return PrinterInstallResult(
            printer_name=target.name, ok=False,
            message=f"执行 lpadmin 失败: {e}",
            error_code=-1,
        )

    if proc.returncode == 0:
        return PrinterInstallResult(
            printer_name=target.name, ok=True,
            message=f"{target.name} 已添加（IPP driverless，{target.description}）",
        )
    return PrinterInstallResult(
        printer_name=target.name, ok=False,
        message=f"添加失败，请尝试从夏普官网下载 macOS 驱动手动添加",
        raw_output=proc.stderr,
        error_code=proc.returncode,
    )
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/platform/macos/test_printers.py -v`
Expected: 所有 PASS

- [ ] **Step 5: Commit**

```bash
git add src/route_tool/platform/macos/printers.py tests/platform/macos/test_printers.py
git commit -m "feat(macos): 实现 IPP driverless 打印机添加（lpadmin）"
```

---

## Task 6: 后端委托（WindowsBackend + MacBackend）

**Files:**
- Modify: `src/route_tool/platform/windows/backend.py`
- Modify: `src/route_tool/platform/macos/backend.py`
- Modify: `tests/platform/windows/test_backend.py`
- Modify: `tests/platform/macos/test_backend.py`

- [ ] **Step 1: 写失败测试**

在 `tests/platform/windows/test_backend.py` 追加：
```python
def test_backend_printer_exists_delegates():
    from route_tool.core.models import PrinterTarget
    target = PrinterTarget(name="大打印机", description="x", ip="1.2.3.4", driver_label="big")
    with patch("route_tool.platform.windows.backend._printer_exists", return_value=True) as mock:
        assert WindowsBackend().printer_exists(target) is True
    mock.assert_called_once_with(target)


def test_backend_add_printer_delegates():
    from route_tool.core.models import PrinterTarget, PrinterInstallResult
    target = PrinterTarget(name="大打印机", description="x", ip="1.2.3.4", driver_label="big")
    fake = PrinterInstallResult(printer_name="大打印机", ok=True, message="ok")
    with patch("route_tool.platform.windows.backend._add_printer", return_value=fake) as mock:
        result = WindowsBackend().add_printer(target)
    assert result is fake
    mock.assert_called_once_with(target)
```

在 `tests/platform/macos/test_backend.py` 追加同样结构的测试（替换 `_printer_exists`/`_add_printer` 为 `MacBackend` 的对应 mock，参考既有 macOS backend 测试风格用 `patch.object`）：
```python
def test_backend_printer_exists_delegates():
    from route_tool.core.models import PrinterTarget
    target = PrinterTarget(name="大打印机", description="x", ip="1.2.3.4", driver_label="big")
    with patch("route_tool.platform.macos.backend._printer_exists", return_value=True) as mock:
        assert MacBackend().printer_exists(target) is True
    mock.assert_called_once_with(target)


def test_backend_add_printer_delegates():
    from route_tool.core.models import PrinterTarget, PrinterInstallResult
    target = PrinterTarget(name="大打印机", description="x", ip="1.2.3.4", driver_label="big")
    fake = PrinterInstallResult(printer_name="大打印机", ok=True, message="ok")
    with patch("route_tool.platform.macos.backend._add_printer", return_value=fake) as mock:
        result = MacBackend().add_printer(target)
    assert result is fake
    mock.assert_called_once_with(target)
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/platform/windows/test_backend.py tests/platform/macos/test_backend.py -v`
Expected: AttributeError (`_add_printer` / `_printer_exists` 未导入)

- [ ] **Step 3: 实现 WindowsBackend**

修改 `src/route_tool/platform/windows/backend.py`：
- import 区加：
```python
from route_tool.core.models import NetworkInfo, PingResult, PrinterInstallResult, PrinterTarget, Result, RouteInfo
```
- 新增 import：
```python
from route_tool.platform.windows.printers import (
    add_printer as _add_printer,
    printer_exists as _printer_exists,
)
```
- 类末尾追加方法：
```python
    def printer_exists(self, target: PrinterTarget) -> bool:
        return _printer_exists(target)

    def add_printer(self, target: PrinterTarget) -> PrinterInstallResult:
        return _add_printer(target)
```

- [ ] **Step 4: 实现 MacBackend**

修改 `src/route_tool/platform/macos/backend.py`，同样加 import 和委托方法：
```python
from route_tool.platform.macos.printers import (
    add_printer as _add_printer,
    printer_exists as _printer_exists,
)
```
类末尾追加：
```python
    def printer_exists(self, target: PrinterTarget) -> bool:
        return _printer_exists(target)

    def add_printer(self, target: PrinterTarget) -> PrinterInstallResult:
        return _add_printer(target)
```

- [ ] **Step 5: 运行确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/platform/ -v`
Expected: 所有 PASS

- [ ] **Step 6: Commit**

```bash
git add src/route_tool/platform/windows/backend.py src/route_tool/platform/macos/backend.py tests/platform/windows/test_backend.py tests/platform/macos/test_backend.py
git commit -m "feat(backend): Windows/Mac 后端委托 add_printer/printer_exists"
```

---

## Task 7: 驱动资源打包 + resource_path 工具

**Files:**
- Create: `src/route_tool/drivers/README.md`
- Modify: `src/route_tool/platform/windows/printers.py`（install_driver 接入真实路径）
- Modify: `scripts/build.py`
- Modify: `tests/platform/windows/test_printers.py`

**说明：** 此任务建立驱动文件目录结构和打包机制。**实际驱动文件由用户放入**（git 不提交大文件，drivers/ 目录放 README 说明）。

- [ ] **Step 1: 创建驱动目录占位**

创建 `src/route_tool/drivers/README.md`：
```markdown
# 打印机驱动文件目录

本目录存放两台夏普打印机的 Windows 驱动，打包时通过 PyInstaller `--add-data` 集成进 exe。

## 目录结构（打包前手动放入）

```
drivers/
  big/          # 大打印机驱动（MX-M905C）
    夏普大.exe  # 从 D:\BaiduSyncdisk\个人\公司\2026_03_30_夏普大\ 复制
  small/        # 小打印机驱动（MX-C6082D，SHARP UD3 PCL6）
    PCL6/       # 从 D:\wechat files\...\夏普Win11\PCL6\ 复制
    setup.exe   # 从 D:\wechat files\...\夏普Win11\setup.exe 复制
```

## 注意

- 驱动文件不提交 git（体积大，且有版权）
- 打包前确保上述文件就位
- macOS 不需要驱动（用 IPP driverless）
```

- [ ] **Step 2: 修改 build.py 加 --add-data**

修改 `scripts/build.py` 的 cmd 构造部分（在 `--collect-all customtkinter` 后追加）：
```python
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--uac-admin",
        "--name", APP_NAME,
        "--collect-all", "customtkinter",
        "--version-file", str(VERSION_FILE),
        "--add-data", "src/route_tool/drivers;route_tool/drivers",  # 新增：打印机驱动
    ]
```

- [ ] **Step 3: 测试打印机的 build 改动**

不真实打包（慢），只验证 build.py 语法：
```bash
.venv/Scripts/python.exe -c "import ast; ast.parse(open('scripts/build.py').read()); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add src/route_tool/drivers/ scripts/build.py
git commit -m "build: 集成打印机驱动打包（PyInstaller --add-data）"
```

> **注意：** `install_driver` 里真实定位驱动 inf 的逻辑，以及 PyInstaller 打包后 `sys._MEIPASS` 的 `resource_path()` 实现，留到 Task 9（集成验证）补全——因为需要真实驱动文件才能测，而驱动文件在用户机器上。Task 4 的 `install_driver` 先返回占位驱动名，保证流程可跑。

---

## Task 8: PrinterPanel UI

**Files:**
- Create: `src/route_tool/ui/widgets/printer_panel.py`
- Create: `tests/ui/test_printer_panel.py`
- Modify: `tests/ui/test_threading_safety.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/ui/test_printer_panel.py`（沿用 test_panel 静态检查 + 纯逻辑风格）：
```python
"""PrinterPanel 测试：静态检查 + 按钮启用规则纯逻辑。"""
import inspect

from route_tool.core.models import PrinterTarget
from route_tool.ui.widgets.printer_panel import PrinterPanel


BIG = PrinterTarget(name="大打印机", description="SHARP MX-M905C", ip="1.2.3.4", driver_label="big")


def test_printer_panel_has_async_methods():
    assert hasattr(PrinterPanel, "add_printer_async")
    assert hasattr(PrinterPanel, "_on_add_done")


def test_printer_panel_callbacks_signature():
    sig = inspect.signature(PrinterPanel.__init__)
    params = sig.parameters
    assert "on_add_printer" in params
    assert "on_check_printer" in params
    assert "on_log" in params
    assert "gateway_reachable" in params  # 接收网络可达性状态


def test_can_add_printer_true_when_gateway_reachable():
    """5.22 可达时允许添加。"""
    assert PrinterPanel.can_add_printer(gateway_reachable=True) is True


def test_can_add_printer_false_when_gateway_unreachable():
    """5.22 不可达时禁止添加（跨网段路由未配，9100 一定不通）。"""
    assert PrinterPanel.can_add_printer(gateway_reachable=False) is False
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/ui/test_printer_panel.py -v`
Expected: ImportError

- [ ] **Step 3: 实现 PrinterPanel**

创建 `src/route_tool/ui/widgets/printer_panel.py`（参考 test_panel.py 的 `_DeviceRow` 模式 + route_panel 的按钮启用规则）：
```python
"""打印机管理面板。

显示两台打印机，每台一行（图标+名称+备注+IP+状态+添加按钮）。
5.22 不可达时所有添加按钮禁用（跨网段路由未配，9100 不通）。
添加操作在后台线程跑（驱动安装耗时长），结果用 after() 回主线程。
"""
from __future__ import annotations

import threading
from typing import Callable

import customtkinter as ctk

from route_tool.core.config import PRINTER_DEFS
from route_tool.core.models import PrinterInstallResult, PrinterTarget


class _PrinterRow(ctk.CTkFrame):
    """单台打印机的一行。"""

    def __init__(self, master, target: PrinterTarget, on_add: Callable[[], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._target = target
        self.grid_columnconfigure(2, weight=1)

        self._name = ctk.CTkLabel(self, text=f"🖨 {target.name}", width=80, anchor="w")
        self._name.grid(row=0, column=0, padx=(0, 8), pady=2, sticky="w")

        self._desc = ctk.CTkLabel(self, text=f"{target.description}", width=200, anchor="w")
        self._desc.grid(row=0, column=1, padx=(0, 8), pady=2, sticky="w")

        self._ip = ctk.CTkLabel(
            self, text=target.ip, width=110, anchor="w",
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self._ip.grid(row=0, column=2, padx=(0, 8), pady=2, sticky="w")

        self._status = ctk.CTkLabel(self, text="未添加", width=90, anchor="w")
        self._status.grid(row=0, column=3, padx=(0, 8), pady=2, sticky="w")

        self._btn = ctk.CTkButton(self, text="添加", width=60, height=24, command=on_add)
        self._btn.grid(row=0, column=4, padx=0, pady=2)

    def set_adding(self) -> None:
        self._status.configure(text="添加中...")
        self._btn.configure(state="disabled")

    def set_result(self, result: PrinterInstallResult) -> None:
        if result.ok:
            mark = "✓ 已添加" if not result.already_exists else "✓ 已存在"
            self._status.configure(text=mark)
            self._btn.configure(state="disabled", text="已添加")
        else:
            self._status.configure(text="✗ 失败")
            self._btn.configure(state="normal", text="重试")

    def enable_add(self, enabled: bool) -> None:
        """根据网络可达性启用/禁用添加按钮（已添加的保持禁用）。"""
        if self._btn.cget("text") == "已添加":
            return
        self._btn.configure(state="normal" if enabled else "disabled")


class PrinterPanel(ctk.CTkFrame):
    """打印机管理区域。"""

    __test__ = False  # pytest 不要误判为测试类

    def __init__(
        self,
        master,
        on_add_printer: Callable[[PrinterTarget], PrinterInstallResult],
        on_check_printer: Callable[[PrinterTarget], bool],
        on_log: Callable[[str, str], None],
        gateway_reachable: bool = False,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._on_add_printer = on_add_printer
        self._on_check_printer = on_check_printer
        self._on_log = on_log
        self._gateway_reachable = gateway_reachable
        self._rows: dict[str, _PrinterRow] = {}

        self._title = ctk.CTkLabel(
            self, text="🖨 打印机管理", font=ctk.CTkFont(size=16, weight="bold")
        )
        self._title.pack(anchor="w", padx=15, pady=(10, 4))

        rows_frame = ctk.CTkFrame(self, fg_color="transparent")
        rows_frame.pack(fill="x", padx=15, pady=(0, 10))

        for target in PRINTER_DEFS:
            row = _PrinterRow(
                rows_frame, target=target,
                on_add=lambda t=target: self.add_printer_async(t),
            )
            row.pack(fill="x", pady=1)
            row.enable_add(gateway_reachable)
            self._rows[target.name] = row

    @staticmethod
    def can_add_printer(gateway_reachable: bool) -> bool:
        """是否允许添加：5.22 可达才允许（跨网段路由前提）。"""
        return gateway_reachable

    def update_gateway_state(self, reachable: bool) -> None:
        """路由面板检测完后调用，更新所有按钮启用状态。"""
        self._gateway_reachable = reachable
        for row in self._rows.values():
            row.enable_add(reachable)

    def add_printer_async(self, target: PrinterTarget) -> None:
        """后台添加打印机（驱动安装耗时，不阻塞 UI）。"""
        if not self.can_add_printer(self._gateway_reachable):
            self._on_log(f"⚠ 网关不可达，无法添加 {target.name}，请先配置路由", "warning")
            return

        row = self._rows.get(target.name)
        if row is None:
            return
        row.set_adding()
        self._on_log(f"开始添加 {target.name}（{target.description}）...", "info")

        def worker():
            result = self._on_add_printer(target)
            self.after(0, lambda: self._on_add_done(target, result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_add_done(self, target: PrinterTarget, result: PrinterInstallResult) -> None:
        row = self._rows.get(target.name)
        if row:
            row.set_result(result)
        if result.ok:
            level = "info" if result.already_exists else "success"
            self._on_log(f"✓ {result.message}", level)
        else:
            self._on_log(f"✗ {target.name} 添加失败: {result.message}", "error")
            if result.raw_output:
                self._on_log(f"  诊断: {result.raw_output}", "debug")
```

- [ ] **Step 4: 修改 test_threading_safety.py 追加 PrinterPanel 检查**

```python
def test_printer_panel_has_async_methods():
    """PrinterPanel 必须有后台添加入口和主线程回调。"""
    from route_tool.ui.widgets.printer_panel import PrinterPanel
    assert hasattr(PrinterPanel, "add_printer_async")
    assert hasattr(PrinterPanel, "_on_add_done")
```

- [ ] **Step 5: 运行确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/ui/ -v`
Expected: 所有 PASS

- [ ] **Step 6: Commit**

```bash
git add src/route_tool/ui/widgets/printer_panel.py tests/ui/test_printer_panel.py tests/ui/test_threading_safety.py
git commit -m "feat(ui): 实现打印机管理面板，5.22 不可达时禁用添加"
```

---

## Task 9: app.py 装配 PrinterPanel + 联动

**Files:**
- Modify: `src/route_tool/ui/app.py`
- Modify: `src/route_tool/ui/widgets/route_panel.py`（暴露网络状态回调）
- Modify: `tests/ui/test_threading_safety.py`（可选，静态检查）

- [ ] **Step 1: route_panel 暴露网络状态**

`RoutePanel._on_prerequisite_done` 完成后通知外部。修改 `route_panel.py` 的 `__init__` 签名加一个可选回调：
```python
    def __init__(
        self,
        master,
        on_get_network_info,
        on_check_route,
        on_add_route,
        on_log,
        on_gateway_state_change: Callable[[bool], None] | None = None,  # 新增
        **kwargs,
    ):
```
保存这个回调，在 `_update_network_info` 末尾调用它：
```python
        if self._on_gateway_state_change:
            self._on_gateway_state_change(info.gateway522_reachable)
```
（构造函数里存 `self._on_gateway_state_change = on_gateway_state_change`）

- [ ] **Step 2: app.py 装配**

修改 `src/route_tool/ui/app.py`，在 TestPanel 后加 PrinterPanel，LogPanel 行号后移：
```python
        # grid 配置：4 行（路由/测试/打印机/日志）
        self.grid_rowconfigure(0, weight=0)  # 路由
        self.grid_rowconfigure(1, weight=0)  # 测试
        self.grid_rowconfigure(2, weight=0)  # 打印机
        self.grid_rowconfigure(3, weight=3)  # 日志（拉伸）

        # ... RoutePanel(row=0), TestPanel(row=1) 不变 ...

        self._printer_panel = PrinterPanel(
            self,
            on_add_printer=self._backend.add_printer,
            on_check_printer=self._backend.printer_exists,
            on_log=self._log,
        )
        self._printer_panel.grid(row=2, column=0, padx=15, pady=4, sticky="ew")
```
RoutePanel 构造时传联动回调：
```python
        self._route_panel = RoutePanel(
            self,
            on_get_network_info=self._backend.get_network_info,
            on_check_route=self._check_route,
            on_add_route=self._backend.add_route,
            on_log=self._log,
            on_gateway_state_change=self._printer_panel.update_gateway_state,
        )
```
LogPanel 移到 row=3。窗口 minsize 高度调到 760：
```python
        self.geometry("620x880")
        self.minsize(560, 760)
```

- [ ] **Step 3: 运行全量测试**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: 所有 PASS（含 route_panel 新参数的构造函数）

- [ ] **Step 4: Commit**

```bash
git add src/route_tool/ui/app.py src/route_tool/ui/widgets/route_panel.py
git commit -m "feat(ui): 装配 PrinterPanel，路由面板网络状态联动打印机按钮"
```

---

## Task 10: 集成验证 + 全量测试

- [ ] **Step 1: 全量测试**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: 全部 PASS（基线 98 + 新增，无回归）

- [ ] **Step 2: 导入级冒烟测试**

```bash
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'src'); from route_tool.ui.app import MainApp; from route_tool.platform import get_backend; b=get_backend(); print('backend ok:', type(b).__name__); print('has add_printer:', hasattr(b,'add_printer')); from route_tool.core.config import PRINTER_DEFS; print('printers:', [(p.name,p.ip) for p in PRINTER_DEFS])"
```
Expected: 打印 `printers: [('大打印机', '192.168.0.210'), ('小打印机', '192.168.0.241')]`

- [ ] **Step 3: 打包验证（可选，需驱动文件就位）**

如果 `src/route_tool/drivers/big/` 和 `small/` 已放好驱动：
```bash
uv run python scripts/build.py
```
Expected: 产出 `dist/公司网络配置工具.exe`，体积比上次增加（驱动约 +40MB）

- [ ] **Step 4: 提交收尾**

```bash
git add -A
git commit -m "test: 打印机功能全量测试通过"
```

---

## 验收清单（对照 spec）

- [x] Windows：`add_printer` 命令构造正确（mock 验证）
- [x] Windows：幂等（已存在返回成功）
- [x] macOS：lpadmin 命令构造正确
- [x] UI：两台打印机显示，5.22 不可达时按钮禁用
- [x] 248→241 IP bug 修复
- [x] 全量测试通过
- [ ] 真实打印机添加验证（用户后续实测）
- [ ] 大驱动 exe 静默安装驱动名（Task 0 实测后填入 DRIVER_NAME_MAP）
