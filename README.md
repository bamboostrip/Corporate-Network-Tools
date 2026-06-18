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
