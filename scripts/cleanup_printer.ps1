# 清理 SHARP 打印机驱动和端口（测试前用，需管理员权限）
# 必须用 pwsh (PowerShell 7+) 运行：pwsh -File scripts/cleanup_printer.ps1
# 用 Windows PowerShell 5.1 (powershell) 运行会因 GBK 编码导致中文乱码。
#
# 关键：pnputil /delete-driver 在打印机驱动上会报 "device is using INF"，
# 必须先用 Remove-PrinterDriver 删打印子系统的驱动注册项，再删 inf 包。

$OutputEncoding = [System.Text.Encoding]::UTF8
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

# === 1. 删除残留打印机（按驱动名匹配，覆盖中文名）===
Get-Printer -ErrorAction SilentlyContinue |
    Where-Object { $_.DriverName -match 'SHARP|M905|UD3' } |
    ForEach-Object {
        Write-Host "🗑  删除打印机: $($_.Name)"
        Remove-Printer -Name $_.Name -ErrorAction SilentlyContinue
    }

# === 2. 删除残留端口 ===
Get-PrinterPort -ErrorAction SilentlyContinue |
    Where-Object { $_.PrinterHostAddress -match '192\.168\.0\.(210|241)' -or $_.Name -match '192\.168\.0\.(210|241)|S0_http' } |
    ForEach-Object {
        Write-Host "🗑  删除端口: $($_.Name)"
        Remove-PrinterPort -Name $_.Name -ErrorAction SilentlyContinue
    }

# === 3. 停 Print Spooler（释放驱动文件引用）===
Write-Host "⏸  停止 Print Spooler 服务..."
Stop-Service -Name Spooler -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# === 4. 删除打印子系统的驱动注册项（关键步骤，否则 pnputil 删不掉 inf）===
$drivers = @('SHARP MX-M905 PCL6', 'SHARP MX-M905 PS', 'SHARP UD3 PCL6')
foreach ($drv in $drivers) {
    Write-Host "🗑  删除打印机驱动注册: $drv"
    Remove-PrinterDriver -Name $drv -ErrorAction SilentlyContinue
}

# === 5. 启动 Print Spooler（pnputil 需要它运行）===
Write-Host "▶  启动 Print Spooler 服务..."
Start-Service -Name Spooler -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# === 6. 删除 DriverStore 里的 inf 包 ===
# oem 编号通过 pnputil /enum-drivers 实测确认：
#   oem46.inf = su0emenu.inf (MX-M905 PCL6 大打印机)
#   oem47.inf = su0hmenu.inf (MX-M905 PS 大打印机)
#   oem28.inf = sv0emenu.inf (UD3 PCL6 小打印机)
$sharpOems = @('oem46.inf', 'oem47.inf', 'oem28.inf')
foreach ($oem in $sharpOems) {
    Write-Host "🗑  删除驱动包: $oem"
    & pnputil /delete-driver $oem /uninstall /force 2>&1 | ForEach-Object {
        if ($_ -match 'successfully|成功') { Write-Host "    $_" }
        elseif ($_ -match 'failed|error|denied|失败|拒绝|using the specified') {
            Write-Host "    [错误] $_" -ForegroundColor Red
        }
    }
}

# === 7. 验证清理结果 ===
Write-Host ""
Write-Host "=== 清理后状态 ==="

$drv = Get-PrinterDriver -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'SHARP|M905|UD3' }
if ($drv) {
    Write-Host "⚠  仍有 SHARP 驱动残留:"
    $drv | Format-Table Name -AutoSize
} else {
    Write-Host "✅ SHARP 驱动已全部删除"
}

$prt = Get-Printer -ErrorAction SilentlyContinue | Where-Object { $_.DriverName -match 'SHARP|M905|UD3' }
if ($prt) {
    Write-Host "⚠  仍有打印机残留"
} else {
    Write-Host "✅ 打印机已全部删除"
}

$ports = Get-PrinterPort -ErrorAction SilentlyContinue | Where-Object { $_.PrinterHostAddress -match '192\.168\.0\.(210|241)' }
if ($ports) {
    Write-Host "⚠  仍有端口残留"
} else {
    Write-Host "✅ 端口已全部删除"
}
