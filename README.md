# 公司网络配置工具

华为 WiFi 下设备访问锐捷网络及内网办公资源的一键配置工具。

## 功能特性

- **🚀 一键快捷部署**：一键并行/串行运行路由配置、打印机添加、网络文件夹配置的完整流程，帮助新员工快速融入办公环境。
- **🌐 自动路由配置**：自动在终端上为锐捷内部网络（`192.168.0.0/22`）配置网关（`192.168.5.22`）的静态持久路由，解决 WiFi 设备无法直接互通的问题。
- **🖨️ 打印机一键添加**：
  - 自动检测并创建 TCP/IP 打印机端口；
  - 内嵌官方打印驱动，采用**“总是覆盖安装”**的策略，完美解决由于旧驱动卸载不干净或损坏导致的 `0x8007000d` 报错；
  - 自动应对 Windows Print Spooler 服务偶发时序报错（`0x80070006`），延迟自动重试。
- **📂 网络文件夹配置（SMY 扫描目录）**：
  - 自动在桌面生成网络共享位置的快捷方式（`.lnk`），双击即可快速访问；
  - 后台提供静默自动备份服务，可在测试设备连接时自动备份 `.cc-switch` 配置文件到共享目录中。

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
.venv/Scripts/python.exe -m pytest

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
- macOS 不支持一键添加 Windows 打印机及网络共享快捷方式（仅限 Windows 平台）
- 不支持 Linux

