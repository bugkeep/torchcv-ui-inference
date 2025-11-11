@echo off
chcp 65001 >nul
echo ========================================
echo GitHub上传脚本
echo ========================================
echo.

REM 检查Git是否安装
git --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Git未安装，请先安装Git: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo [OK] Git已安装
echo.

REM 获取项目根目录
cd /d "%~dp0.."
set "PROJECT_ROOT=%CD%"

echo 项目目录: %PROJECT_ROOT%
echo.

REM 检查是否已经是Git仓库
if exist ".git" (
    echo [信息] 已经是Git仓库
) else (
    echo [步骤1] 初始化Git仓库...
    git init
    if errorlevel 1 (
        echo [错误] Git初始化失败
        pause
        exit /b 1
    )
    echo [OK] Git仓库初始化成功
)

echo.
echo [步骤2] 检查文件状态...
git status --short

echo.
echo [步骤3] 添加文件到Git...
git add .

echo.
echo [步骤4] 检查要提交的文件...
git status --short

echo.
set /p COMMIT_MSG="请输入提交信息 (直接回车使用默认信息): "
if "%COMMIT_MSG%"=="" set "COMMIT_MSG=Initial commit: UI推理工具"

git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
    echo [错误] 提交失败
    pause
    exit /b 1
)
echo [OK] 提交成功

echo.
echo [步骤5] 检查远程仓库...
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo [信息] 未配置远程仓库
    echo.
    echo 请提供GitHub仓库地址:
    echo 示例: https://github.com/用户名/仓库名.git
    echo.
    set /p REPO_URL="GitHub仓库地址: "
    if "%REPO_URL%"=="" (
        echo [错误] 未提供仓库地址
        echo.
        echo 请先创建GitHub仓库，然后运行:
        echo   git remote add origin ^<仓库地址^>
        echo   git push -u origin main
        pause
        exit /b 1
    )
    git remote add origin "%REPO_URL%"
    if errorlevel 1 (
        echo [错误] 添加远程仓库失败
        pause
        exit /b 1
    )
    echo [OK] 远程仓库添加成功
) else (
    git remote get-url origin
    echo [信息] 已配置远程仓库
)

echo.
echo [步骤6] 推送代码到GitHub...
echo 这可能需要一些时间，请耐心等待...
echo.

REM 尝试推送到main分支，如果失败则尝试master分支
git push -u origin main 2>nul
if errorlevel 1 (
    git push -u origin master 2>nul
    if errorlevel 1 (
        echo [错误] 推送失败
        echo.
        echo 可能的原因:
        echo 1. 认证失败 - 请检查GitHub用户名和密码/token
        echo 2. 网络问题 - 请检查网络连接
        echo 3. 权限问题 - 请检查仓库权限
        echo.
        echo 解决方法:
        echo 1. 使用Personal Access Token作为密码
        echo 2. 配置SSH密钥
        echo 3. 手动推送: git push -u origin main
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo 上传成功！
echo ========================================
echo.
echo 您的代码已上传到GitHub
echo.
pause

