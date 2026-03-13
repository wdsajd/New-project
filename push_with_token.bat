@echo off
echo ========================================
echo GitHub仓库推送工具
echo ========================================
echo.
echo 仓库信息：
echo   用户名: wdsajd
echo   仓库名: New-project
echo   分支: master
echo.
echo 请按照以下步骤操作：
echo 1. 访问 https://github.com/settings/tokens
echo 2. 生成新的个人访问令牌（选择repo权限）
echo 3. 复制生成的令牌
echo.
set /p token=请输入你的GitHub个人访问令牌: 
echo.
echo 正在推送到GitHub...
echo.

git push https://%token%@github.com/wdsajd/New-project.git master

if %errorlevel% equ 0 (
    echo.
    echo ✅ 推送成功！
    echo 请访问：https://github.com/wdsajd/New-project
) else (
    echo.
    echo ❌ 推送失败，请检查：
    echo   - 令牌是否正确
    echo   - 令牌是否有repo权限
    echo   - 网络连接是否正常
)

echo.
pause