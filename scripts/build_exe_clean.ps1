param(
  [string]$SpecPath = ".\scripts\pyinstaller_ui_inference.spec"
)

Write-Host "Installing PyInstaller if missing..."
.\torchcv_env\Scripts\python.exe -m pip install pyinstaller -q

Write-Host "Stopping any running ui_inference processes..."
Get-Process | Where-Object {$_.ProcessName -like "*ui_inference*"} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "Cleaning output directory..."
$distPath = ".\dist\ui_inference_dist"
if (Test-Path $distPath) {
    Remove-Item -Path $distPath -Recurse -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

Write-Host "Building executable via spec: $SpecPath"
.\torchcv_env\Scripts\pyinstaller.exe $SpecPath --clean -y --noconfirm

Write-Host "Build done. Checking output..."

# 单文件模式会在 dist 目录生成 ui_inference.exe
# 需要复制到 dist\ui_inference_dist 目录
$exeSource = ".\dist\ui_inference.exe"
$exeDest = ".\dist\ui_inference_dist\ui_inference.exe"

if (Test-Path $exeSource) {
    # 确保目标目录存在
    if (-not (Test-Path ".\dist\ui_inference_dist")) {
        New-Item -ItemType Directory -Path ".\dist\ui_inference_dist" -Force | Out-Null
    }
    # 复制可执行文件
    Copy-Item -Path $exeSource -Destination $exeDest -Force
    Write-Host "Executable created successfully at: $exeDest"
    Write-Host "File size: $((Get-Item $exeDest).Length / 1MB) MB"
} else {
    Write-Host "WARNING: Executable not found at $exeSource"
    if (Test-Path $exeDest) {
        Write-Host "Found executable at $exeDest instead"
    }
}

