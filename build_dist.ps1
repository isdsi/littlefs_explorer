# ==============================================================================
# LittleFS Explorer 배포판(dist) 빌드 스크립트
# ==============================================================================

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venvPython = Join-Path $scriptDir "venv\Scripts\python.exe"
$venvPip = Join-Path $scriptDir "venv\Scripts\pip.exe"
$venvPyinstaller = Join-Path $scriptDir "venv\Scripts\pyinstaller.exe"

# 1. 가상환경 확인
if (-not (Test-Path $venvPython)) {
    Write-Host "[오류] 가상 환경(venv)을 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "먼저 '.\venv_install.ps1'을 실행하여 환경을 구축해주세요." -ForegroundColor Yellow
    exit 1
}

# 2. PyInstaller 설치 확인
if (-not (Test-Path $venvPyinstaller)) {
    Write-Host "[1/3] PyInstaller가 설치되어 있지 않습니다. 설치를 시작합니다..." -ForegroundColor Cyan
    & $venvPip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[오류] PyInstaller 설치 실패" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[1/3] PyInstaller 준비 완료." -ForegroundColor Green
}

# 3. 배포 폴더 준비 및 기존 잔여물 정리
Write-Host "[2/3] 이전 빌드 캐시 정리 중..." -ForegroundColor Cyan
if (Test-Path "$scriptDir\build") {
    Remove-Item -Path "$scriptDir\build" -Recurse -Force -ErrorAction SilentlyContinue
}
if (-not (Test-Path "$scriptDir\dist")) {
    New-Item -ItemType Directory -Path "$scriptDir\dist" | Out-Null
}

# 4. PyInstaller 빌드 실행
Write-Host "[3/3] LittleFS_Explorer 단일 실행 파일(.exe) 빌드 시작..." -ForegroundColor Cyan

& $venvPyinstaller `
    --name "LittleFS_Explorer" `
    --onefile `
    --noconsole `
    --clean `
    --add-data "img;img" `
    --hidden-import "littlefs" `
    --hidden-import "esptool" `
    --distpath "dist" `
    "littlefs_explorer.py"

if ($LASTEXITCODE -eq 0) {
    $targetExe = Join-Path $scriptDir "dist\LittleFS_Explorer.exe"
    if (Test-Path $targetExe) {
        $fileSizeMB = [math]::Round(((Get-Item $targetExe).Length / 1MB), 2)
        Write-Host "`n========================================================" -ForegroundColor Green
        Write-Host " [성공] 배포판 빌드가 완료되었습니다!" -ForegroundColor Green
        Write-Host " 위치: $targetExe" -ForegroundColor Yellow
        Write-Host " 크기: $fileSizeMB MB" -ForegroundColor Yellow
        Write-Host "========================================================`n" -ForegroundColor Green
    }
} else {
    Write-Host "`n[오류] 빌드 중 에러가 발생했습니다." -ForegroundColor Red
    exit $LASTEXITCODE
}
