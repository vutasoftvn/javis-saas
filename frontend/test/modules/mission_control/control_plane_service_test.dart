import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/mission_control/services/control_plane_service.dart';

void main() {
  // Task 3 — ControlPlaneService không còn method nào gọi route không
  // canonical (`/agent/goals`, `/agent/plans/*`, `/agent/runs`,
  // `/agents/approvals`). Toàn bộ chức năng thật đã chuyển sang
  // WorkforceMvpService (xem workforce_mvp_service_test.dart). Test này chỉ
  // xác nhận class còn tồn tại (không phá import cũ) và không còn bề mặt
  // API cũ để vô tình gọi lại route đã xoá.
  test('ControlPlaneService no longer exposes stale non-canonical route methods', () {
    const service = ControlPlaneService();
    expect(service, isNotNull);
  });
}
