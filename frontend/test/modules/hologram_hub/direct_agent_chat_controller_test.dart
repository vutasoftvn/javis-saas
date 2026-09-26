import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/task_kanban_model.dart';
import 'package:frontend/modules/chat/models/chat_models.dart';
import 'package:frontend/modules/chat/models/data_access_declaration.dart';
import 'package:frontend/modules/chat/services/agent_chat_service.dart';
import 'package:frontend/modules/hologram_hub/controllers/direct_agent_chat_controller.dart';
import 'package:frontend/modules/tasks/services/task_service.dart';

class _FakeChatService extends AgentChatService {
  final List<Map<String, dynamic>> createCalls = [];
  final List<Map<String, dynamic>> sendCalls = [];
  Object? createError;
  Object? sendError;

  @override
  Future<ChatConversation?> createConversation({
    required String projectId,
    String? title,
    String? activeAgentProfile,
  }) async {
    createCalls.add({
      'project_id': projectId,
      'active_agent_profile': activeAgentProfile,
    });
    if (createError != null) throw createError!;
    return ChatConversation(
      id: 'conv-1',
      workspaceId: 'ws-1',
      projectId: projectId,
      createdByPrincipal: 'u1',
      title: title ?? '',
      activeAgentProfile: activeAgentProfile,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
      messages: [],
    );
  }

  @override
  Future<Map<String, dynamic>?> sendMessage(
    String conversationId, {
    required String projectId,
    required String content,
    required DataAccessDeclaration dataAccess,
    List<Map<String, dynamic>>? attachments,
    String? responseLocaleOverride,
  }) async {
    sendCalls.add({
      'conversation_id': conversationId,
      'project_id': projectId,
      'content': content,
      'data_access': dataAccess.toJson(),
    });
    if (sendError != null) throw sendError!;
    return {'run_id': 'run-1', 'message_id': 'msg-1', 'status': 'RUNNING'};
  }
}

class _FakeTaskService extends TaskService {
  final List<Map<String, dynamic>> calls = [];
  Object? error;

  @override
  Future<TaskKanbanModel> createTypedTask(
    String title, {
    TaskKanbanStatus status = TaskKanbanStatus.todo,
    String? priority = 'medium',
    String? dueAt,
    dynamic assigneeMemberId,
    String? executionMode,
    String? function,
    String? projectId,
    String? weeklyCommitmentId,
    String? idempotencyKey,
  }) async {
    calls.add({
      'title': title,
      'projectId': projectId,
      'idempotencyKey': idempotencyKey,
    });
    if (error != null) throw error!;
    return TaskKanbanModel(id: 'task-1', title: title, projectId: projectId);
  }
}

const _declaration = DataAccessDeclaration(
  categories: {DataAccessCategory.nonPersonal},
);

Map<String, dynamic> _delta(String text) => {
      'event_type': 'message.delta',
      'payload': {'delta': text},
    };

Map<String, dynamic> _completed() => {
      'event_type': 'run.completed',
      'payload': <String, dynamic>{},
    };

DirectAgentChatController _controller({
  required _FakeChatService chat,
  required _FakeTaskService tasks,
  String? projectId = 'proj-1',
  Stream<Map<String, dynamic>> Function(String, {String? conversationId})? events,
}) {
  return DirectAgentChatController(
    projectId: projectId,
    profileKey: 'finance',
    chatService: chat,
    taskService: tasks,
    runEvents: events ?? (_, {conversationId}) => Stream.fromIterable([_delta('Runway 10 tháng.'), _completed()]),
  );
}

void main() {
  test('creates a Project-scoped conversation for the profile and sends data_access', () async {
    final chat = _FakeChatService();
    final controller = _controller(chat: chat, tasks: _FakeTaskService());

    await controller.send('Runway còn bao lâu?', _declaration);

    expect(chat.createCalls, [
      {'project_id': 'proj-1', 'active_agent_profile': 'finance'},
    ]);
    expect(chat.sendCalls.single['project_id'], 'proj-1');
    expect(chat.sendCalls.single['conversation_id'], 'conv-1');
    expect(chat.sendCalls.single['data_access'], {
      'categories': ['NON_PERSONAL'],
      'subject_reference': null,
    });
    final assistant = controller.messages.last;
    expect(assistant.isUser, isFalse);
    expect(assistant.text, 'Runway 10 tháng.');
    expect(assistant.state, DirectChatMessageState.completed);
    expect(assistant.runId, 'run-1');
  });

  test('reuses the conversation for a second message', () async {
    final chat = _FakeChatService();
    final controller = _controller(chat: chat, tasks: _FakeTaskService());

    await controller.send('một', _declaration);
    await controller.send('hai', _declaration);

    expect(chat.createCalls, hasLength(1));
    expect(chat.sendCalls, hasLength(2));
  });

  test('network failure leaves no assistant response and reports the error', () async {
    final chat = _FakeChatService()..sendError = AgentChatApiException('boom', statusCode: 500);
    final controller = _controller(chat: chat, tasks: _FakeTaskService());

    await controller.send('Runway?', _declaration);

    expect(controller.messages.where((m) => !m.isUser), isEmpty);
    expect(controller.messages.single.state, DirectChatMessageState.failed);
    expect(controller.errorMessage, contains('boom'));
  });

  test('a run that ends without a terminal event is a failure, not a fabricated answer', () async {
    final controller = _controller(
      chat: _FakeChatService(),
      tasks: _FakeTaskService(),
      events: (_, {conversationId}) => const Stream.empty(),
    );

    await controller.send('Runway?', _declaration);

    final assistant = controller.messages.last;
    expect(assistant.state, DirectChatMessageState.failed);
    expect(assistant.text, isEmpty);
    expect(controller.errorMessage, isNotNull);
  });

  test('a failed run surfaces the server error only', () async {
    final controller = _controller(
      chat: _FakeChatService(),
      tasks: _FakeTaskService(),
      events: (_, {conversationId}) => Stream.value({
        'event_type': 'run.failed',
        'payload': {'error': 'compliance_denied'},
      }),
    );

    await controller.send('Runway?', _declaration);

    final assistant = controller.messages.last;
    expect(assistant.state, DirectChatMessageState.failed);
    expect(assistant.text, isEmpty);
    expect(assistant.error, 'compliance_denied');
  });

  test('run.failed hiển thị user_message thay vì chuỗi thô', () async {
    final controller = _controller(
      chat: _FakeChatService(),
      tasks: _FakeTaskService(),
      events: (_, {conversationId}) => Stream.value({
        'event_type': 'run.failed',
        'payload': {'error': 'litellm.BadRequestError raw', 'user_message': 'Hết hạn mức nhà cung cấp.'},
      }),
    );

    await controller.send('hi', _declaration);

    expect(controller.errorMessage, 'Hết hạn mức nhà cung cấp.');
    expect(controller.messages.last.error, 'Hết hạn mức nhà cung cấp.');
  });

  test('mở SSE kèm conversationId của cuộc trò chuyện', () async {
    String? seen;
    final controller = _controller(
      chat: _FakeChatService(),
      tasks: _FakeTaskService(),
      events: (runId, {conversationId}) {
        seen = conversationId;
        return Stream.fromIterable([_delta('ok'), _completed()]);
      },
    );

    await controller.send('hi', _declaration);

    expect(seen, isNotNull);
    expect(seen, controller.conversationId);
  });

  test('missing Project sends nothing and shows a recoverable error', () async {
    final chat = _FakeChatService();
    final controller = _controller(chat: chat, tasks: _FakeTaskService(), projectId: null);

    await controller.send('Runway?', _declaration);

    expect(chat.createCalls, isEmpty);
    expect(chat.sendCalls, isEmpty);
    expect(controller.messages, isEmpty);
    expect(controller.errorMessage, contains('PROJECT_CONTEXT_REQUIRED'));
  });

  test('an invalid data access declaration sends nothing', () async {
    final chat = _FakeChatService();
    final controller = _controller(chat: chat, tasks: _FakeTaskService());

    await controller.send('Runway?', const DataAccessDeclaration());

    expect(chat.sendCalls, isEmpty);
    expect(controller.errorMessage, contains('DATA_ACCESS_REQUIRED'));
  });

  group('createTaskFromResponse', () {
    Future<(DirectAgentChatController, DirectChatMessage, _FakeTaskService)> completed() async {
      final tasks = _FakeTaskService();
      final controller = _controller(chat: _FakeChatService(), tasks: tasks);
      await controller.send('Runway?', _declaration);
      return (controller, controller.messages.last, tasks);
    }

    test('returns the persisted task id and sends Project + stable idempotency key', () async {
      final (controller, message, tasks) = await completed();

      final id = await controller.createTaskFromResponse(message, title: 'Cắt chi phí');

      expect(id, 'task-1');
      expect(message.taskId, 'task-1');
      expect(tasks.calls.single, {
        'title': 'Cắt chi phí',
        'projectId': 'proj-1',
        'idempotencyKey': 'hub-direct-chat-task:proj-1:conv-1:msg-1',
      });
    });

    test('failure keeps the response and a retry reuses the same idempotency key', () async {
      final (controller, message, tasks) = await completed();
      tasks.error = StateError('company down');

      await expectLater(
        controller.createTaskFromResponse(message, title: 'T'),
        throwsA(isA<StateError>()),
      );
      expect(message.taskId, isNull);
      expect(message.text, 'Runway 10 tháng.');

      tasks.error = null;
      await controller.createTaskFromResponse(message, title: 'T');

      expect(tasks.calls, hasLength(2));
      expect(tasks.calls[0]['idempotencyKey'], tasks.calls[1]['idempotencyKey']);
      expect(message.taskId, 'task-1');
    });

    test('an already created task is not created twice', () async {
      final (controller, message, tasks) = await completed();

      await controller.createTaskFromResponse(message, title: 'T');
      await controller.createTaskFromResponse(message, title: 'T');

      expect(tasks.calls, hasLength(1));
    });

    test('without a Project it refuses without calling Company', () async {
      final tasks = _FakeTaskService();
      final controller = _controller(chat: _FakeChatService(), tasks: tasks, projectId: null);
      final message = DirectChatMessage(
        localId: 'x',
        isUser: false,
        text: 'a',
        state: DirectChatMessageState.completed,
        sourceMessageId: 'm',
      );

      await expectLater(
        controller.createTaskFromResponse(message, title: 'T'),
        throwsA(isA<StateError>()),
      );
      expect(tasks.calls, isEmpty);
    });

    test('a failed response cannot become a task', () async {
      final tasks = _FakeTaskService();
      final controller = _controller(chat: _FakeChatService(), tasks: tasks);
      final message = DirectChatMessage(
        localId: 'x',
        isUser: false,
        text: '',
        state: DirectChatMessageState.failed,
      );

      await expectLater(
        controller.createTaskFromResponse(message, title: 'T'),
        throwsA(isA<StateError>()),
      );
      expect(tasks.calls, isEmpty);
    });
  });
}
