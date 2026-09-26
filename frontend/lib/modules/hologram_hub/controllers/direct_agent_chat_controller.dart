import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../chat/models/data_access_declaration.dart';
import '../../chat/services/agent_chat_service.dart';
import '../../tasks/services/task_service.dart';

enum DirectChatMessageState { sending, running, completed, failed }

class DirectChatMessage {
  DirectChatMessage({
    required this.localId,
    required this.isUser,
    required this.text,
    required this.state,
    this.error,
    this.runId,
    this.sourceMessageId,
    this.taskId,
  });

  final String localId;
  final bool isUser;
  String text;
  DirectChatMessageState state;
  String? error;

  /// Run durable của backend tạo ra câu trả lời này (chỉ có ở tin nhắn agent).
  final String? runId;

  /// Message id phía server của tin nhắn Founder đã sinh ra run — cùng Project và
  /// conversation, dùng làm khoá idempotency khi biến câu trả lời thành task.
  final String? sourceMessageId;

  /// Task id Company đã trả về; chỉ có sau khi tạo task thành công.
  String? taskId;
}

/// Chat trực tiếp với 1 specialist trong Project đang hoạt động, hoàn toàn qua API thật:
/// conversation Project-scoped -> message -> run durable -> SSE. Không bao giờ tự sinh
/// câu trả lời cục bộ; mọi lỗi được hiển thị là lỗi, không thành "kết quả agent".
class DirectAgentChatController extends ChangeNotifier {
  DirectAgentChatController({
    required this.projectId,
    required this.profileKey,
    required this.chatService,
    required this.taskService,
    Stream<Map<String, dynamic>> Function(String runId, {String? conversationId})? runEvents,
  }) : _runEvents = runEvents ?? chatService.streamRunEvents;

  final String? projectId;
  final String profileKey;
  final AgentChatService chatService;
  final TaskService taskService;
  final Stream<Map<String, dynamic>> Function(String runId, {String? conversationId}) _runEvents;

  final List<DirectChatMessage> messages = [];
  String? _conversationId;
  bool _busy = false;
  String? _errorMessage;
  int _localSeq = 0;
  StreamSubscription<Map<String, dynamic>>? _subscription;

  String? get conversationId => _conversationId;
  bool get isBusy => _busy;
  String? get errorMessage => _errorMessage;

  bool get hasProject => projectId != null && projectId!.trim().isNotEmpty;

  /// Lý do không thể chat (hiển thị recoverable error), null nếu sẵn sàng.
  String? get unavailableReason =>
      hasProject ? null : 'PROJECT_CONTEXT_REQUIRED: chọn một Project đang hoạt động trước khi chat với agent.';

  String _nextLocalId() => 'direct-chat-${_localSeq++}';

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }

  Future<void> send(String text, DataAccessDeclaration dataAccess) async {
    final content = text.trim();
    if (content.isEmpty || _busy) return;
    if (!hasProject) {
      _errorMessage = unavailableReason;
      notifyListeners();
      return;
    }
    if (!dataAccess.isValid) {
      _errorMessage = 'DATA_ACCESS_REQUIRED: khai báo loại dữ liệu trước khi gửi.';
      notifyListeners();
      return;
    }

    final userMessage = DirectChatMessage(
      localId: _nextLocalId(),
      isUser: true,
      text: content,
      state: DirectChatMessageState.sending,
    );
    messages.add(userMessage);
    _busy = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final conversation = _conversationId ??
          (await chatService.createConversation(
            projectId: projectId!,
            title: profileKey,
            activeAgentProfile: profileKey,
          ))
              ?.id;
      if (conversation == null || conversation.isEmpty) {
        throw AgentChatApiException('Conversation was not created');
      }
      _conversationId = conversation;

      final response = await chatService.sendMessage(
        conversation,
        projectId: projectId!,
        content: content,
        dataAccess: dataAccess,
      );
      final runId = response?['run_id']?.toString();
      if (runId == null || runId.isEmpty) {
        throw AgentChatApiException('Server did not return a run for this message');
      }
      userMessage.state = DirectChatMessageState.completed;

      final assistant = DirectChatMessage(
        localId: _nextLocalId(),
        isUser: false,
        text: '',
        state: DirectChatMessageState.running,
        runId: runId,
        sourceMessageId: response?['message_id']?.toString(),
      );
      messages.add(assistant);
      notifyListeners();
      await _followRun(runId, assistant);
    } catch (e) {
      // Không thêm tin nhắn agent nào: chỉ đánh dấu tin nhắn Founder thất bại + báo lỗi.
      if (userMessage.state == DirectChatMessageState.sending) {
        userMessage.state = DirectChatMessageState.failed;
      }
      userMessage.error = e.toString();
      _errorMessage = e.toString();
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  Future<void> _followRun(String runId, DirectChatMessage assistant) {
    final done = Completer<void>();

    void fail(String reason) {
      assistant.state = DirectChatMessageState.failed;
      assistant.error = reason;
      _errorMessage = reason;
      notifyListeners();
      if (!done.isCompleted) done.complete();
    }

    _subscription?.cancel();
    _subscription = _runEvents(runId, conversationId: _conversationId).listen(
      (event) {
        final type = event['event_type']?.toString() ?? '';
        final payload = (event['payload'] as Map?)?.cast<String, dynamic>() ?? const {};
        switch (type) {
          case 'message.delta':
            assistant.text += payload['delta']?.toString() ?? '';
            notifyListeners();
          case 'run.completed':
            if (assistant.text.isEmpty && payload['output'] != null) {
              assistant.text = payload['output'].toString();
            }
            assistant.state = DirectChatMessageState.completed;
            notifyListeners();
            if (!done.isCompleted) done.complete();
          case 'run.failed':
            // Ưu tiên thông điệp thân thiện từ backend; lùi về chuỗi lỗi thô nếu thiếu.
            fail(payload['user_message']?.toString() ?? payload['error']?.toString() ?? 'Run failed');
          case 'run.cancelled':
            fail('Run cancelled');
        }
      },
      onError: (Object err) => fail('Run stream error: $err'),
      onDone: () {
        if (!done.isCompleted) {
          fail('Run stream ended before the run finished');
        }
      },
      cancelOnError: true,
    );
    return done.future;
  }

  /// Tạo task Company từ 1 câu trả lời agent đã hoàn tất. Thành công chỉ khi Company trả
  /// task id; lỗi được ném lại và câu trả lời giữ nguyên để retry. Retry dùng cùng
  /// idempotency key (Project + conversation + message) nên không tạo task trùng.
  Future<String> createTaskFromResponse(
    DirectChatMessage message, {
    required String title,
  }) async {
    if (!hasProject) {
      throw StateError(unavailableReason!);
    }
    if (message.isUser || message.state != DirectChatMessageState.completed) {
      throw StateError('Chỉ tạo task từ câu trả lời agent đã hoàn tất.');
    }
    final conversation = _conversationId;
    final sourceMessage = message.sourceMessageId;
    if (conversation == null || sourceMessage == null || sourceMessage.isEmpty) {
      throw StateError('Câu trả lời thiếu định danh conversation/message để tạo task an toàn.');
    }
    final existing = message.taskId;
    if (existing != null) return existing;

    final key = 'hub-direct-chat-task:$projectId:$conversation:$sourceMessage';
    final task = await taskService.createTypedTask(
      title,
      projectId: projectId,
      idempotencyKey: key,
    );
    if (task.id.isEmpty) {
      throw StateError('Company did not return a task id');
    }
    message.taskId = task.id;
    notifyListeners();
    return task.id;
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }
}
