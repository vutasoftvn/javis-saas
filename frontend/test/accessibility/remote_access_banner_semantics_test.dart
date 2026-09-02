// Task 10 — Task 5 đã thêm `Semantics(liveRegion: true, label: ...)` cho
// `RemoteAccessBanner`, nhưng chưa có test nào khẳng định label đó THẬT SỰ
// lộ ra dưới dạng semantics node đọc được bởi assistive technology (khác
// với chỉ đọc được qua `find.text` trên cây widget thường). Test này pump
// banner trong `RuntimeAppChrome` thật (như production dùng), bật semantics
// binding, rồi kiểm tra `tester.getSemantics` — không chỉ "label tồn tại
// trong code" mà "trình đọc màn hình sẽ nhìn thấy nó".
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

import 'package:frontend/core/widgets/runtime_app_chrome.dart';
import 'package:frontend/modules/remote_access/controllers/remote_access_controller.dart';
import 'package:frontend/modules/remote_access/models/runtime_status.dart';
import 'package:frontend/modules/remote_access/widgets/remote_access_banner.dart';

Widget _appWithRuntime(RuntimeStatus? status) {
  final controller = Get.put(RemoteAccessController());
  controller.status.value = status;
  return GetMaterialApp(
    debugShowCheckedModeBanner: false,
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

  testWidgets('offline runtime banner is announced to assistive technology', (tester) async {
    final handle = tester.ensureSemantics();

    final remoteOfflineStatus = RuntimeStatus(
      mode: RuntimeMode.remoteAccess,
      presence: NodePresence.offline,
      asOf: DateTime.utc(2026, 9, 2, 3, 4),
    );

    await tester.pumpWidget(_appWithRuntime(remoteOfflineStatus));
    await tester.pump();

    final semantics = tester.getSemantics(find.byType(RemoteAccessBanner));
    expect(semantics.label.toLowerCase(), contains('offline'));
    expect(semantics.flagsCollection.isLiveRegion, isTrue);

    handle.dispose();
  });
}
