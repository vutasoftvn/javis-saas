import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Profile Composition UI Tests', () {
    testWidgets('hiển thị danh sách profile và giải thích các tool không khả dụng', (tester) async {
      // TODO: Render màn hình chi tiết Profile
      // Verify hiển thị reason_code SCOPE cho crm.read
    });

    testWidgets('chỉ admin mới thấy nút publish/edit version', (tester) async {
      // TODO: Giả lập user role member, verify nút Publish bị ẩn
    });

    testWidgets('giao diện override cho phép loại bỏ tool nhưng không cho phép thêm', (tester) async {
      // TODO: Render Session Override widget
      // Verify chỉ có các nút checkbox để disable tool đang có
    });
  });
}
