import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Workflow Builder Widget Tests', () {
    testWidgets('hiển thị danh sách node trên palette', (tester) async {
      // TODO: Render Widget và verify hiển thị danh sách
    });

    testWidgets('kéo thả node từ palette vào canvas', (tester) async {
      // TODO: Giả lập thao tác kéo thả và verify node xuất hiện trong Graph
    });

    testWidgets('từ chối nối các port không tương thích type', (tester) async {
      // TODO: Giả lập kéo từ string-port sang object-port và verify lỗi
    });

    testWidgets('hiển thị inspector khi chọn node', (tester) async {
      // TODO: Tap vào node, verify thông tin config hiện lên inspector
    });

    testWidgets('lưu bản nháp với revision token', (tester) async {
      // TODO: Verify gọi API update draft với optimistic lock token
    });
  });
}
