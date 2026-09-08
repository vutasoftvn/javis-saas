import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/workflows/models/graph_models.dart';
import 'package:frontend/modules/workflows/widgets/canvas.dart';

void main() {
  group('Workflow Builder Widget Tests', () {
    // NOTE: Không có widget "WorkflowBuilder" hay palette node riêng trong
    // codebase — widget canvas thật là `WorkflowCanvas`
    // (frontend/lib/modules/workflows/widgets/canvas.dart). Đã xác nhận
    // (grep toàn bộ frontend/lib/modules/workflows, không tìm thấy
    // `Draggable`/`DragTarget`/palette/revision token/lock token) rằng
    // các hành vi sau CHƯA tồn tại nên các test case tương ứng bị xoá thay
    // vì giữ test rỗng luôn xanh (xem task-8-report.md):
    //   - "hiển thị danh sách node trên palette" — không có palette widget.
    //   - "kéo thả node từ palette vào canvas" — không có Draggable/DragTarget.
    //   - "từ chối nối các port không tương thích type" — canvas không có
    //     khái niệm port hay thao tác nối cạnh (edges chỉ vẽ tĩnh từ graph
    //     truyền vào, không có tương tác tạo edge mới).
    //   - "lưu bản nháp với revision token" — không có API optimistic-lock
    //     draft nào được gọi từ module workflows.
    // Hành vi thật duy nhất mà `WorkflowCanvas` triển khai: render node theo
    // toạ độ x/y trong `WorkflowGraph` và gọi `onNodeSelected` khi tap vào
    // node — giữ lại test case "hiển thị inspector khi chọn node" dưới dạng
    // test cho đúng cơ chế đó (callback selection, không phải render
    // inspector — canvas không tự render inspector).

    testWidgets('tap vào node trên canvas gọi onNodeSelected với đúng node', (tester) async {
      final nodeA = GraphNode(id: 'a', type: 'start', definitionId: 'def-a', x: 10, y: 10);
      final nodeB = GraphNode(id: 'b', type: 'http_call', definitionId: 'def-b', x: 200, y: 10);
      final graph = WorkflowGraph(
        entryNodeId: 'a',
        nodes: {'a': nodeA, 'b': nodeB},
        edges: [],
      );

      GraphNode? selected;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: WorkflowCanvas(
              graph: graph,
              onNodeSelected: (node) => selected = node,
            ),
          ),
        ),
      );

      expect(find.text('def-a'), findsOneWidget);
      expect(find.text('def-b'), findsOneWidget);

      await tester.tap(find.text('def-b'));
      await tester.pump();

      expect(selected, isNotNull);
      expect(selected!.id, 'b');
    });
  });
}
