#!/usr/bin/env bash
# ==============================================================================
#  COSA Local Management CLI (cosa.sh)
#  Usage: ./cosa.sh [command]
#  Commands: start | stop | restart | status | logs | doctor | backup | restore | reset
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Docker Compose detection
if docker compose version &> /dev/null; then
    DC="docker compose"
elif command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    echo "Docker Compose is required."
    exit 1
fi

case "$1" in
    start|up)
        echo "🚀 Khởi động COSA Local Services..."
        $DC up -d
        echo "✅ Các dịch vụ đang chạy. Truy cập: http://localhost:8000/docs"
        ;;

    stop|down)
        echo "🛑 Dừng COSA Local Services..."
        $DC down
        echo "✅ Đã dừng toàn bộ dịch vụ."
        ;;

    restart)
        echo "🔄 Khởi động lại COSA Local Services..."
        $DC down
        $DC up -d
        echo "✅ Khởi động lại hoàn tất."
        ;;

    status|ps)
        echo "📊 Trạng thái dịch vụ COSA Local:"
        $DC ps
        echo ""
        echo "🔍 Kiểm tra kết nối API..."
        curl -fsS http://127.0.0.1:8000/ready 2>/dev/null && echo "✅ Brain API: READY" || echo "⚠️ Brain API: UNREACHABLE"
        ;;

    logs)
        shift
        $DC logs -f "$@"
        ;;

    doctor)
        echo "🩺 Chạy chẩn đoán hệ thống COSA Doctor..."
        $DC exec -T brain-api python -m app.scripts.cosa_doctor
        ;;

    backup)
        BACKUP_DIR="${SCRIPT_DIR}/backups"
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        TARGET_DIR="${BACKUP_DIR}/cosa_backup_${TIMESTAMP}"
        mkdir -p "$TARGET_DIR"

        echo "📦 Đang sao lưu dữ liệu COSA Local..."
        echo "  -> Đang trích xuất PostgreSQL dump..."
        $DC exec -T postgres pg_dump -U javis -d javis -F c -b -v -f /tmp/database.dump
        $DC cp postgres:/tmp/database.dump "${TARGET_DIR}/database.dump"
        
        echo "  -> Đang tạo manifest.json..."
        cat <<EOF > "${TARGET_DIR}/manifest.json"
{
  "backup_version": "1.0",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "database": "postgresql_pgvector",
  "scope": "company_local_operational_data"
}
EOF

        ARCHIVE_FILE="${BACKUP_DIR}/cosa_backup_${TIMESTAMP}.tar.gz"
        tar -czf "$ARCHIVE_FILE" -C "$BACKUP_DIR" "cosa_backup_${TIMESTAMP}"
        rm -rf "$TARGET_DIR"

        echo "✅ Sao lưu hoàn tất! File sao lưu tại:"
        echo "   👉 ${ARCHIVE_FILE}"
        ;;

    restore)
        if [ -z "$2" ]; then
            echo "❌ Vui lòng cung cấp đường dẫn file backup: ./cosa.sh restore <file.tar.gz>"
            exit 1
        fi
        BACKUP_FILE="$2"
        if [ ! -f "$BACKUP_FILE" ]; then
            echo "❌ Không tìm thấy file: $BACKUP_FILE"
            exit 1
        fi
        
        echo "⚠️  CẢNH BÁO: Thao tác này sẽ ghi đè dữ liệu PostgreSQL Local hiện tại."
        read -rp "Bạn có chắc chắn muốn khôi phục không? (y/N): " confirm
        if [[ "$confirm" =~ ^[yY]$ ]]; then
            TEMP_EXTRACT=$(mktemp -d)
            tar -xzf "$BACKUP_FILE" -C "$TEMP_EXTRACT"
            DUMP_FILE=$(find "$TEMP_EXTRACT" -name "database.dump" | head -n 1)
            if [ -n "$DUMP_FILE" ]; then
                $DC cp "$DUMP_FILE" postgres:/tmp/restore.dump
                $DC exec -T postgres pg_restore -U javis -d javis -c --if-exists /tmp/restore.dump || true
                echo "✅ Đã khôi phục dữ liệu thành công!"
            else
                echo "❌ Không tìm thấy database.dump trong file backup!"
            fi
            rm -rf "$TEMP_EXTRACT"
        else
            echo "Đã hủy thao tác khôi phục."
        fi
        ;;

    reset)
        echo "⚠️  CẢNH BÁO NGUY HIỂM: Thao tác này sẽ XÓA TOÀN BỘ dữ liệu local và volumes!"
        read -rp "Bạn có chắc chắn muốn xóa sạch để cài đặt lại không? (type 'DELETE'): " confirm
        if [ "$confirm" = "DELETE" ]; then
            $DC down -v
            echo "✅ Toàn bộ container và volume dữ liệu đã được dọn sạch."
            echo "👉 Chạy './install.sh' để cài đặt lại từ đầu."
        else
            echo "Đã hủy thao tác reset."
        fi
        ;;

    deploy)
        echo "🚀 Deploy toàn bộ (app + control plane schema)..."
        $DC pull
        $DC up --build -d
        echo "⏳ Đang chờ brain-api sẵn sàng..."
        attempt=0
        until curl -fsS http://127.0.0.1:8000/ready > /dev/null 2>&1; do
            attempt=$((attempt + 1))
            [ $attempt -lt 30 ] || { echo "❌ brain-api không khởi động được"; exit 1; }
            sleep 2
        done
        echo "✅ App deployed."
        echo "⏳ Chạy Central Control Plane migration..."
        $DC --profile control-plane run --rm migrate-control-plane
        echo "✅ Deploy hoàn tất!"
        ;;

    deploy-control-plane|migrate-control-plane)
        echo "⏳ Chạy Central Control Plane schema migration..."
        echo "   URL: ${CONTROL_PLANE_DATABASE_URL:-postgresql://javis:javis@postgres:5432/javis}"
        $DC --profile control-plane run --rm migrate-control-plane
        echo "✅ Control Plane migration hoàn tất!"
        ;;

    help|*)
        echo "COSA Local CLI - Công cụ quản lý môi trường dữ liệu cục bộ"
        echo ""
        echo "Sử dụng: ./cosa.sh [lệnh]"
        echo ""
        echo "Các lệnh hỗ trợ:"
        echo "  start                   Khởi động toàn bộ dịch vụ COSA Local"
        echo "  stop                    Dừng toàn bộ dịch vụ"
        echo "  restart                 Khởi động lại dịch vụ"
        echo "  status                  Xem trạng thái chi tiết của các container và API"
        echo "  logs                    Xem log thời gian thực (vd: ./cosa.sh logs brain-api)"
        echo "  doctor                  Chẩn đoán toàn diện sức khỏe hệ thống"
        echo "  backup                  Sao lưu toàn bộ dữ liệu PostgreSQL & Workspace"
        echo "  restore                 Khôi phục dữ liệu từ file backup"
        echo "  reset                   Xóa sạch dữ liệu volumes để cài mới"
        echo ""
        echo "  deploy                  Full deploy: app + control plane schema migration"
        echo "  deploy-control-plane    Chỉ chạy Central Control Plane schema migration"
        echo "  help                    Hiển thị bảng trợ giúp này"
        ;;
esac
