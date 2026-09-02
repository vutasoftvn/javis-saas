// Task 10 — trước đây `HologramHubView.build` gọi `Get.put(FounderCommandCenterController())`
// trực tiếp, tạo ra MỘT instance thứ hai chồng lên instance mà `DashboardBinding`
// đã đăng ký qua `lazyPut` khi vào route `/hub`. Hai instance riêng biệt cùng
// giữ state độc lập (dữ liệu dashboard, chat sheet...) là chính xác kiểu
// "duplicate hub controller ownership" mà Task 10 phải khoá lại. Test này
// giả lập đúng trình tự production thật: binding đăng ký trước (`lazyPut`),
// rồi view mới `build` — và khẳng định CHỈ có một instance được `Get.find`
// thấy trong suốt vòng đời, không có bản sao nào bị tạo thêm khi view build
// lại nhiều lần.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/dashboard/controllers/dashboard_controller.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client originalClient;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_123'});
    Get.testMode = true;
    originalClient = ApiClient.client;
    ApiClient.client = MockClient((request) async => http.Response('{}', 200));
  });

  tearDown(() {
    ApiClient.client = originalClient;
    Get.reset();
  });

  testWidgets(
    'HologramHubView reuses the FounderCommandCenterController registered by the route binding — no duplicate instance',
    (tester) async {
      // Mô phỏng đúng thứ tự production: `DashboardBinding` đăng ký
      // `FounderCommandCenterController` bằng `lazyPut` TRƯỚC khi view của
      // route `/hub` được build.
      Get.lazyPut<DashboardController>(() => DashboardController());
      Get.lazyPut<FounderCommandCenterController>(() => FounderCommandCenterController());

      await tester.pumpWidget(
        const GetMaterialApp(home: Scaffold(body: HologramHubView())),
      );
      await tester.pump();

      final instanceAfterFirstBuild = Get.find<FounderCommandCenterController>();

      // Build lại view (vd. rebuild do parent Obx) không được tạo thêm bản
      // sao mới — `HologramHubView` không còn tự `Get.put`.
      await tester.pumpWidget(
        const GetMaterialApp(home: Scaffold(body: HologramHubView())),
      );
      await tester.pump();

      final instanceAfterSecondBuild = Get.find<FounderCommandCenterController>();

      expect(identical(instanceAfterFirstBuild, instanceAfterSecondBuild), isTrue);
    },
  );
}
