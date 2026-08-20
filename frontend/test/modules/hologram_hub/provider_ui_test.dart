import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Provider UI Tests', () {
    testWidgets('hiển thị thông tin provider và chế độ an toàn', (tester) async {
      // TODO: Render ProviderCard
      // Xác minh hiển thị tên provider (DeepSeek/Codex) và chế độ (cosa_governed, isolated_coding)
    });

    testWidgets('không hiển thị secret hoặc transcript raw', (tester) async {
      // TODO: Render event chứa credentials (nếu có, lẽ ra đã bị redact ở backend)
      // Xác minh UI không chứa secret
    });
  });
}
