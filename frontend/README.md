# frontend

A new Flutter project.

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Learn Flutter](https://docs.flutter.dev/get-started/learn-flutter)
- [Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Flutter learning resources](https://docs.flutter.dev/reference/learning-resources)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.

## Coverage

CI (`.github/workflows/quality.yml`) chạy 2 tầng test frontend:

1. **Line-coverage floor** — `flutter test --coverage` rồi
   `scripts/check_frontend_coverage.mjs ... --minimum=46 --exclude='**/views/**,**/widgets/**'`.
   Floor này áp cho **code logic**: `services/`, `controllers/`, `models/`,
   `core/`. File `views/` và `widgets/` (UI thuần) **không** tính vào mẫu số —
   line-coverage cho code dựng widget là tín hiệu nhiễu.
2. **Test hành vi UI** — `test/` (widget test), `test/golden/`,
   `test/accessibility/`, và `integration_test/` (chạy với fixture riêng, hoặc
   real-stack ở nightly). Đây là nơi đảm bảo view/widget hoạt động đúng.

Khi thêm module mới: viết unit test cho service/controller/model để giữ floor,
và widget/golden test cho view. Không hạ `--minimum`; nếu cần nới `--exclude`,
ghi lý do trong PR.
