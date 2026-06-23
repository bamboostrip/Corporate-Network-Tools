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

- 驱动文件不提交 git（体积大，且有版权），已被 `.gitignore` 忽略
- 打包前确保上述文件就位（运行 `scripts/build.py` 前手动复制）
- macOS 不需要驱动（用 IPP driverless）
- 大打印机驱动名（`DRIVER_NAME_MAP["big"]`）需在实测 `夏普大.exe /S` 安装后确认填入
  `src/route_tool/platform/windows/printers.py`
