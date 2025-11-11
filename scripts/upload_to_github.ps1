# GitHub上传脚本
# 使用方法: .\scripts\upload_to_github.ps1 [GitHub仓库地址]

param(
    [string]$RepoUrl = ""
)

Write-Host "========================================" -ForegroundColor Green
Write-Host "GitHub上传脚本" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 检查Git是否安装
try {
    $gitVersion = git --version
    Write-Host "[OK] Git已安装: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "[错误] Git未安装，请先安装Git: https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

# 获取项目根目录
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host "项目目录: $projectRoot" -ForegroundColor Cyan
Write-Host ""

# 检查是否已经是Git仓库
if (Test-Path ".git") {
    Write-Host "[信息] 已经是Git仓库" -ForegroundColor Yellow
} else {
    Write-Host "[步骤1] 初始化Git仓库..." -ForegroundColor Cyan
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] Git初始化失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Git仓库初始化成功" -ForegroundColor Green
}

Write-Host ""
Write-Host "[步骤2] 检查文件状态..." -ForegroundColor Cyan
git status --short

Write-Host ""
Write-Host "[步骤3] 添加文件到Git..." -ForegroundColor Cyan
git add .

Write-Host ""
Write-Host "[步骤4] 检查要提交的文件..." -ForegroundColor Cyan
$changes = git status --short
if ($changes) {
    Write-Host "以下文件将被提交:" -ForegroundColor Yellow
    git status --short
    Write-Host ""
    
    # 检查是否有大文件
    $largeFiles = git ls-files | ForEach-Object {
        $file = Get-Item $_ -ErrorAction SilentlyContinue
        if ($file -and $file.Length -gt 50MB) {
            Write-Host "[警告] 大文件: $($file.Name) ($([math]::Round($file.Length / 1MB, 2)) MB)" -ForegroundColor Yellow
            $file.FullName
        }
    }
    
    if ($largeFiles) {
        Write-Host ""
        Write-Host "[警告] 检测到大文件，可能会影响上传速度" -ForegroundColor Yellow
        Write-Host "建议: 使用GitHub Release发布大文件，而不是提交到代码仓库" -ForegroundColor Yellow
        Write-Host ""
        $continue = Read-Host "是否继续？(y/n)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            Write-Host "已取消" -ForegroundColor Yellow
            exit 0
        }
    }
    
    Write-Host ""
    $commitMessage = Read-Host "请输入提交信息 (直接回车使用默认信息)"
    if ([string]::IsNullOrWhiteSpace($commitMessage)) {
        $commitMessage = "Initial commit: UI推理工具"
    }
    
    git commit -m $commitMessage
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 提交失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] 提交成功" -ForegroundColor Green
} else {
    Write-Host "[信息] 没有需要提交的文件" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[步骤5] 检查远程仓库..." -ForegroundColor Cyan
$remoteUrl = git remote get-url origin -ErrorAction SilentlyContinue

if ($remoteUrl) {
    Write-Host "[信息] 已配置远程仓库: $remoteUrl" -ForegroundColor Yellow
    $useExisting = Read-Host "是否使用现有远程仓库？(y/n)"
    if ($useExisting -ne "y" -and $useExisting -ne "Y") {
        git remote remove origin
        $remoteUrl = $null
    }
}

if (-not $remoteUrl) {
    if ([string]::IsNullOrWhiteSpace($RepoUrl)) {
        Write-Host ""
        Write-Host "请提供GitHub仓库地址:" -ForegroundColor Cyan
        Write-Host "示例: https://github.com/用户名/仓库名.git" -ForegroundColor Gray
        Write-Host "或者: git@github.com:用户名/仓库名.git" -ForegroundColor Gray
        Write-Host ""
        $RepoUrl = Read-Host "GitHub仓库地址"
    }
    
    if ([string]::IsNullOrWhiteSpace($RepoUrl)) {
        Write-Host "[错误] 未提供仓库地址" -ForegroundColor Red
        Write-Host ""
        Write-Host "请先创建GitHub仓库，然后运行:" -ForegroundColor Yellow
        Write-Host "  git remote add origin <仓库地址>" -ForegroundColor Gray
        Write-Host "  git push -u origin main" -ForegroundColor Gray
        exit 1
    }
    
    Write-Host "[信息] 添加远程仓库: $RepoUrl" -ForegroundColor Cyan
    git remote add origin $RepoUrl
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 添加远程仓库失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] 远程仓库添加成功" -ForegroundColor Green
}

Write-Host ""
Write-Host "[步骤6] 获取默认分支名..." -ForegroundColor Cyan
$defaultBranch = "main"
try {
    $branchInfo = git branch -r 2>&1
    if ($branchInfo -match "origin/main") {
        $defaultBranch = "main"
    } elseif ($branchInfo -match "origin/master") {
        $defaultBranch = "master"
    }
} catch {
    # 如果远程分支不存在，使用main作为默认值
    $defaultBranch = "main"
}

Write-Host "[信息] 使用分支: $defaultBranch" -ForegroundColor Cyan

Write-Host ""
Write-Host "[步骤7] 拉取远程更新..." -ForegroundColor Cyan
git pull origin $defaultBranch --allow-unrelated-histories --no-edit -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "[步骤8] 推送代码到GitHub..." -ForegroundColor Cyan
Write-Host "这可能需要一些时间，请耐心等待..." -ForegroundColor Yellow
git push -u origin $defaultBranch

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "上传成功！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "您的代码已上传到GitHub:" -ForegroundColor Cyan
    if ($remoteUrl) {
        Write-Host $remoteUrl.Replace(".git", "") -ForegroundColor Yellow
    } elseif ($RepoUrl) {
        Write-Host $RepoUrl.Replace(".git", "") -ForegroundColor Yellow
    }
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "[错误] 推送失败" -ForegroundColor Red
    Write-Host ""
    Write-Host "可能的原因:" -ForegroundColor Yellow
    Write-Host "1. 认证失败 - 请检查GitHub用户名和密码/token" -ForegroundColor Gray
    Write-Host "2. 网络问题 - 请检查网络连接" -ForegroundColor Gray
    Write-Host "3. 权限问题 - 请检查仓库权限" -ForegroundColor Gray
    Write-Host ""
    Write-Host "解决方法:" -ForegroundColor Yellow
    Write-Host "1. 使用Personal Access Token作为密码" -ForegroundColor Gray
    Write-Host "2. 配置SSH密钥" -ForegroundColor Gray
    Write-Host "3. 手动推送: git push -u origin $defaultBranch" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

