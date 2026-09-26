import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

import 'package:frontend/modules/chat/controllers/chat_controller.dart';
import 'package:frontend/modules/chat/models/chat_models.dart';
import 'package:frontend/modules/chat/models/data_access_declaration.dart';
import 'package:frontend/modules/chat/services/agent_chat_service.dart';

/// Service giả: trả run_id cố định và phát đúng các event SSE được đưa vào.
class _FakeChatService extends AgentChatService {
  _FakeChatService(this.events);

  final List<Map<String, dynamic>> events;

  @override
  Future<Map<String, dynamic>?> sendMessage(
    String conversationId, {
    required String projectId,
    required String content,
    required DataAccessDeclaration dataAccess,
    List<Map<String, dynamic>>? attachments,
    String? responseLocaleOverride,
  }) async => {'run_id': 'run-1'};

  @override
  Stream<Map<String, dynamic>> streamRunEvents(
    String runId, {
    int? sinceSequence,
    String? conversationId,
  }) => Stream.fromIterable(events);
}

Future<ChatMessage> _sendAndFail(Map<String, dynamic> failedPayload) async {
  final controller = ChatController(
    service: _FakeChatService([
      {'event_type': 'run.failed', 'sequence': 1, 'payload': failedPayload},
    ]),
  );
  controller.activeProjectId.value = 'proj-1';
  controller.activeConversation.value = ChatConversation.fromJson({
    'id': 'conv-1',
    'workspace_id': 'ws-1',
    'created_by_principal': 'user:1',
    'title': 'Chat',
    'created_at': '2026-09-26T00:00:00Z',
    'updated_at': '2026-09-26T00:00:00Z',
    'messages': const [],
  });
  controller.dataAccess.value = const DataAccessDeclaration(
    categories: {DataAccessCategory.nonPersonal},
  );
  controller.textController.text = 'hello';

  await controller.sendMessage();
  await Future<void>.delayed(Duration.zero);

  expect(controller.runStatus.value, 'failed');
  return controller.messages.last;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(Get.reset);
  tearDown(Get.reset);

  test('run.failed hiển thị user_message thay vì mã lỗi', () async {
    final msg = await _sendAndFail({
      'error': 'provider_insufficient_balance',
      'error_code': 'provider_insufficient_balance',
      'user_message': 'Nhà cung cấp model đã hết hạn mức.',
    });

    expect(msg.status, 'failed');
    expect(msg.content, contains('Nhà cung cấp model đã hết hạn mức.'));
    expect(msg.content, isNot(contains('provider_insufficient_balance')));
  });

  test('run.failed không có user_message thì lùi về error', () async {
    final msg = await _sendAndFail({'error': 'internal_error'});

    expect(msg.content, contains('internal_error'));
  });
}
