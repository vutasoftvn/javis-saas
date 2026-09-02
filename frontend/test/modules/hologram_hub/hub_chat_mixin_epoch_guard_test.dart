// Fix (2026-09-02, epoch-guard full audit) — `HubChatMixin.runQuickAction`/
// `executePrompt` gọi API rồi ghi thẳng nội dung trả về vào `mobileMessages`
// — MỘT RxList duy nhất tồn tại xuyên suốt vòng đời controller
// (`permanent: true`); `resetForWorkspace()` chỉ `.clear()` nó chứ không tạo
// mới. Nếu một request cho workspace CŨ đang bay lúc switch workspace,
// response về SAU có thể chèn nội dung của workspace CŨ vào transcript chat
// của workspace MỚI — rò rỉ nội dung chéo tenant thật, không chỉ "flicker".
//
// Test dùng `Completer` để giữ request "in-flight" thật sự, switch workspace
// giữa chừng, complete request cũ, rồi assert `mobileMessages` KHÔNG bị ghi
// đè — cộng test đối chứng (không switch vẫn ghi bình thường).
import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/core/session/session_context_service.dart';
import 'package:frontend/core/session/session_controller.dart';
import 'package:frontend/core/session/session_snapshot.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/dashboard/services/hub_service.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';
import 'package:frontend/modules/hologram_hub/services/chat_service.dart';

import '../../core/services/fakes/fake_secret_store.dart';

SessionSnapshot _snapshotFor(String workspaceId) => SessionSnapshot(
      userId: 'user-1',
      workspaceId: workspaceId,
      role: 'founder',
      runtime: const SessionRuntimeInfo(
        mode: 'LOCAL_ONLY',
        modeSource: 'inferred',
        presenceStatus: 'ONLINE',
        lastHeartbeatAt: null,
        asOf: null,
      ),
      capabilities: const ['workspace.session.read'],
    );

class _SucceedingContextService implements SessionContextService {
  @override
  Future<SessionSnapshot> fetch(String workspaceId) async =>
      _snapshotFor(workspaceId);
}

/// Fake `HubService` giữ `executeQuickAction()` in-flight tuỳ ý.
class _DelayedHubService extends HubService {
  _DelayedHubService(this._pending);
  final Completer<Map<String, dynamic>?> _pending;

  @override
  Future<Map<String, dynamic>?> executeQuickAction(String actionKey) =>
      _pending.future;
}

/// Fake `ChatService` cho phép kiểm soát chính xác thời điểm `createSession`/
/// `sendUserMessage` trả về, và `streamSession` không bao giờ emit gì (không
/// cần thiết cho các test guard boundary-await — guard chặn TRƯỚC khi kịp
/// subscribe stream).
class _DelayedChatService extends ChatService {
  _DelayedChatService({
    this.createSessionCompleter,
    this.sendUserMessageCompleter,
  });

  final Completer<Map<String, dynamic>?>? createSessionCompleter;
  final Completer<Map<String, dynamic>?>? sendUserMessageCompleter;

  @override
  Future<Map<String, dynamic>?> createSession({
    String title = 'New Chat',
    String? provider,
    String? model,
  }) {
    final completer = createSessionCompleter;
    if (completer != null) return completer.future;
    return Future.value({'id': 'sess-1'});
  }

  @override
  Future<Map<String, dynamic>?> sendUserMessage({
    required String sessionId,
    required String content,
    required String clientMessageId,
  }) {
    final completer = sendUserMessageCompleter;
    if (completer != null) return completer.future;
    return Future.value({'id': 'msg-1'});
  }

  @override
  Stream<Map<String, dynamic>> streamSession(
    String sessionId, {
    String? afterMessageId,
  }) =>
      const Stream.empty();
}

/// Fake `ChatService` cho test đối chứng (không switch workspace) — trả lời
/// tức thì cho `createSession`/`sendUserMessage` rồi phát một sự kiện
/// `delta` thật qua `streamSession` để chứng minh guard không chặn nhầm
/// luồng hợp lệ.
class _StreamingChatService extends ChatService {
  final _controller = StreamController<Map<String, dynamic>>();

  void emit(Map<String, dynamic> event) => _controller.add(event);

  @override
  Future<Map<String, dynamic>?> createSession({
    String title = 'New Chat',
    String? provider,
    String? model,
  }) async =>
      {'id': 'sess-1'};

  @override
  Future<Map<String, dynamic>?> sendUserMessage({
    required String sessionId,
    required String content,
    required String clientMessageId,
  }) async =>
      {'id': 'msg-1'};

  @override
  Stream<Map<String, dynamic>> streamSession(
    String sessionId, {
    String? afterMessageId,
  }) =>
      _controller.stream;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  Get.testMode = true;

  late http.Client originalClient;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-a'});
    SecureStorageService.configureForTest(FakeSecretStore());
    AuthService.setCachedToken('fake-token-for-epoch-guard-test');
    originalClient = ApiClient.client;
    ApiClient.client = MockClient((request) async {
      if (request.url.path.contains('/identity/me')) {
        return http.Response(
          jsonEncode({
            'id': 'user-1',
            'workspaceId': 'workspace-b',
            'role': 'founder',
          }),
          200,
        );
      }
      return http.Response('{}', 200);
    });
  });

  tearDown(() {
    ApiClient.client = originalClient;
    ApiClient.clearRuntimeContext();
    AuthService.setCachedToken(null);
    SecureStorageService.resetForTest();
    Get.reset();
  });

  Future<SessionController> putSwitchableSession() => Future.value(
        Get.put<SessionController>(
          SessionController(contextService: _SucceedingContextService()),
        ),
      );

  test(
      'runQuickAction() discards a stale in-flight response after workspace switch (generation guard)',
      () async {
    final session = await putSwitchableSession();
    final pendingOld = Completer<Map<String, dynamic>?>();
    final hub = HologramHubController(hubService: _DelayedHubService(pendingOld));

    final staleRun = hub.runQuickAction('daily_brief', 'Tổng quan hôm nay');
    await Future<void>.delayed(Duration.zero);
    final assistantIndex = hub.mobileMessages.length - 1;
    expect(hub.mobileMessages[assistantIndex]['status'], 'streaming');

    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);

    pendingOld.complete({
      'content_markdown': 'Kết quả workspace-a CŨ',
      'run_id': 'run-old',
    });
    await staleRun;

    // `hub` không được `Get.put` trong test này nên `resetForWorkspace()`
    // (chỉ chạy khi `Get.isRegistered<HologramHubController>()`) không tự
    // kích hoạt — điều đó tách biệt rõ: assertion dưới đây kiểm chứng ĐÚNG
    // cơ chế generation-guard (không ghi đè), không lẫn với side-effect của
    // `resetForWorkspace()`.
    expect(
      hub.mobileMessages[assistantIndex]['status'],
      'streaming',
      reason:
          'response trả về SAU khi workspace đã chuyển phải bị bỏ qua, không được ghi nội dung của workspace CŨ vào placeholder',
    );
    expect(hub.mobileMessages[assistantIndex]['text'], isNot('Kết quả workspace-a CŨ'));
  });

  test(
      'runQuickAction() still writes the response when the generation has NOT changed',
      () async {
    await putSwitchableSession();
    final pending = Completer<Map<String, dynamic>?>();
    final hub = HologramHubController(hubService: _DelayedHubService(pending));

    final run = hub.runQuickAction('daily_brief', 'Tổng quan hôm nay');
    await Future<void>.delayed(Duration.zero);
    final assistantIndex = hub.mobileMessages.length - 1;

    pending.complete({
      'content_markdown': 'Kết quả workspace-a mới',
      'run_id': 'run-new',
    });
    await run;

    expect(hub.mobileMessages[assistantIndex]['text'], 'Kết quả workspace-a mới');
    expect(hub.mobileMessages[assistantIndex]['status'], 'delivered');
  });

  test(
      'executePrompt() discards a stale in-flight createSession() response after workspace switch (generation guard)',
      () async {
    final session = await putSwitchableSession();
    final pendingCreateSession = Completer<Map<String, dynamic>?>();
    final hub = HologramHubController(
      chatService: _DelayedChatService(createSessionCompleter: pendingCreateSession),
    );

    final stalePrompt = hub.executePrompt('Câu hỏi cho workspace CŨ');
    await Future<void>.delayed(Duration.zero);
    expect(hub.mobileMessages, hasLength(2)); // user + placeholder assistant

    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);

    pendingCreateSession.complete({'id': 'sess-workspace-a'});
    await stalePrompt;

    // `hub` không `Get.put` nên `resetForWorkspace()` không tự chạy — kiểm
    // chứng riêng generation-guard: placeholder assistant vẫn y nguyên, KHÔNG
    // bị ghi đè bởi bất kỳ nội dung nào xuất phát từ session-id của
    // workspace CŨ.
    expect(hub.mobileMessages, hasLength(2));
    expect(
      hub.mobileMessages[1],
      {'role': 'assistant', 'text': '', 'status': 'streaming'},
      reason:
          'createSession() trả về SAU khi workspace đã chuyển phải bị bỏ qua — không được gán session-id của workspace CŨ hay ghi tiếp vào placeholder',
    );
  });

  test(
      'executePrompt() discards a stale in-flight sendUserMessage() response after workspace switch (generation guard)',
      () async {
    final session = await putSwitchableSession();
    final pendingSendUserMessage = Completer<Map<String, dynamic>?>();
    final hub = HologramHubController(
      chatService: _DelayedChatService(
        sendUserMessageCompleter: pendingSendUserMessage,
      ),
    );

    final stalePrompt = hub.executePrompt('Câu hỏi cho workspace CŨ');
    await Future<void>.delayed(Duration.zero);
    expect(hub.mobileMessages, hasLength(2));

    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);

    pendingSendUserMessage.complete({'id': 'msg-workspace-a'});
    await stalePrompt;

    expect(hub.mobileMessages, hasLength(2));
    expect(
      hub.mobileMessages[1],
      {'role': 'assistant', 'text': '', 'status': 'streaming'},
      reason:
          'response sendUserMessage() trễ của workspace CŨ không được mở stream/ghi nội dung vào placeholder của workspace MỚI',
    );
  });

  test(
      'executePrompt() still streams the response into mobileMessages when the generation has NOT changed',
      () async {
    await putSwitchableSession();
    final chatService = _StreamingChatService();
    final hub = HologramHubController(chatService: chatService);

    final promptFuture = hub.executePrompt('Câu hỏi hợp lệ');
    // Chờ tới khi session/sendUserMessage resolve và stream đã được subscribe.
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(Duration.zero);

    final assistantIndex = hub.mobileMessages.length - 1;
    chatService.emit({'type': 'delta', 'text': 'Xin chào'});
    await Future<void>.delayed(Duration.zero);

    expect(hub.mobileMessages[assistantIndex]['text'], 'Xin chào');
    expect(hub.mobileMessages[assistantIndex]['status'], 'streaming');

    await chatService._controller.close();
    await promptFuture;
  });
}
