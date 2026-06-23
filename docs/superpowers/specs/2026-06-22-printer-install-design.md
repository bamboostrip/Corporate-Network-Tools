# 设计：IPP/9100 打印机自动添加

**日期**: 2026-06-22
**状态**: 待批准
**依赖**: 已完成的路由配置工具（5.22 跨网段路由）

## 一、背景与调研结论

### 用户环境（已实测确认）

| 打印机 | IP | 型号（IPP 实测） | IPP(631) | Raw(9100) | 备注 |
|--------|-----|-----------------|----------|-----------|------|
| 大打印机 | 192.168.0.210 | SHARP MX-M905C（彩色复合机） | ✅ 开放 | ✅ 开放 | urf=V1.4，不完整 |
| 小打印机 | **192.168.0.241** | SHARP MX-C6082D | ✅ 开放 | ✅ 开放 | urf=V1.5，不完整 |

> **重要修正**：项目里 `config.py` 原写的小打印机 IP `192.168.0.248` 是错的，实际是 `192.168.0.241`。本次一并修复。

### 三个关键问题的答案

1. **IPP 能打几千页大 PDF 吗？** —— 协议本身不限，但 210/241 的 IPP 是"伪 driverless"（urf 仅有版本号无渲染命令），纯 IPP 渲染质量不可靠。**用 9100+PCL6 驱动打大文件最稳**。

2. **Windows/macOS 都能加吗？**
   - Windows：`Add-PrinterDriver/Port/Printer`（PrintManagement 模块）+ 内嵌 PCL6 驱动 = **完整支持**
   - macOS：`lpadmin -m everywhere` 尝试 IPP driverless，**无驱动兜底**（用户没提供 macOS 驱动）

3. **不用 IPP 能跨网段打印吗？** —— **能**。跨网段是路由层的事，与协议无关。路由工具配好 `192.168.0.0/22 → 192.168.5.22` 后，5 网段可访问 0 网段所有端口（9100/631/80）。**9100 跨网段比 IPP 更稳**（流式传输、不依赖 urf、大文件可靠）。

### 驱动文件分析（已确认）

| 驱动 | 路径 | 类型 | 架构 | 静默安装 |
|------|------|------|------|---------|
| 大打印机 | `夏普大.exe`（14MB） | 自解压安装器（MX_D54_PCL6_PS） | x64 | 支持 `/S` |
| 小打印机 | `夏普Win11/`（23MB，含 setup.exe + inf） | SHARP UD3 PCL6 通用驱动 | x86+x64 | setup.exe `/S`（需验证） |

## 二、目标与范围

### 做（In Scope）

- Windows：一键添加大/小打印机（9100+驱动，静默安装）
- macOS：一键添加（IPP driverless 尝试，明确提示限制）
- UI：在路由配置面板下方新增"打印机管理"面板，显示两台打印机及添加状态
- 前置检查：路由未配 / 9100 不通时禁止添加，提示先配路由
- 修复 248→241 的 IP bug

### 不做（Out of Scope，YAGNI）

- ❌ 不做删除打印机功能（用户可从系统设置手动删）
- ❌ 不做驱动版本更新/卸载（只装，不管后续升级）
- ❌ 不做 macOS 驱动集成（用户未提供）
- ❌ 不做打印队列管理/查看任务
- ❌ 不做打印首选项配置（纸张/双面交给系统打印对话框）

## 三、架构

遵循现有分层（UI → contracts → platform 实现），新增 `printer` 能力：

```
ui/widgets/printer_panel.py (新增)
    │  注入回调 on_add_printer / on_check_printer / on_log
    ▼
core/contracts.py  ← 新增 add_printer() / printer_exists()
    │
    ├── WindowsBackend
    │     └── platform/windows/printers.py (新增)
    │           ├── 驱动安装（静默执行内嵌 exe/inf）
    │           ├── 端口创建（Add-PrinterPort -LPR/9100）
    │           ├── 添加打印机（Add-Printer）
    │           └── 状态查询（Get-Printer）
    │
    └── MacBackend
          └── platform/macos/printers.py (新增)
                └── lpadmin -p xxx -E -v ipp://... -m everywhere

core/config.py  ← 新增 PRINTER_DEFS（两台打印机的元数据）
core/models.py  ← 新增 PrinterTarget / PrinterInstallResult
```

## 四、数据模型

### `core/models.py` 新增

```python
@dataclass
class PrinterTarget:
    """待添加的打印机定义（写死，非用户输入）。"""
    name: str           # 显示名："大打印机"
    description: str    # 备注："SHARP MX-M905C 彩色复合机"
    ip: str             # "192.168.0.210"
    port: int = 9100    # Windows 用 9100，macOS 用 631
    driver_label: str   # "大打印机驱动"（用于日志/资源定位）


@dataclass
class PrinterInstallResult:
    """添加打印机的结果。"""
    printer_name: str   # 目标打印机显示名
    ok: bool            # 是否成功（已存在也视为成功）
    already_exists: bool = False  # 之前已装过
    message: str = ""   # 用户可读消息
    raw_output: str = ""  # 诊断输出（IT 排查用）
    error_code: int = 0
```

### `core/config.py` 新增

```python
# === 打印机定义 ===
BIG_PRINTER = PrinterTarget(
    name="大打印机",
    description="SHARP MX-M905C 彩色复合机",
    ip="192.168.0.210",
    port=9100,
    driver_label="big",  # 对应打包资源 drivers/big/
)
SMALL_PRINTER = PrinterTarget(
    name="小打印机",
    description="SHARP MX-C6082D",
    ip="192.168.0.241",  # 修正：原 248 是错的
    port=9100,
    driver_label="small",
)
PRINTER_DEFS: list[PrinterTarget] = [BIG_PRINTER, SMALL_PRINTER]
```

## 五、契约扩展（`core/contracts.py`）

```python
def printer_exists(self, target: PrinterTarget) -> bool:
    """检查打印机是否已添加到系统。"""
    ...

def add_printer(self, target: PrinterTarget) -> PrinterInstallResult:
    """添加打印机到系统（静默安装驱动+端口+打印机）。
    已存在时直接返回成功（幂等）。
    """
    ...
```

## 六、Windows 实现（`platform/windows/printers.py`）

### 驱动资源打包

PyInstaller `--add-data` 把驱动打进 exe：
```
drivers/
  big/       # 夏普大.exe（MX_D54 PCL6+PS）
  small/     # 夏普Win11/ 目录（SHARP UD3 PCL6）
```
运行时从 `sys._MEIPASS`（PyInstaller 临时目录）或 `Path(__file__).parent/drivers/`（开发环境）定位。

### 添加流程（`add_printer`）

```
1. 幂等检查：Get-Printer -Name "大打印机"
   └─ 已存在 → 返回 PrinterInstallResult(ok=True, already_exists=True)

2. 连通性检查：TCP 连 192.168.0.210:9100
   └─ 不通 → 返回失败，提示"请先配置路由"

3. 安装驱动（若未装）：
   - 大打印机：静默执行 drivers/big/夏普大.exe /S（自解压安装驱动）
   - 小打印机：pnputil /add-driver drivers/small/PCL6/64bit/sv0emenu.inf /install
                + Add-PrinterDriver -Name "SHARP UD3 PCL6"
   注意：inf 驱动更可靠，优先用 inf；exe 安装器作为备选

4. 创建端口：
   Add-PrinterPort -Name "IP_192.168.0.210" -PrinterHostAddress "192.168.0.210"
   （Windows 标准 TCP/IP 端口，默认走 9100 Raw）

5. 添加打印机：
   Add-Printer -Name "大打印机" -DriverName "SHARP MX-M905C PCL6" -Port "IP_192.168.0.210"

6. 设置备注（Printer[pn]Comment 字段，可选）

7. 验证：Get-Printer -Name "大打印机" 确认存在
```

### subprocess 封装

复用现有 `subprocess_utils.no_window_kwargs()`（已实现）—— 所有 PowerShell/pnputil 调用都隐藏控制台窗口，避免黑窗。

### 驱动名映射

实际驱动名（从 inf 提取）：
- 大打印机：MX_D54 驱动 → 需要从 exe 解压后看 inf 确定（exe 自解压会在临时目录释放文件）
- 小打印机：`SHARP UD3 PCL6`（已从 sv0emenu.inf 确认）

**打印机队列显示名**（用户决策）：用中文"大打印机"/"小打印机"（写进 `Add-Printer -Name`，最贴近用户习惯，符合"免得用户分不出来"的初衷；备注字段放型号描述）。

> **实现时风险点**：大打印机 `夏普大.exe` 是自解压安装器，静默安装的具体行为（装完后驱动名是什么）需要实测。实现时会先在测试机跑一次 `夏普大.exe /S`，用 `Get-PrinterDriver` 看装出来的驱动名，再写死映射。若 exe 行为不可控，fallback 到从 exe 解压出 inf 再用 `pnputil`。

## 七、macOS 实现（`platform/macos/printers.py`）

```python
def add_printer(target):
    # 幂等检查：lpstat -p "大打印机"
    # 添加：lpadmin -p "大打印机" -E -v ipp://192.168.0.210:631/ipp/print -m everywhere -L "公司" -D "SHARP MX-M905C"
    # 验证：lpstat -p "大打印机"
```

`-m everywhere` 让 CUPS 用 driverless（IPP Everywhere）。由于 210/241 的 urf 不完整，渲染可能异常，UI 会明确提示用户。

## 八、UI 设计（`ui/widgets/printer_panel.py`）

在 TestPanel 下方、LogPanel 上方新增"🖨 打印机管理"面板：

```
🖨 打印机管理
─────────────────────────
🖨 大打印机   SHARP MX-M905C 彩色复合机   192.168.0.210   状态: 未添加  [添加]
🖨 小打印机   SHARP MX-C6082D            192.168.0.241   状态: 未添加  [添加]
─────────────────────────
```

- 每行：图标+名称+备注+IP+状态+[添加]按钮（复用 TestPanel 的 `_DeviceRow` 模式）
- 状态：未添加 / ✓已添加 / 添加中... / ✗失败
- **前置检查**：路由面板检测 5.22 不可达时，添加按钮禁用（跨网段路由未配，9100 一定不通）
- 添加操作在后台线程跑（驱动安装耗时长，不阻塞 UI），结果用 `after()` 回主线程

### app.py 改动

新增 PrinterPanel 注入：
```python
self._printer_panel = PrinterPanel(
    self,
    on_add_printer=self._backend.add_printer,
    on_check_printer=self._backend.printer_exists,
    on_log=self._log,
)
self._printer_panel.grid(row=2, ...)  # LogPanel 移到 row=3
```

窗口高度相应增加（minsize 调整）。

## 九、错误处理

| 场景 | 处理 |
|------|------|
| 路由未配（5.22 不通） | 按钮禁用，日志提示"请先配置路由" |
| 9100 端口不通 | 返回失败，日志写"打印机网络不可达" |
| 驱动安装失败 | 返回失败，raw_output 含 pnputil/PowerShell 错误 |
| 端口已存在 | 幂等，继续下一步 |
| 打印机已存在 | 返回成功，already_exists=True，日志提示"已添加过" |
| 非管理员 | 友好提示"需要管理员权限"（UAC manifest 已保证提权） |
| macOS lpadmin 失败 | 提示"IPP 添加失败，请尝试从夏普官网下载 macOS 驱动手动添加" |

## 十、测试策略（TDD）

| 测试文件 | 覆盖 |
|---------|------|
| `tests/core/test_models.py`（追加） | `PrinterTarget` / `PrinterInstallResult` 字段 |
| `tests/core/test_config.py`（追加） | `PRINTER_DEFS` 含两台打印机，IP 正确（241） |
| `tests/core/test_contracts.py`（追加） | Protocol 含 `add_printer` / `printer_exists` |
| `tests/platform/windows/test_printers.py`（新增） | 命令构造、幂等检查、幂等返回、错误处理（mock subprocess） |
| `tests/platform/macos/test_printers.py`（新增） | lpadmin 命令构造、幂等（mock subprocess） |
| `tests/platform/windows/test_backend.py`（追加） | WindowsBackend.add_printer 委托 |
| `tests/platform/macos/test_backend.py`（追加） | MacBackend.add_printer 委托 |
| `tests/ui/test_printer_panel.py`（新增） | PrinterPanel 静态检查 + 按钮启用规则 |
| `tests/ui/test_threading_safety.py`（追加） | PrinterPanel 有 add_async 方法 |

**测试不真实安装驱动**（会污染开发机），全部 mock subprocess，只验证命令构造和结果处理逻辑。

## 十一、打包改动（`scripts/build.py`）

```python
cmd = [
    sys.executable, "-m", "PyInstaller",
    ...
    "--add-data", "src/route_tool/drivers;route_tool/drivers",  # 新增
    ...
]
```

驱动文件放 `src/route_tool/drivers/{big,small}/`，运行时通过 `resource_path()` 工具函数定位（兼容开发环境和 PyInstaller 打包）。

## 十二、风险与缓解

| 风险 | 缓解 |
|------|------|
| 大打印机 exe 静默安装行为未知 | 实现时先实测 `夏普大.exe /S`，记录驱动名；不可控则改用解压+pnputil |
| PyInstaller 打包后驱动路径 | 用 `sys._MEIPASS` 检测 + `resource_path()` 抽象 |
| 驱动签名问题（Win11 强制驱动签名） | 夏普驱动有 WHQL 签名（inf 含 .cat 文件），应无问题 |
| 跨网段 9100 被防火墙拦 | 前置检查时实测 TCP 连通性，失败给清晰提示 |
| macOS driverless 渲染异常 | UI 明确提示限制，不承诺 macOS 100% 可用 |

## 十三、验收标准

- [ ] Windows：点击"添加大打印机"后，系统设置里出现"大打印机"，能正常打印测试页
- [ ] Windows：重复点击"添加大打印机"返回成功（幂等，提示"已添加"）
- [ ] Windows：路由未配时按钮禁用
- [ ] macOS：`lpadmin` 命令构造正确（driverless 尝试）
- [ ] UI：两台打印机状态正确显示
- [ ] 248→241 的 IP bug 修复，config 测试更新
- [ ] 全量测试通过（现有 98 + 新增）
- [ ] exe 打包成功，驱动文件包含在内
