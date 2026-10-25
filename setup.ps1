# ==============================================================================
# iBanking Microservices - Automatic Setup Script (Phase 1 Security Cleanup)
# ==============================================================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "         iBanking TDTU - Quick Setup & Environment Configurator       " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$envFile = Join-Path $PSScriptRoot ".env"
$exampleFile = Join-Path $PSScriptRoot ".env.example"

if (-not (Test-Path $exampleFile)) {
    Write-Host "[ERROR] .env.example not found!" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $envFile)) {
    Write-Host "[1/3] Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item $exampleFile $envFile
} else {
    Write-Host "[1/3] .env file already exists. Checking for placeholder tokens..." -ForegroundColor Green
}

# Helper function to generate strong random alphanumeric strings
function Generate-RandomSecret([int]$length = 32) {
    $bytes = New-Object byte[] $length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    return -join ($bytes | ForEach-Object { "{0:x2}" -f $_ })
}

Write-Host "[2/3] Generating unique, cryptographically secure secrets..." -ForegroundColor Yellow
$content = Get-Content $envFile -Raw -Encoding UTF8

$replacements = @{
    "CHANGE_ME_ROOT_PASSWORD"        = (Generate-RandomSecret 16)
    "CHANGE_ME_USER_DB_PASSWORD"     = (Generate-RandomSecret 16)
    "CHANGE_ME_TUITION_DB_PASSWORD"  = (Generate-RandomSecret 16)
    "CHANGE_ME_PAYMENT_DB_PASSWORD"  = (Generate-RandomSecret 16)
    "CHANGE_ME_JWT_SECRET_KEY"       = (Generate-RandomSecret 32)
    "CHANGE_ME_INTERNAL_API_KEY"     = (Generate-RandomSecret 32)
}

$modified = $false
foreach ($key in $replacements.Keys) {
    if ($content.Contains($key)) {
        $content = $content.Replace($key, $replacements[$key])
        $modified = $true
    }
}

if ($modified) {
    [System.IO.File]::WriteAllText($envFile, $content, [System.Text.Encoding]::UTF8)
    Write-Host "  -> Successfully generated unique DB passwords and API/JWT keys in .env!" -ForegroundColor Green
} else {
    Write-Host "  -> All secrets already configured in .env." -ForegroundColor Green
}

Write-Host ""
Write-Host "[3/3] Ready for launch!" -ForegroundColor Cyan
Write-Host "  1. To start all containers:  docker compose up -d --build" -ForegroundColor White
Write-Host "  2. Web Interface:           http://localhost:3000" -ForegroundColor White
Write-Host "  3. API Gateway Docs:        http://localhost:8000/docs" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Cyan
