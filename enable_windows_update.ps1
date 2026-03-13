# Windows自动更新启用脚本
Write-Host "正在重新启用Windows自动更新..." -ForegroundColor Green
Write-Host ""

# 检查是否以管理员身份运行
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "请以管理员身份运行此脚本！" -ForegroundColor Red
    Write-Host "右键点击脚本文件，选择'以管理员身份运行'" -ForegroundColor Yellow
    pause
    exit
}

try {
    # 1. 启用服务启动
    Write-Host "1. 启用Windows更新服务..." -ForegroundColor Cyan
    Set-Service -Name wuauserv -StartupType Manual -ErrorAction SilentlyContinue
    
    Write-Host "2. 启用Windows更新医疗服务..." -ForegroundColor Cyan
    Set-Service -Name UsoSvc -StartupType Manual -ErrorAction SilentlyContinue
    
    Write-Host "3. 启用Windows更新Orchestrator服务..." -ForegroundColor Cyan
    Set-Service -Name WaaSMedicSvc -StartupType Manual -ErrorAction SilentlyContinue
    
    # 2. 删除注册表项
    Write-Host "4. 删除自动更新注册表限制..." -ForegroundColor Cyan
    $regPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
    
    if (Test-Path $regPath) {
        Remove-ItemProperty -Path $regPath -Name "NoAutoUpdate" -ErrorAction SilentlyContinue
        Remove-ItemProperty -Path $regPath -Name "AUOptions" -ErrorAction SilentlyContinue
        Remove-ItemProperty -Path $regPath -Name "ScheduledInstallDay" -ErrorAction SilentlyContinue
        Remove-ItemProperty -Path $regPath -Name "NoAutoRebootWithLoggedOnUsers" -ErrorAction SilentlyContinue
    }
    
    # 3. 启用Windows Update调度任务
    Write-Host "5. 启用Windows Update调度任务..." -ForegroundColor Cyan
    Get-ScheduledTask -TaskPath "\Microsoft\Windows\WindowsUpdate\" | Enable-ScheduledTask -ErrorAction SilentlyContinue
    
    # 4. 启动服务
    Write-Host "6. 启动Windows更新服务..." -ForegroundColor Cyan
    Start-Service -Name wuauserv -ErrorAction SilentlyContinue
    
    Write-Host ""
    Write-Host "✅ Windows自动更新已重新启用！" -ForegroundColor Green
    Write-Host ""
    Write-Host "已执行的操作：" -ForegroundColor Yellow
    Write-Host "  • 启用了Windows更新服务" -ForegroundColor White
    Write-Host "  • 启用了Windows更新医疗服务" -ForegroundColor White
    Write-Host "  • 启用了Windows更新Orchestrator服务" -ForegroundColor White
    Write-Host "  • 删除了注册表限制" -ForegroundColor White
    Write-Host "  • 启用了Windows Update调度任务" -ForegroundColor White
    Write-Host ""
    Write-Host "建议：重启计算机以确保所有更改生效。" -ForegroundColor Yellow
    
} catch {
    Write-Host "执行过程中出现错误: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")