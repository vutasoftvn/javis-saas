import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/views/provider_card.dart';

void main() {
  group('Provider UI Tests', () {
    // NOTE: `ProviderCard` (frontend/lib/modules/hologram_hub/views/
    // provider_card.dart) chỉ nhận 3 String (providerName, mode, status) và
    // render nguyên văn — không có logic redact secret/transcript nào ở
    // widget layer. Đọc toàn bộ file: không có parsing JSON, không có regex
    // mask, không filter field nào — bất cứ string nào truyền vào sẽ hiển
    // thị y nguyên. Redaction (nếu có) phải xảy ra ở backend trước khi data
    // tới widget này (đúng như README của repo mô tả), nên test "không hiển
    // thị secret hoặc transcript raw" ở widget layer là vô nghĩa (sẽ luôn
    // pass giả tạo hoặc luôn fail tuỳ dữ liệu test tự chọn, không phản ánh
    // hành vi thật nào của widget) — đã xoá test case này thay vì giữ rỗng
    // luôn xanh (xem task-8-report.md).

    testWidgets('hiển thị tên provider và chế độ vận hành', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ProviderCard(
              providerName: 'DeepSeek',
              mode: 'cosa_governed',
              status: 'active',
            ),
          ),
        ),
      );

      expect(find.text('Provider: DeepSeek'), findsOneWidget);
      expect(find.text('Mode: cosa_governed | Status: active'), findsOneWidget);
      // cosa_governed dùng icon "security" (khác isolated_coding dùng "shield").
      expect(find.byIcon(Icons.security), findsOneWidget);
      expect(find.byIcon(Icons.shield), findsNothing);
    });

    testWidgets('isolated_coding hiển thị icon shield thay vì security', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ProviderCard(
              providerName: 'Codex',
              mode: 'isolated_coding',
              status: 'active',
            ),
          ),
        ),
      );

      expect(find.byIcon(Icons.shield), findsOneWidget);
      expect(find.byIcon(Icons.security), findsNothing);
    });
  });
}
