# ==============================================================================
# iBanking Microservices - Automatic Setup & Environment Validator Script
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
    Write-Host "[1/4] Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item $exampleFile $envFile
} else {
    Write-Host "[1/4] .env file exists. Checking configuration..." -ForegroundColor Green
}

# Helper function to generate strong random alphanumeric strings
function Generate-RandomSecret([int]$length = 32) {
    $bytes = New-Object byte[] $length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    return -join ($bytes | ForEach-Object { "{0:x2}" -f $_ })
}

Write-Host "[2/4] Generating unique, cryptographically secure secrets for placeholders..." -ForegroundColor Yellow
$content = Get-Content $envFile -Raw -Encoding UTF8

$replacements = @{
    "CHANGE_ME_ROOT_PASSWORD"        = (Generate-RandomSecret 16)
    "CHANGE_ME_USER_DB_PASSWORD"     = (Generate-RandomSecret 16)
    "CHANGE_ME_TUITION_DB_PASSWORD"  = (Generate-RandomSecret 16)
    "CHANGE_ME_PAYMENT_DB_PASSWORD"  = (Generate-RandomSecret 16)
    "CHANGE_ME_JWT_SECRET_KEY"       = (Generate-RandomSecret 32)
    "CHANGE_ME_INTERNAL_API_KEY"     = (Generate-RandomSecret 32)
    "CHANGE_ME_INTERNAL_SECRET_KEY"  = (Generate-RandomSecret 32)
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
    Write-Host "  -> No placeholder tokens detected." -ForegroundColor Green
}

# [3/4] Xác thực cấu hình nghiêm ngặt (Fail-fast validation)
Write-Host "[3/4] Validating environment configuration..." -ForegroundColor Yellow
$envLines = Get-Content $envFile -Encoding UTF8
$envMap = @{}

foreach ($line in $envLines) {
    $trimmed = $line.Trim()
    if ($trimmed -ne "" -and -not $trimmed.StartsWith("#")) {
        $parts = $trimmed.Split("=", 2)
        if ($parts.Length -eq 2) {
            $key = $parts[0].Trim()
            $val = $parts[1].Trim()
            $envMap[$key] = $val
        }
    }
}

$requiredKeys = @(
    "MYSQL_ROOT_PASSWORD",
    "USER_DB_USER",
    "USER_DB_PASSWORD",
    "TUITION_DB_USER",
    "TUITION_DB_PASSWORD",
    "PAYMENT_DB_USER",
    "PAYMENT_DB_PASSWORD",
    "JWT_SECRET_KEY",
    "INTERNAL_API_KEY",
    "ALLOWED_ORIGINS",
    "SMTP_HOST",
    "SMTP_PORT"
)

$hasError = $false
foreach ($reqKey in $requiredKeys) {
    if (-not $envMap.ContainsKey($reqKey) -or [string]::IsNullOrWhiteSpace($envMap[$reqKey])) {
        Write-Host "  [FAIL] Missing or empty required configuration: $($reqKey)" -ForegroundColor Red
        $hasError = $true
    } elseif ($envMap[$reqKey].Contains("CHANGE_ME")) {
        Write-Host "  [FAIL] Unresolved placeholder in $($reqKey) - value: $($envMap[$reqKey])" -ForegroundColor Red
        $hasError = $true
    }
}

# Kiểm tra nếu dùng SMTP ngoài (Gmail, ...) thì bắt buộc phải có USER và PASSWORD
if ($envMap.ContainsKey("SMTP_HOST") -and $envMap["SMTP_HOST"] -notin @("mailpit", "localhost", "127.0.0.1")) {
    if (-not $envMap.ContainsKey("SMTP_USER") -or [string]::IsNullOrWhiteSpace($envMap["SMTP_USER"])) {
        Write-Host "  [FAIL] External SMTP host requires SMTP_USER to be set." -ForegroundColor Red
        $hasError = $true
    }
    if (-not $envMap.ContainsKey("SMTP_PASSWORD") -or [string]::IsNullOrWhiteSpace($envMap["SMTP_PASSWORD"])) {
        Write-Host "  [FAIL] External SMTP host requires SMTP_PASSWORD to be set." -ForegroundColor Red
        $hasError = $true
    }
}

if ($hasError) {
    Write-Host ""
    Write-Host "[ERROR] Environment validation failed! Please fix the errors in .env above." -ForegroundColor Red
    exit 1
}

Write-Host "  -> Configuration validation passed! All required secrets and ports are set." -ForegroundColor Green

Write-Host ""
Write-Host "[4/4] System is ready to launch!" -ForegroundColor Cyan
Write-Host "  - To start all containers:  docker compose up -d --build" -ForegroundColor White
Write-Host "  - Web Interface:           http://localhost:3000" -ForegroundColor White
Write-Host "  - API Gateway Docs:        http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Mailpit (OTP Inbox):     http://localhost:8025" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Cyan
