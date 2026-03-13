# Windows自动更新禁用脚本
Write-Host "正在禁用Windows自动更新..." -ForegroundColor Green
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
    # 1. 停止相关服务
    Write-Host "1. 停止Windows更新服务..." -ForegroundColor Cyan
    Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue
    
    Write-Host "2. 停止Windows更新医疗服务..." -ForegroundColor Cyan
    Stop-Service -Name UsoSvc -Force -ErrorAction SilentlyContinue
    
    Write-Host "3. 停止Windows更新Orchestrator服务..." -ForegroundColor Cyan
    Stop-Service -Name WaaSMedicSvc -Force -ErrorAction SilentlyContinue
    
    # 2. 禁用服务启动
    Write-Host "4. 禁用Windows更新服务..." -ForegroundColor Cyan
    Set-Service -Name wuauserv -StartupType Disabled -ErrorAction SilentlyContinue
    
    Write-Host "5. 禁用Windows更新医疗服务..." -ForegroundColor Cyan
    Set-Service -Name UsoSvc -StartupType Disabled -ErrorAction SilentlyContinue
    
    Write-Host "6. 禁用Windows更新Orchestrator服务..." -ForegroundColor Cyan
    Set-Service -Name WaaSMedicSvc -StartupType Disabled -ErrorAction SilentlyContinue
    
    # 3. 设置注册表项
    Write-Host "7. 通过注册表禁用自动更新..." -ForegroundColor Cyan
    $regPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
    
    # 确保路径存在
    if (-not (Test-Path $regPath)) {
        New-Item -Path $regPath -Force | Out-Null
    }
    
    # 设置注册表值
    New-ItemProperty -Path $regPath -Name "NoAutoUpdate" -Value 1 -PropertyType DWORD -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "AUOptions" -Value 2 -PropertyType DWORD -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "ScheduledInstallDay" -Value 0 -PropertyType DWORD -Force | Out-Null
    New-ItemProperty -Path $regPath -Name "NoAutoRebootWithLoggedOnUsers" -Value 1 -PropertyType DWORD -Force | Out-Null
    
    # 4. 禁用Windows Update调度任务
    Write-Host "8. 禁用Windows Update调度任务..." -ForegroundColor Cyan
    Get-ScheduledTask -TaskPath "\Microsoft\Windows\WindowsUpdate\" | Disable-ScheduledTask -ErrorAction SilentlyContinue
    
    Write-Host ""
    Write-Host "✅ Windows自动更新已成功禁用！" -ForegroundColor Green
    Write-Host ""
    Write-Host "已执行的操作：" -ForegroundColor Yellow
    Write-Host "  • 停止并禁用了Windows更新服务" -ForegroundColor White
    Write-Host "  • 停止并禁用了Windows更新医疗服务" -ForegroundColor White
    Write-Host "  • 停止并禁用了Windows更新Orchestrator服务" -ForegroundColor White
    Write-Host "  • 通过注册表禁用了自动更新" -ForegroundColor White
    Write-Host "  • 禁用了Windows Update调度任务" -ForegroundColor White
    Write-Host ""
    Write-Host "注意：如果你以后需要重新启用Windows更新，可以运行'enable_windows_update.ps1'脚本。" -ForegroundColor Yellow
    
} catch {
    Write-Host "执行过程中出现错误: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")