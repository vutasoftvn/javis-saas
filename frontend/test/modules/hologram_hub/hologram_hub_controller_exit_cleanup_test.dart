// Task 10 — Step 3 đòi hỏi: "on exit, timers, voice handlers and realtime
// listeners all cancel and test their counters" — không chỉ "gọi onClose()
// không crash". Trước đây suite test của `HologramHubController` chỉ có
// test wake-word dispose (đếm qua `_FakeWakeWordService.isDisposed`); KHÔNG
// test nào chứng minh `_clockTimer`/`_refreshTimer`/`_realtimeDebounce`
// (Timer riêng) hay listener trên `RealtimeService` (singleton toàn app)
// thực sự bị huỷ sau `onClose()`. Test này dùng `fake_async` để kiểm soát
// thời gian tất định (đếm số lần side-effect của timer bắn ra trước/sau khi
// đóng) thay vì chỉ "không ném exception".
import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/realtime_service.dart';
import 'package:frontend/core/session/session_controller.dart';
import 'package:frontend/core/session/session_snapshot.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';

SessionSnapshot _activeSnapshot() => const SessionSnapshot(
      userId: 'user-1',
      workspaceId: 'ws-1',
      role: 'founder',
      runtime: SessionRuntimeInfo(
        mode: 'LOCAL_ONLY',
        modeSource: 'inferred',
        presenceStatus: 'ONLINE',
        lastHeartbeatAt: null,
        asOf: null,
      ),
      capabilities: ['workspace.session.read'],
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client originalClient;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws-1'});
    Get.testMode = true;
    AuthService.setCachedToken('fake-token-for-cleanup-test');
    originalClient = ApiClient.client;
    // Mọi request nền (loadStageContext/loadHubSummary/getMe/SSE...) đều
    // trả 200 rỗng — test này không quan tâm dữ liệu nghiệp vụ, chỉ quan
    // tâm vòng đời timer/listener.
    ApiClient.client = MockClient((request) async => http.Response('{}', 200));
  });

  tearDown(() {
    ApiClient.client = originalClient;
    AuthService.setCachedToken(null);
    RealtimeService().resetForTest();
    Get.reset();
  });

  test('onClose cancels the periodic clock timer — it stops ticking after close', () {
    fakeAsync((async) {
      final session = Get.put(SessionController());
      session.seedForTest(_activeSnapshot());

      final controller = HologramHubController();
      controller.onInit();
      // Để mọi Future nền (ensureAuthenticated/getMe/loadXxx) chạy xong
      // trong đồng hồ ảo trước khi bắt đầu đo timer.
      async.elapse(const Duration(milliseconds: 500));

      async.elapse(const Duration(seconds: 5));
      final ticksBeforeClose = controller.clockTickCountForTest;
      // Đồng hồ chạy mỗi giây → 5 giây ảo phải sinh ra ít nhất một vài lần
      // tick thật (không phải 0 — nếu là 0 nghĩa là timer chưa từng chạy,
      // bài test sẽ vô nghĩa).
      expect(ticksBeforeClose, greaterThan(0));

      controller.onClose();

      async.elapse(const Duration(seconds: 5));
      // Sau khi đóng, bộ đếm KHÔNG được tăng thêm — chứng minh `_clockTimer`
      // đã thực sự bị `cancel()`, không chỉ "không crash".
      expect(controller.clockTickCountForTest, ticksBeforeClose);
    });
  });

  test('onClose removes the RealtimeService listener — events after close no longer update runtimeState', () {
    fakeAsync((async) {
      final session = Get.put(SessionController());
      session.seedForTest(_activeSnapshot());

      final controller = HologramHubController();
      controller.onInit();
      async.elapse(const Duration(milliseconds: 500));

      // Trước khi đóng: một envelope "agent.tool_running" phải cập nhật
      // runtimeState (chứng minh listener đang thực sự lắng nghe).
      RealtimeService().acceptForTest(
        const RealtimeEnvelope(event: 'agent.tool_running', data: {'state': 'tool_running'}),
      );
      expect(controller.runtimeState.value, HologramRuntimeState.acting);

      controller.onClose();

      // Reset về idle thủ công để phân biệt rõ "không đổi vì listener đã gỡ"
      // với "không đổi vì tình cờ trùng giá trị cũ".
      controller.runtimeState.value = HologramRuntimeState.idle;

      RealtimeService().acceptForTest(
        const RealtimeEnvelope(event: 'agent.waiting_approval', data: {'state': 'waiting_approval'}),
      );
      async.elapse(const Duration(milliseconds: 500));

      // Sau khi đóng, listener đã bị `removeListener` — envelope mới KHÔNG
      // còn được xử lý, runtimeState phải giữ nguyên `idle`.
      expect(controller.runtimeState.value, HologramRuntimeState.idle);
    });
  });
}
