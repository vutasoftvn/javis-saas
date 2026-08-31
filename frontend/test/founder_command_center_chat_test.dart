import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';

/// Regression test cho lỗi thật: `sendChatMessage` từng gọi `/cofounder/chat`
/// — một endpoint chưa từng tồn tại ở backend nào (luôn 404, xem
/// `docs`/hologram_hub investigation). Giờ nó phải đi qua đúng flow AgentOS
/// thật (`/agent/conversations` -> `/agent/conversations/{id}/messages` ->
/// SSE `/agent/runs/{id}/events`), giống module `chat` đang dùng.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({});

  late http.Client originalClient;
  setUp(() {
    originalClient = ApiClient.client;
  });
  tearDown(() {
    ApiClient.client = originalClient;
    Get.reset();
  });

  test('sendChatMessage tạo conversation, gửi message, và render câu trả lời stream về từ SSE', () async {
    ApiClient.client = MockClient((request) async {
      final path = request.url.path;
      if (path == '/agent/conversations' && request.method == 'POST') {
        return http.Response(
          '{"id":"conv_1","workspace_id":"ws1","created_by_principal":"p1",'
          '"title":"Founder Command Center","created_at":"2026-08-31T00:00:00Z",'
          '"updated_at":"2026-08-31T00:00:00Z"}',
          201,
        );
      }
      if (path == '/agent/conversations/conv_1/messages' && request.method == 'POST') {
        return http.Response('{"run_id":"run_1","status":"accepted"}', 202);
      }
      if (path == '/agent/runs/run_1/events') {
        return http.Response(
          'event: message.delta\n'
          'data: {"payload":{"delta":"Xin chao"}}\n\n'
          'event: run.completed\n'
          'data: {"payload":{"output":null}}\n\n',
          200,
          headers: {'content-type': 'text/event-stream'},
        );
      }
      return http.Response('not found', 404);
    });

    final controller = Get.put(FounderCommandCenterController());
    await controller.sendChatMessage('chào bạn');
    // Cho SSE stream chạy hết (nội dung tới trong 1 chunk, nhưng vẫn cần một
    // vòng event-loop để listener xử lý).
    await Future<void>.delayed(const Duration(milliseconds: 50));

    expect(controller.chatMessages.length, 2);
    expect(controller.chatMessages[0]['role'], 'user');
    expect(controller.chatMessages[1]['role'], 'cosa');
    expect(controller.chatMessages[1]['content'], 'Xin chao');
    expect(controller.isChatLoading.value, false);
  });

  test('sendChatMessage hiện lỗi thật khi backend trả về non-2xx, không hiện thành công giả', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('{"detail":"internal error"}', 500);
    });

    final controller = Get.put(FounderCommandCenterController());
    await controller.sendChatMessage('chào bạn');

    expect(controller.chatMessages.length, 2);
    expect(controller.chatMessages[0]['role'], 'user');
    expect(controller.chatMessages[1]['role'], 'error');
    expect(controller.isChatLoading.value, false);
  });
}
