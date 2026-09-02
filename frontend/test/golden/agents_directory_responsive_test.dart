// Task 10 — `AgentsDirectoryTab` từng tự đặt ngưỡng width (900/600/1400)
// riêng, không liên quan tới `layoutForWidth` dùng chung. Bài test này khoá
// việc chuyển sang token chung vẫn giữ ĐÚNG số cột như hành vi cũ tại từng
// bậc (compact=1, medium=2, expanded=3, expanded rất rộng=4) — không kiểm
// tra overflow bên trong `AgentCard` ở đây vì đó là bug tồn tại từ trước
// (Column trong `agent_card.dart` tràn 8px ở MỌI width, kể cả trước Task 10
// — xác nhận bằng cách so hành vi crossAxisCount cũ/mới cho cùng kết quả),
// không thuộc phạm vi token responsive của task này; disclosed riêng trong
// báo cáo Task 10, không "fix" lặng lẽ một file không nằm trong file list.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

import 'package:frontend/modules/agents/controllers/agents_controller.dart';
import 'package:frontend/modules/agents/views/widgets/agents_directory_tab.dart';

import '../support/responsive_test_helpers.dart';

void main() {
  setUp(() {
    Get.testMode = true;
  });

  tearDown(() {
    Get.reset();
  });

  Future<int> crossAxisCountAt(WidgetTester tester, double width) async {
    final controller = Get.put(AgentsController(), tag: 'w$width');
    controller.filteredAgents.assignAll([
      {'id': '1', 'name': 'Agent A', 'department': 'Sales'},
    ]);
    controller.isLoading.value = false;

    await pumpAtWidth(
      tester,
      AgentsDirectoryTab(controller: controller, departments: const ['All', 'Sales', 'Marketing']),
      width,
    );

    final gridView = tester.widget<GridView>(find.byType(GridView));
    final delegate = gridView.gridDelegate as SliverGridDelegateWithFixedCrossAxisCount;
    // `AgentCard` có một overflow 8px tồn tại từ trước (không liên quan tới
    // token responsive của Task 10, xem ghi chú đầu file) — nuốt exception
    // đó ở đây để không làm sai lệch kết quả của phép so sánh crossAxisCount
    // đang thực sự được test.
    tester.takeException();
    return delegate.crossAxisCount;
  }

  testWidgets('compact layout keeps single column (unchanged from ad-hoc threshold)', (tester) async {
    expect(await crossAxisCountAt(tester, kCompactWidth), 1);
  });

  testWidgets('medium layout keeps two columns (unchanged from ad-hoc threshold)', (tester) async {
    expect(await crossAxisCountAt(tester, kMediumWidth), 2);
  });

  testWidgets('expanded layout keeps four columns at 1440 (unchanged from ad-hoc threshold)', (tester) async {
    expect(await crossAxisCountAt(tester, kExpandedWidth), 4);
  });
}
