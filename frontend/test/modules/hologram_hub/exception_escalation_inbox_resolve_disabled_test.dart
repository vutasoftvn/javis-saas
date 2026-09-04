// Truthfulness fix (2026-09-02): `AgentPlatformService.resolveEscalation`
// gọi `POST /workforce/exceptions/{id}/resolve` — route này không tồn tại ở
// backend (`apps/cosa/api/workforce_routes.py` chỉ đăng ký prefix
// `/agent/workforce/*`, không có `exceptions/*` nào). Trước fix, nút hành
// động (Retry/Giao lại/Tăng hạn mức/...) trong ExceptionEscalationInbox vẫn
// bấm được, luôn gọi route chết đó, luôn 404 bị nuốt thành `null`, và founder
// không nhận được phản hồi gì — nút "chạy" nhưng không làm gì.
//
// Test này chứng minh: (1) nút hành động không còn tappable — bấm vào vị trí
// hiển thị nhãn action không gọi `onResolve` một lần nào; (2) banner honest
// "chưa khả dụng" luôn hiển thị ngay từ đầu, không cần chờ người dùng bấm.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

import 'package:frontend/modules/hologram_hub/views/widgets/exception_escalation_inbox.dart';

Map<String, dynamic> _escalation({
  String tier = 'LEAD_NOTIFY',
  String exceptionType = 'AGENT_STALL',
}) {
  return {
    'id': 'run_failed_1',
    'tier': tier,
    'exception_type': exceptionType,
    'agent_key': 'agent-x',
    'stage_code': 'P2',
    'details': {'elapsed_minutes': 20},
    'created_at': DateTime.now().toIso8601String(),
  };
}

void main() {
  testWidgets(
    'resolve action buttons are disabled and show an honest unavailable '
    'banner instead of silently no-oping on tap',
    (tester) async {
      // Widget tự tính chiều cao bằng 88% MediaQuery height — nới viewport
      // test đủ lớn để ListView bên trong không bị overflow giả (không liên
      // quan gì tới hành vi đang test).
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      var resolveCallCount = 0;
      final escalations = <Map<String, dynamic>>[_escalation()].obs;
      final isLoading = false.obs;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ExceptionEscalationInbox(
              escalations: escalations,
              summary: const {
                'founder_gate_count': 0,
                'lead_notify_count': 1,
              },
              isLoading: isLoading,
              onResolve: (id, action, comment) {
                resolveCallCount++;
              },
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Banner giải thích lý do chưa khả dụng phải hiển thị ngay, không cần
      // tap trước.
      expect(
        find.textContaining('Xử lý escalation qua API hiện chưa khả dụng'),
        findsOneWidget,
      );

      // Action buttons (đã đổi màu mờ) vẫn hiển thị nhãn cho founder biết
      // hành động nào sẽ có, nhưng phải KHÔNG tappable.
      final actionFinder = find.byKey(const Key('escalation_action_disabled_retry'));
      expect(actionFinder, findsOneWidget);

      // Không còn GestureDetector nào bọc action container — chứng minh
      // control này bị vô hiệu hoá ở cấp cấu trúc, không phải chỉ về mặt
      // hình ảnh.
      final gestureDetectors = find.ancestor(
        of: actionFinder,
        matching: find.byType(GestureDetector),
      );
      expect(gestureDetectors, findsNothing);

      // Tap vào đúng vị trí nút action trước đây — không được gọi onResolve,
      // tức là không có đường nào để bấm vẫn kích hoạt lệnh gọi route chết.
      await tester.tap(actionFinder, warnIfMissed: false);
      await tester.pumpAndSettle();

      expect(
        resolveCallCount,
        0,
        reason: 'Resolve action phải bị vô hiệu hoá hoàn toàn — tap không '
            'được phép gọi onResolve (vốn dẫn tới route backend không tồn '
            'tại).',
      );
    },
  );
}
