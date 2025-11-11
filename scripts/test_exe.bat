@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
set "EXE_DIR=%PROJECT_ROOT%\dist\ui_inference_dist"
set "TEST_IMAGE_DIR=%PROJECT_ROOT%\testimage"
set "CHECKPOINT=%PROJECT_ROOT%\checkpoints\seg\ui\sfnet_res101_ui_latest.pth"
set "OUTPUT_DIR=%EXE_DIR%\test_output"

echo ========================================
echo UI推理工具 - 测试运行
echo ========================================
echo.
echo 脚本目录: %SCRIPT_DIR%
echo 项目根目录: %PROJECT_ROOT%
echo 可执行文件目录: %EXE_DIR%
echo 测试图片目录: %TEST_IMAGE_DIR%
echo Checkpoint路径: %CHECKPOINT%
echo.

cd /d "%EXE_DIR%"
if not exist "ui_inference.exe" (
    echo ERROR: ui_inference.exe not found in %EXE_DIR%
    pause
    exit /b 1
)

echo 查找测试图片...
set "TEST_IMAGE="
REM 首先检查是否有test1.png
if exist "%TEST_IMAGE_DIR%\test1.png" (
    set "TEST_IMAGE=%TEST_IMAGE_DIR%\test1.png"
    echo [OK] Found test1.png
) else (
    REM 查找testimage目录下的第一个png文件
    cd /d "%TEST_IMAGE_DIR%"
    if exist "*.png" (
        for %%f in (*.png) do (
            if not defined TEST_IMAGE (
                set "TEST_IMAGE=%TEST_IMAGE_DIR%\%%f"
                echo [OK] Found PNG image: %%f
            )
        )
    )
)

if not defined TEST_IMAGE (
    echo ERROR: No PNG image found in %TEST_IMAGE_DIR%
    echo Please place a PNG image in the testimage directory
    echo Or specify image path as first argument: test_exe.bat "path\to\image.png"
    pause
    exit /b 1
)

echo 测试图片路径: %TEST_IMAGE%
echo.

echo 检查Checkpoint文件...
if not exist "%CHECKPOINT%" (
    echo WARNING: Checkpoint not found: %CHECKPOINT%
    echo Will use untrained model (for testing only)
) else (
    echo [OK] Checkpoint found: %CHECKPOINT%
)
echo.

REM 如果用户提供了第一个参数作为图片路径，使用用户指定的路径
if not "%~1"=="" (
    set "TEST_IMAGE=%~1"
    echo Using user-specified image: %TEST_IMAGE%
    echo.
)

echo 运行推理...
echo Command: ui_inference.exe --image "%TEST_IMAGE%" --config configs\seg\sfnet_res101_ui.conf --checkpoint "%CHECKPOINT%" --output "%OUTPUT_DIR%" --gpu -1
echo.
cd /d "%EXE_DIR%"
ui_inference.exe --image "%TEST_IMAGE%" --config configs\seg\sfnet_res101_ui.conf --checkpoint "%CHECKPOINT%" --output "%OUTPUT_DIR%" --gpu -1
set EXIT_CODE=!ERRORLEVEL!

echo.
echo ========================================
echo Exit code: !EXIT_CODE!
if !EXIT_CODE! EQU 0 (
    echo SUCCESS: Execution completed successfully
    echo Output files in: %OUTPUT_DIR%
    if exist "%OUTPUT_DIR%\output.html" (
        echo [OK] HTML file generated: %OUTPUT_DIR%\output.html
    )
) else (
    echo ERROR: Execution failed with code !EXIT_CODE!
)
echo ========================================
pause
exit /b !EXIT_CODE!
