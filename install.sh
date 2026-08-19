#!/usr/bin/env bash
# ==============================================================================
#  COSA Local Data & Platform Installer (macOS / Linux / WSL)
#  Architecture: Local PostgreSQL (pgvector) + MinIO + LiveKit Cloud + Brain API
# ==============================================================================

set -eo pipefail

# Text formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_header() {
    echo -e "${CYAN}"
    echo "=================================================================="
    echo "       🚀 COSA OS — LOCAL DATA & HYBRID RUNTIME INSTALLER        "
    echo "      Self-hosted Local PostgreSQL • MinIO • Brain API • Agents  "
    echo "=================================================================="
    echo -e "${NC}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Helper: Read key from .env
get_env_val() {
    local key="$1"
    if [ -f .env ]; then
        grep -E "^${key}=" .env | cut -d '=' -f2- || true
    fi
}

# Helper: Set or update key in .env
set_env_val() {
    local key="$1"
    local val="$2"
    if [ ! -f .env ]; then
        touch .env
    fi
    if grep -q "^${key}=" .env; then
        # Use python or awk/sed safely for values with special characters
        python3 -c "
import sys, re
key, val = sys.argv[1], sys.argv[2]
with open('.env', 'r') as f:
    lines = f.readlines()
with open('.env', 'w') as f:
    found = False
    for line in lines:
        if line.startswith(f'{key}='):
            f.write(f'{key}={val}\n')
            found = True
        else:
            f.write(line)
    if not found:
        f.write(f'{key}={val}\n')
" "$key" "$val"
    else
        echo "${key}=${val}" >> .env
    fi
}

# Helper: Interactive Prompt
prompt_key() {
    local key="$1"
    local prompt_title="$2"
    local default_hint="$3"
    local is_password="${4:-false}"
    
    local current_val
    current_val=$(get_env_val "$key")
    
    local display_hint=""
    if [ -n "$current_val" ]; then
        if [ "$is_password" = true ]; then
            display_hint="[Hiện tại: ********** - Nhấn Enter để giữ nguyên]"
        else
            # Mask partially if long
            if [ ${#current_val} -gt 8 ]; then
                local masked="${current_val:0:4}...${current_val: -4}"
                display_hint="[Hiện tại: ${masked} - Nhấn Enter để giữ nguyên]"
            else
                display_hint="[Hiện tại: ${current_val} - Nhấn Enter để giữ nguyên]"
            fi
        fi
    elif [ -n "$default_hint" ]; then
        display_hint="[Mặc định: ${default_hint}]"
    fi
    
    local user_input
    if [ "$is_password" = true ] && [ -z "$current_val" ]; then
        read -rsp "  🔑 ${prompt_title} ${display_hint}: " user_input
        echo ""
    else
        read -rp "  • ${prompt_title} ${display_hint}: " user_input
    fi
    
    if [ -n "$user_input" ]; then
        set_env_val "$key" "$user_input"
    elif [ -z "$current_val" ] && [ -n "$default_hint" ]; then
        set_env_val "$key" "$default_hint"
    fi
}

# 1. Dependency Checks
check_dependencies() {
    log_info "1/5 Kiểm tra môi trường hệ thống..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker chưa được cài đặt trên máy của bạn!"
        echo -e "👉 Vui lòng tải và cài đặt Docker Desktop tại: ${BOLD}https://www.docker.com/products/docker-desktop/${NC}"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon chưa khởi động!"
        echo -e "👉 Vui lòng mở ứng dụng Docker Desktop hoặc chạy 'sudo systemctl start docker' rồi thử lại."
        exit 1
    fi

    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    else
        log_error "Docker Compose chưa được cài đặt!"
        exit 1
    fi

    log_success "Docker và Docker Compose sẵn sàng."
}

# 2. Port conflict check
check_ports() {
    log_info "Kiểm tra cổng mạng (5432, 8000, 9000)..."
    ports=(5432 8000 9000)
    conflict=false

    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            running_container=$(docker ps --filter "publish=$port" --format "{{.Names}}" 2>/dev/null || true)
            if [ -n "$running_container" ]; then
                log_warn "Cổng $port đang được dùng bởi container '$running_container' (sẽ restart khi cần)."
            else
                log_warn "Cổng $port đang được sử dụng bởi ứng dụng khác trên máy!"
                conflict=true
            fi
        fi
    done

    if [ "$conflict" = true ]; then
        echo -e "${YELLOW}👉 Nếu quá trình khởi động gặp lỗi 'port is already allocated', vui lòng tắt bớt dịch vụ chiếm cổng.${NC}"
    fi
}

# 3. Environment Base Setup
setup_env_base() {
    log_info "2/5 Khởi tạo cấu hình bảo mật môi trường (.env)..."

    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            log_info "Đã tạo file .env từ .env.example."
        else
            touch .env
        fi
    fi

    # Generate secure random keys if empty or placeholder
    local cur_jwt
    cur_jwt=$(get_env_val "JWT_SECRET")
    if [ -z "$cur_jwt" ] || [ "$cur_jwt" = "supersecret-dev-key" ]; then
        RAND_JWT=$(openssl rand -hex 24 2>/dev/null || LC_ALL=C tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 48 || echo "cosa_jwt_secret_dev_key_32char_len")
        set_env_val "JWT_SECRET" "$RAND_JWT"
    fi

    local cur_master
    cur_master=$(get_env_val "MASTER_SECRET_KEY")
    if [ -z "$cur_master" ]; then
        RAND_MASTER=$(openssl rand -hex 24 2>/dev/null || LC_ALL=C tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 48 || echo "cosa_master_secret_key_32char_len")
        set_env_val "MASTER_SECRET_KEY" "$RAND_MASTER"
    fi
}

# 4. Interactive Configuration (Admin Password, LLM Keys, LiveKit Cloud)
configure_interactive() {
    echo ""
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}      ⚙️  THIẾT LẬP THÔNG SỐ & API KEYS (Nhấn Enter để giữ mặc định) ${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # 1. Admin Password
    echo -e "\n${BOLD}[1] Tài khoản Quản trị viên Local (Admin):${NC}"
    local cur_pass
    cur_pass=$(get_env_val "DEV_ADMIN_PASSWORD")
    prompt_key "DEV_ADMIN_PASSWORD" "Mật khẩu Admin" "${cur_pass:-Admin123456}" true
    DEV_ADMIN_PASSWORD=$(get_env_val "DEV_ADMIN_PASSWORD")
    export DEV_ADMIN_PASSWORD

    # 2. AI Model Provider Keys
    echo -e "\n${BOLD}[2] Khóa API Nhà Cung Cấp AI (LLM Providers):${NC}"
    prompt_key "KIRAAI_API_KEY" "Kira AI API Key (Cổng AI Việt Nam - Mặc định, Free/Nhanh)" "" false
    
    # Kira AI Model Selection
    local cur_kira_model
    cur_kira_model=$(get_env_val "KIRAAI_DEFAULT_MODEL")
    if [ -z "$cur_kira_model" ]; then
        cur_kira_model="deepseek-v4-pro-free"
    fi
    
    echo -e "\n  ${CYAN}🤖 Lựa chọn Model Kira AI mặc định:${NC}"
    echo -e "    1) ${BOLD}deepseek-v4-pro-free${NC}  (DeepSeek V4 Pro - Miễn phí, Hỗ trợ Tools) [Mặc định]"
    echo -e "    2) deepseek-chat         (DeepSeek V3 - Nhanh, đa nhiệm)"
    echo -e "    3) deepseek-reasoner     (DeepSeek R1 - Suy luận logic chuyên sâu)"
    echo -e "    4) claude-3-7-sonnet     (Claude 3.7 Sonnet - Code & reasoning mạnh mẽ)"
    echo -e "    5) claude-3-5-sonnet     (Claude 3.5 Sonnet - Độ chính xác cao)"
    echo -e "    6) gpt-4o                (OpenAI GPT-4o)"
    echo -e "    7) gpt-4o-mini           (OpenAI GPT-4o Mini - Phản hồi siêu nhanh)"
    echo -e "    8) gemini-2.0-flash      (Google Gemini 2.0 Flash - Context 1M tokens)"
    echo -e "    9) Nhập tên model tùy chỉnh khác"
    
    read -rp "  👉 Chọn model [1-9 hoặc Enter để chọn '${cur_kira_model}']: " model_choice
    case "$model_choice" in
        1|"") selected_model="${cur_kira_model:-deepseek-v4-pro-free}" ;;
        2) selected_model="deepseek-chat" ;;
        3) selected_model="deepseek-reasoner" ;;
        4) selected_model="claude-3-7-sonnet" ;;
        5) selected_model="claude-3-5-sonnet" ;;
        6) selected_model="gpt-4o" ;;
        7) selected_model="gpt-4o-mini" ;;
        8) selected_model="gemini-2.0-flash" ;;
        9) read -rp "  ✍️  Nhập ID model Kira AI: " custom_m; selected_model="${custom_m:-deepseek-v4-pro-free}" ;;
        *) selected_model="$model_choice" ;;
    esac
    set_env_val "KIRAAI_DEFAULT_MODEL" "$selected_model"
    set_env_val "CHAT_DEFAULT_MODEL" "$selected_model"
    log_success "Model Kira AI được chọn: ${selected_model}"

    echo ""
    prompt_key "GEMINI_API_KEY" "Google Gemini API Key" "" false
    prompt_key "DEEPSEEK_API_KEY" "DeepSeek API Key (Trực tiếp)" "" false
    prompt_key "OPENAI_API_KEY" "OpenAI API Key" "" false
    prompt_key "OPENROUTER_API_KEY" "OpenRouter API Key" "" false

    # Ensure default model provider is set
    local cur_provider
    cur_provider=$(get_env_val "CHAT_DEFAULT_PROVIDER")
    if [ -z "$cur_provider" ]; then
        set_env_val "CHAT_DEFAULT_PROVIDER" "kira_ai"
    fi

    # 3. LiveKit Cloud Credentials
    echo -e "\n${BOLD}[3] Cấu hình Realtime Voice (LiveKit Cloud):${NC}"
    prompt_key "LIVEKIT_URL" "LiveKit Cloud URL" "wss://example.livekit.cloud" false
    prompt_key "LIVEKIT_API_KEY" "LiveKit API Key" "devkey" false
    prompt_key "LIVEKIT_API_SECRET" "LiveKit API Secret" "secret_local_cosa_desktop_key" false

    echo -e "\n${GREEN}✅ Đã lưu toàn bộ cấu hình vào file .env an toàn.${NC}"
}

# 5. Build and Start Services
start_services() {
    log_info "3/5 Đang tải & khởi động các dịch vụ COSA Local (PostgreSQL, MinIO, Brain API)..."
    
    $DOCKER_COMPOSE_CMD up -d postgres minio

    log_info "Đang chờ PostgreSQL Local sẵn sàng..."
    attempt=0
    max_attempts=30
    until $DOCKER_COMPOSE_CMD exec -T postgres pg_isready -U javis >/dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            log_error "PostgreSQL Local không khởi động kịp thời. Vui lòng kiểm tra: '$DOCKER_COMPOSE_CMD logs postgres'"
            exit 1
        fi
        sleep 1
    done
    log_success "PostgreSQL Local (pgvector) đã sẵn sàng."

    log_info "Đang áp dụng Database Migrations (Alembic)..."
    $DOCKER_COMPOSE_CMD up -d migrate
    sleep 3

    log_info "Đang khởi động Brain API & Agent Worker..."
    $DOCKER_COMPOSE_CMD up -d brain-api agent-worker

    log_info "Đang kiểm tra trạng thái Brain API..."
    attempt=0
    until curl -fsS http://127.0.0.1:8000/ready >/dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ $attempt -ge 30 ]; then
            log_warn "Brain API mất nhiều thời gian hơn dự kiến, đang tiếp tục..."
            break
        fi
        sleep 1
    done
    log_success "Các dịch vụ cốt lõi đã hoạt động."
}

# 6. Bootstrap Initial Admin User & Workspace
bootstrap_system() {
    log_info "4/5 Khởi tạo tài khoản Quản trị viên Local & Không gian làm việc..."
    
    if $DOCKER_COMPOSE_CMD exec -T -e DEV_ADMIN_PASSWORD="$DEV_ADMIN_PASSWORD" brain-api python -m app.scripts.bootstrap_dev_user; then
        log_success "Tạo tài khoản Quản trị viên thành công."
    else
        log_warn "Khởi tạo người dùng gặp cảnh báo (có thể tài khoản đã tồn tại từ trước)."
    fi
}

# 7. System Diagnostics (COSA Doctor)
run_diagnostics() {
    log_info "5/5 Chạy chẩn đoán toàn diện hệ thống (COSA Doctor)..."
    echo ""
    $DOCKER_COMPOSE_CMD exec -T brain-api python -m app.scripts.cosa_doctor || true
}

# 8. Completion Summary
print_summary() {
    echo ""
    echo -e "${GREEN}==================================================================${NC}"
    echo -e "${GREEN}   🎉 CÀI ĐẶT COSA LOCAL DATA & PLATFORM HOÀN TẤT THÀNH CÔNG!   ${NC}"
    echo -e "${GREEN}==================================================================${NC}"
    echo ""
    echo -e "${BOLD}📍 THÔNG TIN TRUY CẬP VÀ QUẢN TRỊ:${NC}"
    echo -e "  • ${BOLD}Brain API & Swagger Docs:${NC}  http://localhost:8000/docs"
    echo -e "  • ${BOLD}Health Check Endpoint:${NC}     http://localhost:8000/ready"
    echo -e "  • ${BOLD}MinIO Storage Console:${NC}     http://localhost:9001 (minioadmin / minioadmin)"
    echo -e "  • ${BOLD}PostgreSQL Local:${NC}          localhost:5432 (DB: javis, User: javis, Pass: javis)"
    echo ""
    echo -e "${BOLD}👤 TÀI KHOẢN ĐĂNG NHẬP LOCAL ADMIN:${NC}"
    echo -e "  • ${BOLD}Email:${NC}     admin@javis.local"
    echo -e "  • ${BOLD}Mật khẩu:${NC}  $DEV_ADMIN_PASSWORD"
    echo ""
    echo -e "${BOLD}🛠️  CÔNG CỤ QUẢN LÝ NHANH (COSA CLI):${NC}"
    echo -e "  • Khởi động lại:     ${CYAN}./cosa.sh start${NC}"
    echo -e "  • Dừng hệ thống:     ${CYAN}./cosa.sh stop${NC}"
    echo -e "  • Xem log trực tiếp: ${CYAN}./cosa.sh logs${NC}"
    echo -e "  • Kiểm tra sức khỏe: ${CYAN}./cosa.sh doctor${NC}"
    echo -e "  • Sao lưu dữ liệu:   ${CYAN}./cosa.sh backup${NC}"
    echo -e "  • Khôi phục dữ liệu: ${CYAN}./cosa.sh restore <file.tar.gz>${NC}"
    echo ""
    echo -e "📱 ${BOLD}Mở ứng dụng Frontend Desktop / Web:${NC}"
    echo -e "  Chạy ứng dụng Flutter macOS/Windows hoặc mở Web Client."
    echo -e "${GREEN}==================================================================${NC}"
}

main() {
    print_header
    check_dependencies
    check_ports
    setup_env_base
    configure_interactive
    start_services
    bootstrap_system
    run_diagnostics
    print_summary
}

main "$@"
