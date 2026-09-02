// Task 10 — Skill Registry là view desktop-first thuần tuý trước đây (Row
// filter cố định, không hề đọc `layoutForWidth`). Ở compact width (điện
// thoại dọc, 390), hàng filter dọc theo domain + status pill tràn ngang
// không thể hiển thị hết — trước đây không có cơ chế thu gọn nào, chỉ tràn
// lặng lẽ ra ngoài viewport. Bài test này khoá hành vi: ở compact, filter
// phải thu vào MỘT nút "Bộ lọc" mở filter sheet dọc, không dùng `OverflowBar`
// (tránh "fix" hời hợt bằng cách bọc Row cũ trong OverflowBar thay vì thật
// sự thiết kế lại cho di động).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

import 'package:frontend/modules/skills/views/skill_registry_view.dart';

import '../support/responsive_test_helpers.dart';

void main() {
  setUp(() {
    Get.testMode = true;
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('skill registry uses a vertical filter sheet on compact layout', (tester) async {
    await pumpAtWidth(tester, const SkillRegistryView(), kCompactWidth);

    expect(find.byType(OverflowBar), findsNothing);
    expect(find.byTooltip('Bộ lọc'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('skill registry shows inline filters on medium and expanded layout', (tester) async {
    await pumpAtWidth(tester, const SkillRegistryView(), kMediumWidth);
    expect(find.byTooltip('Bộ lọc'), findsNothing);
    expect(tester.takeException(), isNull);

    await pumpAtWidth(tester, const SkillRegistryView(), kExpandedWidth);
    expect(find.byTooltip('Bộ lọc'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
