#!/usr/bin/env bash
# Task 18 (P5) — chạy 3 file `frontend/integration_test/*_test.dart` ở chế độ
# `E2E_MODE=real` chống lại stack 4 plane THẬT.
#
# Script này KHÔNG tự boot stack (quá dễ vỡ để sở hữu ở đây). Nó chỉ:
#   1. Kiểm tra company:4000 / cosa:4001 / api:8000 `/healthz` đang sống.
#   2. Chạy từng file integration_test MỘT LẦN MỘT (`-d macos`) với các
#      `--dart-define` trỏ vào stack thật — chạy cả thư mục 1 lệnh làm macOS
#      desktop driver rớt kết nối từ file thứ 2 (known issue, xem
#      `docs/testing/frontend-integration.md` §8 + `tool/run_quality.sh`).
#   3. In tổng kết PASS/FAIL từng file.
#
# Tiền đề: `make dev-stack` đã chạy VÀ được khởi động với
# `E2E_TEST_SEED_ENABLED=1` (seed đi qua `POST /identity/_e2e/session`, handler
# trả 404 nếu thiếu biến này). Ví dụ:
#   E2E_TEST_SEED_ENABLED=1 make dev-stack
#
# Override URL qua env: E2E_COMPANY_URL / E2E_COSA_URL / E2E_API_URL.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPANY_URL="${E2E_COMPANY_URL:-http://127.0.0.1:4000}"
COSA_URL="${E2E_COSA_URL:-http://127.0.0.1:4001}"
API_URL="${E2E_API_URL:-http://127.0.0.1:8000}"
DEVICE="${E2E_FLUTTER_DEVICE:-macos}"

check_health() {
  local name="$1" url="$2"
  if curl -fsS "${url}/healthz" >/dev/null 2>&1; then
    echo "  ✓ ${name} (${url})"
    return 0
  fi
  echo "  ✗ ${name} (${url}) — /healthz không phản hồi"
  return 1
}

echo "── Kiểm tra stack 4 plane ──"
missing=0
check_health "company" "$COMPANY_URL" || missing=1
check_health "cosa" "$COSA_URL" || missing=1
check_health "api" "$API_URL" || missing=1
if [ "$missing" -ne 0 ]; then
  cat >&2 <<EOF

Stack thật chưa sẵn sàng. Chạy trước:
    E2E_TEST_SEED_ENABLED=1 make dev-stack
rồi chạy lại script này. (Script này cố tình KHÔNG tự boot stack.)
EOF
  exit 1
fi

# Cảnh báo mềm nếu seed endpoint không bật — vẫn chạy để lỗi hiện rõ trong test.
if curl -fsS -o /dev/null -w '%{http_code}' -X POST \
     -H 'content-type: application/json' -d '{}' \
     "${COMPANY_URL}/identity/_e2e/session" 2>/dev/null | grep -q '^404$'; then
  echo "  ⚠ POST ${COMPANY_URL}/identity/_e2e/session → 404: stack có vẻ KHÔNG"
  echo "    được khởi động với E2E_TEST_SEED_ENABLED=1 — seed sẽ fail."
fi

shopt -s nullglob
files=(integration_test/*_test.dart)
shopt -u nullglob
if [ ${#files[@]} -eq 0 ]; then
  echo "Không tìm thấy integration_test/*_test.dart — fail cứng (không skip im lặng)." >&2
  exit 1
fi

echo
echo "── flutter test (E2E_MODE=real, device=${DEVICE}) ──"
declare -a results=()
status=0
for f in "${files[@]}"; do
  echo
  echo "==> $f"
  if flutter test "$f" -d "$DEVICE" -r compact \
      --dart-define=E2E_MODE=real \
      --dart-define=E2E_COMPANY_URL="$COMPANY_URL" \
      --dart-define=E2E_COSA_URL="$COSA_URL" \
      --dart-define=E2E_API_URL="$API_URL"; then
    results+=("PASS $f")
  else
    results+=("FAIL $f")
    status=1
  fi
done

echo
echo "── Tổng kết ──"
for r in "${results[@]}"; do
  echo "  $r"
done
exit $status
