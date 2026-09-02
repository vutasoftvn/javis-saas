#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
flutter analyze
flutter test test/core/services/secure_storage_service_test.dart -r compact
flutter test test/modules/workspace_picker/workspace_picker_controller_test.dart -r compact
flutter test -r compact

# Task 11 — integration_test (`frontend/integration_test/*_test.dart`) đòi hỏi
# một device macOS thật (`flutter test <file> -d macos`) và mất thời gian
# đáng kể hơn hẳn unit test (build app macOS ~15-20s/file) — KHÔNG bắt buộc
# chạy mặc định ở local/PR (đã có analyzer + unit test ở trên phủ phần lớn
# lát dọc), chỉ bật khi biến môi trường `RUN_FRONTEND_INTEGRATION=1` (CI job
# release-candidate/nightly luôn set biến này — xem
# `.github/workflows/quality.yml` job `frontend-integration`). Chạy TỪNG file
# bằng một lời gọi `flutter test` riêng, KHÔNG gọi
# `flutter test integration_test` một lần cho cả thư mục — known limitation
# đã verify thực tế, xem docs/testing/frontend-integration.md §8 (nhiều
# instance app macOS liên tiếp trong 1 tiến trình test runner làm rớt kết nối
# debug từ file thứ 2 trở đi, dù mỗi file PASS hoàn toàn khi chạy độc lập).
if [ "${RUN_FRONTEND_INTEGRATION:-0}" = "1" ]; then
  shopt -s nullglob
  integration_files=(integration_test/*_test.dart)
  shopt -u nullglob
  if [ ${#integration_files[@]} -eq 0 ]; then
    # Task 11 nguyên tắc lõi — "A skipped test is not a green release gate":
    # không có file integration_test nào để chạy KHÔNG được coi là pass im
    # lặng, đây là hạ tầng test bị thiếu/hỏng, phải fail rõ ràng.
    echo "RUN_FRONTEND_INTEGRATION=1 nhưng không tìm thấy integration_test/*_test.dart — fail cứng (không skip im lặng)." >&2
    exit 1
  fi
  for f in "${integration_files[@]}"; do
    echo "── flutter test $f -d macos ──"
    flutter test "$f" -d macos -r compact
  done
fi

cd ..
node scripts/check_frontend_api_contracts.mjs
