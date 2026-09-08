import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/workflows/models/graph_models.dart';
import 'package:frontend/modules/workflows/widgets/node_inspector.dart';

void main() {
  group('Workflow Inspector Widget Tests', () {
    // NOTE: `NodeInspector` hiện tại (frontend/lib/modules/workflows/widgets/
    // node_inspector.dart) chỉ hiển thị id/type/definitionId/config của node
    // và một khối cảnh báo TĨNH ("Node này an toàn. (Mock diagnostic)") —
    // không có logic rủi ro động, không có dry-run/publish flow, không có
    // redaction bí mật, không có nút approve/reject theo trạng thái workflow.
    // Các test case gốc mô tả hành vi đó đã bị xoá (xem task-8-report.md) vì
    // feature chưa tồn tại — giữ lại test thật cho hành vi hiện có.

    testWidgets('hiển thị placeholder khi chưa chọn node nào', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: NodeInspector(selectedNode: null)),
      );

      expect(find.text('Chưa chọn node nào'), findsOneWidget);
    });

    testWidgets('hiển thị id, type, definition và config của node đang chọn', (tester) async {
      final node = GraphNode(
        id: 'node-1',
        type: 'http_call',
        definitionId: 'def-http-call',
        config: const {'url': 'https://api.example.com', 'timeout_ms': 3000},
      );

      await tester.binding.setSurfaceSize(const Size(400, 2000));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(home: NodeInspector(selectedNode: node)),
      );

      expect(find.text('ID: node-1'), findsOneWidget);
      expect(find.text('Type: http_call'), findsOneWidget);
      expect(find.text('Definition: def-http-call'), findsOneWidget);
      expect(find.text('url: https://api.example.com'), findsOneWidget);
      expect(find.text('timeout_ms: 3000'), findsOneWidget);
    });
  });
}
