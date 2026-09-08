import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/settings/workforce/views/profile_composition_view.dart';

void main() {
  group('Profile Composition UI Tests', () {
    // NOTE: `ProfileCompositionView` hiện tại (frontend/lib/modules/settings/
    // workforce/views/profile_composition_view.dart) chỉ nhận `items` tĩnh
    // (List<AgentReadinessItem>) và render tên profile + trạng thái ready/
    // not-ready + danh sách missingCapabilities/missingPermissions dạng text
    // thô. Widget KHÔNG có: role/permission prop, nút Publish/Edit version,
    // hay "Session Override" widget để bật/tắt tool. Đã đọc toàn bộ file —
    // không có logic ẩn/hiện theo role admin/member, không có checkbox
    // override nào. Do đó 2 test case sau bị xoá thay vì giữ rỗng luôn xanh
    // (xem task-8-report.md):
    //   - "chỉ admin mới thấy nút publish/edit version" — không có nút này.
    //   - "giao diện override cho phép loại bỏ tool nhưng không cho phép
    //     thêm" — không có Session Override widget trong module này.

    testWidgets('hiển thị danh sách profile với capability/permission còn thiếu', (tester) async {
      const items = [
        AgentReadinessItem(
          profileId: 'p1',
          profileName: 'Finance Analyst',
          missingCapabilities: ['crm.read'],
        ),
        AgentReadinessItem(
          profileId: 'p2',
          profileName: 'Marketing Assistant',
        ),
      ];

      await tester.pumpWidget(
        const MaterialApp(home: ProfileCompositionView(items: items)),
      );

      expect(find.text('Finance Analyst'), findsOneWidget);
      expect(find.text('Marketing Assistant'), findsOneWidget);

      // Profile thiếu capability hiển thị chip "Action Required" và liệt kê
      // tool bị thiếu (vd. crm.read).
      expect(find.byKey(const ValueKey('not_ready_p1')), findsOneWidget);
      expect(find.text('• crm.read'), findsOneWidget);

      // Profile không thiếu gì hiển thị chip "Ready".
      expect(find.byKey(const ValueKey('ready_p2')), findsOneWidget);
    });

    testWidgets('hiển thị placeholder khi danh sách profile rỗng', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: ProfileCompositionView()),
      );

      expect(
        find.text('Danh sách profile và giải thích các tool không khả dụng sẽ hiển thị ở đây.'),
        findsOneWidget,
      );
    });
  });
}
