import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/services/ai_service.dart';
import 'package:frontend/data/services/chat_service.dart';
import 'package:frontend/data/services/connectors_service.dart';
import 'package:frontend/core/services/voice_service.dart';
import 'package:frontend/modules/chat/controllers/chat_controller.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _FakeAiService implements AiService {
  @override
  Future<List<dynamic>> getModels() async => [
    {'provider': 'deepseek', 'model': 'deepseek-chat', 'label': 'DeepSeek Chat'},
    {'provider': 'openai', 'model': 'gpt-4o-mini', 'label': 'GPT-4o mini'},
  ];

  @override
  Future<Map<String, dynamic>?> getUsage() async => null;
}

class _FakeVoiceService implements IVoiceService {
  @override
  bool get isRecording => false;

  @override
  Future<bool> startRecording() async => false;

  @override
  Future<String?> stopRecordingAndTranscribe({String language = 'vi'}) async => null;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'workspace-1',
      'brain_id': 'brain-1',
      'auth_token': 'access-token',
    });
  });

  test('sends a user message to the brain-api chat endpoint', () async {
    final client = MockClient((request) async {
      expect(request.url.path, '/api/v1/chat/brain-1/sessions/session-1/messages');
      expect(request.url.queryParameters['workspace_id'], 'workspace-1');
      expect(request.method, 'POST');
      expect(request.headers['authorization'], 'Bearer access-token');
      expect(jsonDecode(request.body), {
        'role': 'user',
        'content': 'Xin chào',
        'client_message_id': 'client-message-1',
      });
      return http.Response(
        jsonEncode({
          'id': 'message-1',
          'role': 'user',
          'content': 'Xin chào',
          'status': 'sent',
          'client_message_id': 'client-message-1',
          'created_at': '2026-08-09T00:00:00Z',
        }),
        200,
      );
    });

    final result = await ChatService(client: client).sendUserMessage(
      sessionId: 'session-1',
      content: 'Xin chào',
      clientMessageId: 'client-message-1',
    );

    expect(result?['id'], 'message-1');
  });

  test('sends provider/model when creating a session', () async {
    final client = MockClient((request) async {
      expect(request.url.path, '/api/v1/chat/brain-1/sessions');
      expect(request.url.queryParameters['workspace_id'], 'workspace-1');
      expect(jsonDecode(request.body), {
        'title': 'New Chat',
        'provider': 'openai',
        'model': 'gpt-4o-mini',
      });
      return http.Response(
        jsonEncode({
          'id': 'session-1',
          'title': 'New Chat',
          'provider': 'openai',
          'model': 'gpt-4o-mini',
          'created_at': '2026-08-09T00:00:00Z',
        }),
        200,
      );
    });

    final result = await ChatService(
      client: client,
    ).createSession(provider: 'openai', model: 'gpt-4o-mini');

    expect(result?['provider'], 'openai');
  });

  test('cancels the in-progress reply of a session', () async {
    final client = MockClient((request) async {
      expect(request.url.path, '/api/v1/chat/brain-1/sessions/session-1/cancel');
      expect(request.url.queryParameters['workspace_id'], 'workspace-1');
      expect(request.method, 'POST');
      return http.Response(jsonEncode({'id': 'message-1', 'status': 'cancelled'}), 200);
    });

    final result = await ChatService(client: client).cancel('session-1');

    expect(result, isTrue);
  });

  test(
    'creates a backend session before posting the first user message',
    () async {
      final gateway = _FakeChatGateway();
      final controller = ChatController(chatService: gateway, voiceService: _FakeVoiceService());

      await controller.sendMessage('Tin nhắn đầu tiên');

      expect(gateway.createdSession, isTrue);
      expect(gateway.sentSessionId, 'session-1');
      expect(controller.currentSessionId.value, 'session-1');
      expect(controller.messages.single['content'], 'Tin nhắn đầu tiên');
    },
  );

  test('creates the new session with the picked model', () async {
    final gateway = _FakeChatGateway();
    final controller = ChatController(
      chatService: gateway,
      aiService: _FakeAiService(),
    );

    await controller.loadModels();
    controller.selectModel({
      'provider': 'openai',
      'model': 'gpt-4o-mini',
      'label': 'GPT-4o mini',
    });
    await controller.sendMessage('Xin chào');

    expect(gateway.lastProvider, 'openai');
    expect(gateway.lastModel, 'gpt-4o-mini');
  });

  test(
    'does not treat an earlier assistant message as the pending reply',
    () async {
      final gateway = _ExistingAssistantGateway();
      final controller = ChatController(
        chatService: gateway,
        connectorsService: _FakeConnectorsService(),
      );

      await controller.selectSession('session-1');
      await controller.sendMessage('Tin nhắn mới');
      await Future<void>.delayed(const Duration(milliseconds: 1100));

      expect(controller.isSending.value, isTrue);
      controller.onClose();
    },
  );

  test('defaults to a model whose provider actually has an API key', () async {
    final controller = ChatController(
      chatService: _FakeChatGateway(),
      aiService: _MixedKeyAiService(),
    );

    await controller.loadModels();

    // Lấy đại phần tử đầu danh sách sẽ chọn phải provider chưa có key, và mọi câu chat
    // trong session đó trả về "Không thể tạo phản hồi AI lúc này."
    expect(controller.selectedModel.value?['provider'], 'openrouter');
    expect(controller.selectedModel.value?['configured'], isTrue);
  });

  test('creates the session with the configured model by default', () async {
    final gateway = _FakeChatGateway();
    final controller = ChatController(
      chatService: gateway,
      aiService: _MixedKeyAiService(),
    );

    await controller.loadModels();
    await controller.sendMessage('Xin chào');

    expect(gateway.lastProvider, 'openrouter');
    expect(gateway.lastModel, 'deepseek/deepseek-chat');
  });

  test('lets the server pick the model when the picker has no data', () async {
    // Gửi đại 'deepseek/deepseek-chat' cứng trong app khi chưa tải được danh sách model
    // là cách chat hỏng trước đây: provider đó không có API key trên server, nên mọi câu
    // trả lời đều là lỗi. Không biết chọn gì thì để server dùng mặc định của nó.
    final gateway = _ServerDefaultGateway();
    final controller = ChatController(
      chatService: gateway,
      aiService: _EmptyAiService(),
    );

    await controller.loadModels();
    await controller.sendMessage('Xin chào');

    expect(gateway.lastProvider, isNull);
    expect(gateway.lastModel, isNull);
  });

  test('adopts the model the server actually used for the session', () async {
    final gateway = _ServerDefaultGateway();
    final controller = ChatController(
      chatService: gateway,
      aiService: _EmptyAiService(),
    );

    await controller.loadModels();
    await controller.sendMessage('Xin chào');

    // Header phải hiện model thật của đoạn chat, không giữ nhãn tạm - nhãn sai làm người
    // dùng tưởng đang chạy model khác với model thực sự trả lời.
    expect(controller.selectedModel.value?['provider'], 'openrouter');
    expect(controller.selectedModel.value?['model'], 'deepseek/deepseek-chat');
  });

  test('appends streamed deltas instead of replacing the reply', () async {
    final gateway = _DeltaStreamGateway();
    final controller = ChatController(chatService: gateway);

    await controller.sendMessage('Xin chào');
    await Future<void>.delayed(const Duration(milliseconds: 20));

    final reply = controller.messages.last;
    expect(reply['id'], 'assistant-1');
    expect(reply['content'], 'Xin chào bạn');
    expect(reply['status'], 'delivered');
    expect(controller.isSending.value, isFalse);
    controller.onClose();
  });

  test('asks the stream to follow the reply for the message just sent', () async {
    final gateway = _DeltaStreamGateway();
    final controller = ChatController(chatService: gateway);

    await controller.sendMessage('Xin chào');
    await Future<void>.delayed(const Duration(milliseconds: 20));

    // Không có mốc này, server sẽ bám vào câu trả lời đã xong của lượt trước.
    expect(gateway.lastAfterMessageId, 'message-1');
    controller.onClose();
  });

  test('parses delta events from the SSE stream', () async {
    final body =
        'event: message\n'
        'data: {"id":"assistant-1","role":"assistant","content":"","status":"streaming"}\n'
        '\n'
        'event: delta\n'
        'data: {"id":"assistant-1","text":"Xin "}\n'
        '\n'
        ': ping\n'
        '\n'
        'event: delta\n'
        'data: {"id":"assistant-1","text":"chào"}\n'
        '\n';

    late Uri requestedUri;
    final client = MockClient.streaming((request, bodyStream) async {
      requestedUri = request.url;
      return http.StreamedResponse(
        Stream.value(utf8.encode(body)),
        200,
        headers: {'content-type': 'text/event-stream'},
      );
    });

    final events = await ChatService(client: client)
        .streamSession('session-1', afterMessageId: 'message-1')
        .toList();

    expect(requestedUri.queryParameters['after_message_id'], 'message-1');
    expect(events.map((event) => event['type']).toList(), [
      'message',
      'delta',
      'delta',
    ]);
    expect(events[1]['text'], 'Xin ');
    expect(events[2]['text'], 'chào');
  });
}

class _DeltaStreamGateway extends _FakeChatGateway {
  String? lastAfterMessageId;

  @override
  Stream<Map<String, dynamic>> streamSession(
    String sessionId, {
    String? afterMessageId,
  }) {
    lastAfterMessageId = afterMessageId;
    return Stream.fromIterable([
      {
        'type': 'message',
        'id': 'assistant-1',
        'role': 'assistant',
        'content': '',
        'status': 'streaming',
      },
      {'type': 'delta', 'id': 'assistant-1', 'text': 'Xin chào'},
      {'type': 'delta', 'id': 'assistant-1', 'text': ' bạn'},
      {
        'type': 'message',
        'id': 'assistant-1',
        'role': 'assistant',
        'content': 'Xin chào bạn',
        'status': 'delivered',
      },
    ]);
  }
}

class _FakeChatGateway implements ChatGateway {
  bool createdSession = false;
  String? sentSessionId;
  String? lastProvider;
  String? lastModel;

  @override
  Future<Map<String, dynamic>?> createSession({
    String title = 'New Chat',
    String? provider,
    String? model,
  }) async {
    createdSession = true;
    lastProvider = provider;
    lastModel = model;
    return {
      'id': 'session-1',
      'title': title,
      'provider': provider,
      'model': model,
      'created_at': '2026-08-09T00:00:00Z',
    };
  }

  @override
  Future<List<dynamic>> getMessages(String sessionId) async => [];

  @override
  Future<List<dynamic>> getSessions() async => [];

  @override
  Future<bool> deleteSession(String sessionId) async => true;

  @override
  Future<Map<String, dynamic>?> sendUserMessage({
    required String sessionId,
    required String content,
    required String clientMessageId,
  }) async {
    sentSessionId = sessionId;
    return {
      'id': 'message-1',
      'role': 'user',
      'content': content,
      'status': 'sent',
      'client_message_id': clientMessageId,
      'created_at': '2026-08-09T00:00:00Z',
    };
  }

  @override
  Stream<Map<String, dynamic>> streamSession(
    String sessionId, {
    String? afterMessageId,
  }) => const Stream.empty();

  @override
  Future<bool> cancel(String sessionId) async => true;
}

class _ExistingAssistantGateway extends _FakeChatGateway {
  @override
  Future<List<dynamic>> getMessages(String sessionId) async => [
    {
      'id': 'old-user-message',
      'role': 'user',
      'content': 'Tin nhắn cũ',
      'status': 'sent',
      'created_at': '2026-08-08T00:00:00Z',
    },
    {
      'id': 'old-assistant-message',
      'role': 'assistant',
      'content': 'Phản hồi cũ',
      'status': 'delivered',
      'created_at': '2026-08-08T00:00:01Z',
    },
  ];
}

/// Server tự chọn provider/model khi client gửi lên null - đúng như create_chat_session
/// trong backend/app/modules/chat/router.py.
class _ServerDefaultGateway extends _FakeChatGateway {
  @override
  Future<Map<String, dynamic>?> createSession({
    String title = 'New Chat',
    String? provider,
    String? model,
  }) async {
    await super.createSession(title: title, provider: provider, model: model);
    return {
      'id': 'session-1',
      'title': title,
      'provider': provider ?? 'openrouter',
      'model': model ?? 'deepseek/deepseek-chat',
      'created_at': '2026-08-09T00:00:00Z',
    };
  }
}

/// getModels() trả rỗng khi workspace_id chưa kịp cache lúc app khởi động lại.
class _EmptyAiService implements AiService {
  @override
  Future<List<dynamic>> getModels() async => [];

  @override
  Future<Map<String, dynamic>?> getUsage() async => null;
}

class _MixedKeyAiService implements AiService {
  @override
  Future<List<dynamic>> getModels() async => [
    {'provider': 'deepseek', 'model': 'deepseek-chat', 'label': 'DeepSeek Chat', 'configured': false},
    {'provider': 'openrouter', 'model': 'deepseek/deepseek-chat', 'label': 'DeepSeek (OpenRouter)', 'configured': true},
  ];

  @override
  Future<Map<String, dynamic>?> getUsage() async => null;
}

class _FakeConnectorsService extends ConnectorsService {
  @override
  Future<List<dynamic>> getEmailApprovals({String? sessionId}) async => [];
}
