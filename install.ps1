# ==============================================================================
#  COSA Local Data & Platform Installer (Windows PowerShell)
#  Architecture: Local PostgreSQL (pgvector) + MinIO + LiveKit Cloud + Brain API
# ==============================================================================

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "       🚀 COSA OS — LOCAL DATA & HYBRID RUNTIME INSTALLER        " -ForegroundColor Cyan
Write-Host "      Self-hosted Local PostgreSQL • MinIO • Brain API • Agents  " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

# Helper: Read key from .env
function Get-EnvVal($key) {
    if (Test-Path ".env") {
        $line = Get-Content ".env" | Where-Object { $_ -match "^$key=" } | Select-Object -First 1
        if ($line) {
            return ($line -split "=", 2)[1]
        }
    }
    return ""
}

# Helper: Set or update key in .env
function Set-EnvVal($key, $val) {
    if (-not (Test-Path ".env")) {
        New-Item -ItemType File -Name ".env" | Out-Null
    }
    $lines = @(Get-Content ".env")
    $found = $false
    $newLines = @()
    foreach ($l in $lines) {
        if ($l -match "^$key=") {
            $newLines += "$key=$val"
            $found = $true
        } else {
            $newLines += $l
        }
    }
    if (-not $found) {
        $newLines += "$key=$val"
    }
    $newLines | Set-Content ".env"
}

# Helper: Interactive Prompt
function Prompt-Key($key, $title, $defaultHint) {
    $curVal = Get-EnvVal $key
    $hint = ""
    if (![string]::IsNullOrWhiteSpace($curVal)) {
        if ($curVal.Length -gt 8) {
            $masked = $curVal.Substring(0, 4) + "..." + $curVal.Substring($curVal.Length - 4)
            $hint = "[Hiện tại: $masked - Nhấn Enter để giữ nguyên]"
        } else {
            $hint = "[Hiện tại: $curVal - Nhấn Enter để giữ nguyên]"
        }
    } elseif (![string]::IsNullOrWhiteSpace($defaultHint)) {
        $hint = "[Mặc định: $defaultHint]"
    }

    $inputVal = Read-Host "  • $title $hint"
    if (![string]::IsNullOrWhiteSpace($inputVal)) {
        Set-EnvVal $key $inputVal
    } elseif ([string]::IsNullOrWhiteSpace($curVal) -and ![string]::IsNullOrWhiteSpace($defaultHint)) {
        Set-EnvVal $key $defaultHint
    }
}

# 1. Dependency Checks
Write-Host "[1/5] Kiểm tra môi trường hệ thống..." -ForegroundColor Blue

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker chưa được cài đặt trên máy của bạn!" -ForegroundColor Red
    Write-Host "👉 Vui lòng tải và cài đặt Docker Desktop tại: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    Exit 1
}

$dockerCheck = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker daemon chưa chạy. Vui lòng mở Docker Desktop rồi thử lại." -ForegroundColor Red
    Exit 1
}

Write-Host "✅ Docker Desktop đang hoạt động tốt." -ForegroundColor Green

# 2. Environment Setup (.env)
Write-Host "[2/5] Khởi tạo cấu hình bảo mật môi trường (.env)..." -ForegroundColor Blue

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Đã tạo file .env từ .env.example." -ForegroundColor Green
    }
}

# 3. Interactive Configuration
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "      ⚙️  THIẾT LẬP THÔNG SỐ & API KEYS (Nhấn Enter để giữ mặc định)" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

Write-Host "`n[1] Tài khoản Quản trị viên Local (Admin):" -ForegroundColor White
$curAdminPass = Get-EnvVal "DEV_ADMIN_PASSWORD"
if ([string]::IsNullOrWhiteSpace($curAdminPass)) { $curAdminPass = "Admin123456" }
Prompt-Key "DEV_ADMIN_PASSWORD" "Mật khẩu Admin" $curAdminPass
$env:DEV_ADMIN_PASSWORD = Get-EnvVal "DEV_ADMIN_PASSWORD"

Write-Host "`n[2] Khóa API Nhà Cung Cấp AI (LLM Providers):" -ForegroundColor White
Prompt-Key "KIRAAI_API_KEY" "Kira AI API Key (Cổng AI Việt Nam - Mặc định, Free/Nhanh)" ""

$curKiraModel = Get-EnvVal "KIRAAI_DEFAULT_MODEL"
if ([string]::IsNullOrWhiteSpace($curKiraModel)) { $curKiraModel = "deepseek-v4-pro-free" }

Write-Host "`n  🤖 Lựa chọn Model Kira AI mặc định:" -ForegroundColor Cyan
Write-Host "    1) deepseek-v4-pro-free  (DeepSeek V4 Pro - Miễn phí, Hỗ trợ Tools) [Mặc định]"
Write-Host "    2) deepseek-chat         (DeepSeek V3 - Nhanh, đa nhiệm)"
Write-Host "    3) deepseek-reasoner     (DeepSeek R1 - Suy luận logic chuyên sâu)"
Write-Host "    4) claude-3-7-sonnet     (Claude 3.7 Sonnet - Code & reasoning mạnh mẽ)"
Write-Host "    5) claude-3-5-sonnet     (Claude 3.5 Sonnet - Độ chính xác cao)"
Write-Host "    6) gpt-4o                (OpenAI GPT-4o)"
Write-Host "    7) gpt-4o-mini           (OpenAI GPT-4o Mini - Phản hồi siêu nhanh)"
Write-Host "    8) gemini-2.0-flash      (Google Gemini 2.0 Flash - Context 1M tokens)"
Write-Host "    9) Nhập tên model tùy chỉnh khác"

$modelChoice = Read-Host "  👉 Chọn model [1-9 hoặc Enter để chọn '$curKiraModel']"
$selectedModel = $curKiraModel
switch ($modelChoice) {
    "1" { $selectedModel = "deepseek-v4-pro-free" }
    "2" { $selectedModel = "deepseek-chat" }
    "3" { $selectedModel = "deepseek-reasoner" }
    "4" { $selectedModel = "claude-3-7-sonnet" }
    "5" { $selectedModel = "claude-3-5-sonnet" }
    "6" { $selectedModel = "gpt-4o" }
    "7" { $selectedModel = "gpt-4o-mini" }
    "8" { $selectedModel = "gemini-2.0-flash" }
    "9" { 
        $customM = Read-Host "  ✍️  Nhập ID model Kira AI"
        if (![string]::IsNullOrWhiteSpace($customM)) { $selectedModel = $customM }
    }
    default {
        if (![string]::IsNullOrWhiteSpace($modelChoice)) { $selectedModel = $modelChoice }
    }
}
Set-EnvVal "KIRAAI_DEFAULT_MODEL" $selectedModel
Set-EnvVal "CHAT_DEFAULT_MODEL" $selectedModel
Write-Host "✅ Model Kira AI được chọn: $selectedModel" -ForegroundColor Green

Write-Host ""
Prompt-Key "GEMINI_API_KEY" "Google Gemini API Key" ""
Prompt-Key "DEEPSEEK_API_KEY" "DeepSeek API Key (Trực tiếp)" ""
Prompt-Key "OPENAI_API_KEY" "OpenAI API Key" ""
Prompt-Key "OPENROUTER_API_KEY" "OpenRouter API Key" ""

$curProvider = Get-EnvVal "CHAT_DEFAULT_PROVIDER"
if ([string]::IsNullOrWhiteSpace($curProvider)) {
    Set-EnvVal "CHAT_DEFAULT_PROVIDER" "kira_ai"
}

Write-Host "`n[3] Cấu hình Realtime Voice (LiveKit Cloud):" -ForegroundColor White
Prompt-Key "LIVEKIT_URL" "LiveKit Cloud URL" "wss://example.livekit.cloud"
Prompt-Key "LIVEKIT_API_KEY" "LiveKit API Key" "devkey"
Prompt-Key "LIVEKIT_API_SECRET" "LiveKit API Secret" "secret_local_cosa_desktop_key"

Write-Host "`n✅ Đã lưu toàn bộ cấu hình vào file .env." -ForegroundColor Green

# 4. Start Docker Services
Write-Host "`n[3/5] Đang khởi động các dịch vụ COSA Local (PostgreSQL, MinIO)..." -ForegroundColor Blue
docker compose up -d postgres minio

Write-Host "Đang chờ PostgreSQL Local sẵn sàng..." -ForegroundColor Blue
$attempt = 0
while ($attempt -lt 30) {
    $res = docker compose exec -T postgres pg_isready -U javis 2>&1
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 1
    $attempt++
}
Write-Host "✅ PostgreSQL Local (pgvector) đã sẵn sàng." -ForegroundColor Green

Write-Host "Đang áp dụng Database Migrations (Alembic)..." -ForegroundColor Blue
docker compose up -d migrate
Start-Sleep -Seconds 3

Write-Host "Đang khởi động Brain API & Agent Worker..." -ForegroundColor Blue
docker compose up -d brain-api agent-worker

Write-Host "Đang kiểm tra trạng thái Brain API..." -ForegroundColor Blue
$attempt = 0
while ($attempt -lt 30) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/ready" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) { break }
    } catch {}
    Start-Sleep -Seconds 1
    $attempt++
}
Write-Host "✅ Các dịch vụ cốt lõi đã hoạt động." -ForegroundColor Green

# 5. Bootstrap User
Write-Host "[4/5] Khởi tạo tài khoản Quản trị viên Local..." -ForegroundColor Blue
docker compose exec -T -e DEV_ADMIN_PASSWORD="$env:DEV_ADMIN_PASSWORD" brain-api python -m app.scripts.bootstrap_dev_user

# 6. Diagnostics
Write-Host "[5/5] Chẩn đoán hệ thống (COSA Doctor)..." -ForegroundColor Blue
docker compose exec -T brain-api python -m app.scripts.cosa_doctor

# 7. Summary
Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   🎉 CÀI ĐẶT COSA LOCAL DATA & PLATFORM HOÀN TẤT THÀNH CÔNG!   " -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📍 THÔNG TIN TRUY CẬP VÀ QUẢN TRỊ:" -ForegroundColor White
Write-Host "  • Brain API & Swagger Docs:  http://localhost:8000/docs"
Write-Host "  • Health Check Endpoint:     http://localhost:8000/ready"
Write-Host "  • MinIO Storage Console:     http://localhost:9001 (minioadmin / minioadmin)"
Write-Host "  • PostgreSQL Local:          localhost:5432 (DB: javis, User: javis, Pass: javis)"
Write-Host ""
Write-Host "👤 TÀI KHOẢN ĐĂNG NHẬP LOCAL ADMIN:" -ForegroundColor White
Write-Host "  • Email:     admin@javis.local"
Write-Host "  • Mật khẩu:  $env:DEV_ADMIN_PASSWORD"
Write-Host ""
Write-Host "🛠️ CÔNG CỤ QUẢN LÝ DÒNG LỆNH:" -ForegroundColor White
Write-Host "  • Dừng hệ thống:             docker compose down"
Write-Host "  • Khởi động lại:             docker compose up -d"
Write-Host "  • Xem log trực tiếp:         docker compose logs -f"
Write-Host "==================================================================" -ForegroundColor Green
