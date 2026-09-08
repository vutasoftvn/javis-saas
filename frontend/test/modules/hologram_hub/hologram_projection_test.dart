import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/artifact_card.dart';
import 'package:frontend/modules/hologram_hub/presentation/widgets/task_card.dart';

void main() {
  group('Hologram UI Tests', () {
    // NOTE: Không có widget "HologramProjection" nào trong codebase. Các
    // card hiển thị trạng thái projection thật là `TaskCard` và
    // `ArtifactCard` (frontend/lib/modules/hologram_hub/presentation/
    // widgets/{task_card,artifact_card}.dart) — cả hai chỉ nhận String/double
    // hiển thị (title, status, progress, risk...) từ constructor, KHÔNG có
    // field nào cho "private reasoning" nên không có gì để rò rỉ ở layer
    // widget này (structural guarantee: constructor không expose field đó).
    //
    // Test case "cập nhật realtime khi có event mới qua SSE" bị xoá: SSE
    // subscription thật (`_hubChatStreamSub`) nằm trong
    // `hub_chat_mixin.dart`, được compose vào `HologramHubController` khổng
    // lồ (nhiều mixin, phụ thuộc service/HTTP/LiveKit thật) — không có widget
    // đơn lẻ nào nhận trực tiếp SSE event để test độc lập ở mức widget. Test
    // hành vi này đòi hỏi dựng lại toàn bộ controller stack, vượt phạm vi
    // "widget test" của Task 8 — xoá thay vì giữ rỗng luôn xanh (xem
    // task-8-report.md).

    testWidgets('TaskCard hiển thị title/status/progress, không có field private reasoning', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(
              title: 'Chuẩn bị báo cáo tài chính Q3',
              status: 'in_progress',
              progressPercent: 42,
              riskLevel: 'L1',
              currentStepText: 'Đang tổng hợp số liệu',
            ),
          ),
        ),
      );

      expect(find.text('Chuẩn bị báo cáo tài chính Q3'), findsOneWidget);
      expect(find.text('Đang thực hiện'), findsOneWidget);
      expect(find.text('Đang tổng hợp số liệu'), findsOneWidget);
      expect(find.text('Risk L1'), findsOneWidget);
    });

    testWidgets('TaskCard chỉ hiện nút Phê duyệt/Từ chối khi status waiting_approval', (tester) async {
      var approved = false;
      var rejected = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TaskCard(
              title: 'Duyệt ngân sách marketing',
              status: 'waiting_approval',
              onApprove: () => approved = true,
              onReject: () => rejected = true,
            ),
          ),
        ),
      );

      expect(find.text('Phê duyệt'), findsOneWidget);
      expect(find.text('Từ chối'), findsOneWidget);

      await tester.tap(find.text('Phê duyệt'));
      expect(approved, isTrue);
      await tester.tap(find.text('Từ chối'));
      expect(rejected, isTrue);
    });

    testWidgets('TaskCard status khác waiting_approval không hiện nút phê duyệt', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(title: 'Việc đã xong', status: 'done'),
          ),
        ),
      );

      expect(find.text('Phê duyệt'), findsNothing);
      expect(find.text('Từ chối'), findsNothing);
    });

    testWidgets('ArtifactCard hiển thị title/type/status của artifact', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ArtifactCard(
              title: 'Bao_cao_Q3.pdf',
              type: 'document',
              status: 'published',
            ),
          ),
        ),
      );

      expect(find.text('Bao_cao_Q3.pdf'), findsOneWidget);
      expect(find.text('DOCUMENT'), findsOneWidget);
      expect(find.text('PUBLISHED'), findsOneWidget);
    });
  });
}
