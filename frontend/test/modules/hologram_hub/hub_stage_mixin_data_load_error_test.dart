import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';

/// Tái hiện Finding 1 của review Task 9: `dataLoadError` được set khi
/// `loadProjectsList()` thất bại nhưng trước đây KHÔNG bao giờ được reset về
/// `null` khi lần tải lại sau đó thành công — khiến banner lỗi (nếu có nơi
/// nào render) kẹt vĩnh viễn dù dữ liệu đã tải lại đúng. Test này chứng minh
/// hành vi đã sửa: lỗi phải biến mất sau một lần retry thành công.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client originalClient;
  var callCount = 0;

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'ws_123',
    });
    Get.testMode = true;
    callCount = 0;
    originalClient = ApiClient.client;
    ApiClient.client = MockClient((request) async {
      if (request.url.path == '/operations/projects') {
        callCount += 1;
        if (callCount == 1) {
          // Lần đầu: lỗi máy chủ thật (không phải "chưa có dự án").
          return http.Response('{"detail":"internal error"}', 500);
        }
        // Lần retry: thành công với dữ liệu thật.
        return http.Response(
          '{"projects":[{"id":1,"title":"Project A"}]}',
          200,
        );
      }
      return http.Response('{}', 200);
    });
  });

  tearDown(() {
    ApiClient.client = originalClient;
    Get.reset();
  });

  test(
    'loadProjectsList clears dataLoadError after a failed-then-successful reload',
    () async {
      final controller = HologramHubController();

      await controller.loadProjectsList();
      expect(controller.dataLoadError.value, isNotNull);
      expect(controller.projectsList, isEmpty);

      await controller.loadProjectsList();
      expect(
        controller.dataLoadError.value,
        isNull,
        reason: 'dataLoadError phải được xoá sau khi retry thành công',
      );
      expect(controller.projectsList, hasLength(1));
    },
  );
}
