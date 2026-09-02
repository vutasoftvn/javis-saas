// Task 5 — RuntimeAppChrome là nơi DUY NHẤT hiển thị RemoteAccessBanner,
// đặt phía trên toàn bộ nội dung shell. Banner đọc trạng thái từ
// `RemoteAccessController` (được `SessionController` đồng bộ khi commit) —
// không tự parse JSON picker.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

import 'package:frontend/core/widgets/runtime_app_chrome.dart';
import 'package:frontend/modules/remote_access/controllers/remote_access_controller.dart';
import 'package:frontend/modules/remote_access/models/runtime_status.dart';

Widget _appWithRuntime(RuntimeStatus? status) {
  final controller = Get.put(RemoteAccessController());
  controller.status.value = status;
  return GetMaterialApp(
    home: const RuntimeAppChrome(child: Text('SHELL_BODY')),
  );
}

void main() {
  setUp(() {
    Get.testMode = true;
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('shell displays stale read-only banner for remote offline workspace', (tester) async {
    final remoteOfflineStatus = RuntimeStatus(
      mode: RuntimeMode.remoteAccess,
      presence: NodePresence.offline,
      asOf: DateTime.utc(2026, 9, 2, 3, 4),
    );

    await tester.pumpWidget(_appWithRuntime(remoteOfflineStatus));
    await tester.pump();

    expect(find.textContaining('chỉ đọc'), findsOneWidget);
    expect(find.textContaining('Dữ liệu tính đến'), findsOneWidget);
    // Body vẫn hiển thị phía dưới banner — offline không được che mất toàn
    // bộ shell, chỉ chặn mutation + báo trạng thái.
    expect(find.text('SHELL_BODY'), findsOneWidget);
  });

  testWidgets('shell shows no banner for a healthy local-only workspace', (tester) async {
    await tester.pumpWidget(_appWithRuntime(
      RuntimeStatus(mode: RuntimeMode.localOnly, presence: NodePresence.online),
    ));
    await tester.pump();

    expect(find.textContaining('chỉ đọc'), findsNothing);
    expect(find.text('SHELL_BODY'), findsOneWidget);
  });

  testWidgets('shell shows no banner when RemoteAccessController is not registered', (tester) async {
    await tester.pumpWidget(GetMaterialApp(
      home: const RuntimeAppChrome(child: Text('SHELL_BODY')),
    ));
    await tester.pump();

    expect(find.textContaining('chỉ đọc'), findsNothing);
    expect(find.text('SHELL_BODY'), findsOneWidget);
  });
}
