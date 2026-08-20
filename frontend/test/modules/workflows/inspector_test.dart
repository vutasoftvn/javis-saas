import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Workflow Inspector Widget Tests', () {
    testWidgets('hiển thị thông tin rủi ro và bí mật của node', (tester) async {
      // TODO: Render widget NodeInspector, truyền vào mock NodeDefinition rủi ro cao, verify warning icon
    });

    testWidgets('gửi dry-run input và xác nhận publish', (tester) async {
      // TODO: Render màn hình Publish, giả lập nhập test payload, verify API call
    });

    testWidgets('ẩn thông tin private reasoning và secret payload', (tester) async {
      // TODO: Render live node status, verify không hiển thị các raw secret (như API key)
    });

    testWidgets('hiển thị nút approve/reject khi workflow pause', (tester) async {
      // TODO: Truyền state là paused/waiting_approval, verify hiển thị nút
    });
  });
}
