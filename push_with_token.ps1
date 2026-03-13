# GitHub仓库推送脚本 - PowerShell版本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GitHub仓库推送工具" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "仓库信息：" -ForegroundColor Green
Write-Host "  用户名: wdsajd" -ForegroundColor White
Write-Host "  仓库名: New-project" -ForegroundColor White
Write-Host "  分支: master" -ForegroundColor White
Write-Host ""
Write-Host "请按照以下步骤操作：" -ForegroundColor Green
Write-Host "1. 访问 https://github.com/settings/tokens" -ForegroundColor White
Write-Host "2. 生成新的个人访问令牌（选择repo权限）" -ForegroundColor White
Write-Host "3. 复制生成的令牌" -ForegroundColor White
Write-Host ""

# 安全地获取令牌
$token = Read-Host "请输入你的GitHub个人访问令牌" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($token)
$plainToken = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)

Write-Host ""
Write-Host "正在推送到GitHub..." -ForegroundColor Cyan
Write-Host ""

# 构建带令牌的URL
$pushUrl = "https://${plainToken}@github.com/wdsajd/New-project.git"

# 执行推送
git push $pushUrl master

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ 推送成功！" -ForegroundColor Green
    Write-Host "请访问：https://github.com/wdsajd/New-project" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "❌ 推送失败，请检查：" -ForegroundColor Red
    Write-Host "  - 令牌是否正确" -ForegroundColor White
    Write-Host "  - 令牌是否有repo权限" -ForegroundColor White
    Write-Host "  - 网络连接是否正常" -ForegroundColor White
}

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")