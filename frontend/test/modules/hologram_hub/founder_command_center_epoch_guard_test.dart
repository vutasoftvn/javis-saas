// Fix (2026-09-02, epoch-guard) — reviewer độc lập phát hiện: trong
// `FounderCommandCenterController.sendChatMessage()`,
// `_cofounderConversationId ??= await createConversation()` không kiểm tra
// "workspace hiện tại còn giống lúc bắt đầu gửi hay không". Nếu Founder gửi
// tin nhắn rồi chuyển workspace NGAY TRƯỚC khi `createConversation` resolve,
// response trả về SAU khi `resetForWorkspace()` đã xoá state (đặt
// `_cofounderConversationId = null`) có thể gán ngược conversation-id CỦA
// WORKSPACE CŨ vào state workspace MỚI.
//
// Test dùng `Completer` để giữ request `POST /agent/conversations` "in-flight"
// thật sự, chuyển workspace trong lúc nó còn pending, rồi mới hoàn thành với
// dữ liệu cũ — chứng minh qua timing thật rằng conversation-id/state chat
// KHÔNG bị dữ liệu workspace CŨ ghi đè.
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
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';

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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  Get.testMode = true;

  late http.Client originalClient;
  late Completer<http.Response> pendingCreateConversation;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-a'});
    SecureStorageService.configureForTest(FakeSecretStore());
    AuthService.setCachedToken('fake-token-for-fcc-epoch-guard-test');
    pendingCreateConversation = Completer<http.Response>();
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
      // POST /agent/conversations — chỉ request này bị giữ "in-flight" tuỳ ý
      // qua Completer; mọi request khác (dashboard load, pulse, projects,
      // approvals...) trả 200 rỗng ngay lập tức.
      if (request.method == 'POST' &&
          request.url.path.contains('/agent/conversations')) {
        return pendingCreateConversation.future;
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

  test(
      'sendChatMessage() does not adopt a stale conversation id created for the OLD workspace after a switch mid-flight',
      () async {
    final session = Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final fcc = FounderCommandCenterController();
    // `loadDashboardData()` (chạy trong onInit) không liên quan tới test này
    // — chờ nó xong để không lẫn side-effect vào các assertion dưới.
    await Future<void>.delayed(const Duration(milliseconds: 10));

    // 1) Gửi tin nhắn cho workspace-a — `createConversation` sẽ "bay" cho
    //    tới khi ta tự complete Completer bên dưới.
    final sendFuture = fcc.sendChatMessage('hello from workspace-a');
    await Future<void>.delayed(Duration.zero);
    expect(
      fcc.cofounderConversationIdForTest,
      isNull,
      reason: 'chưa có response nào trả về, conversation id phải còn null',
    );

    // 2) Chuyển sang workspace-b TRONG LÚC createConversation còn pending.
    final generationBeforeSwitch = session.workspaceGeneration;
    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);
    expect(session.workspaceGeneration, greaterThan(generationBeforeSwitch));

    // `resetForWorkspace()` không tự động được gọi ở đây vì `fcc` không được
    // đăng ký permanent qua `Get.put` (hành vi đó đã có test riêng ở
    // `session_controller_shell_reset_test.dart`) — test này cô lập đúng
    // guard trong `sendChatMessage()`. Giả lập đúng hệ quả của
    // `resetForWorkspace()` mà `SessionController._commit` lẽ ra sẽ gây ra
    // cho state chat: conversation id của workspace mới phải là null (chưa
    // có conversation nào cho workspace-b).
    expect(fcc.cofounderConversationIdForTest, isNull);

    // 3) CHỈ BÂY GIỜ mới hoàn thành request tạo conversation, với id thuộc
    //    về workspace-a.
    pendingCreateConversation.complete(
      http.Response(jsonEncode({'id': 'conversation-workspace-a'}), 201),
    );
    await sendFuture;

    // 4) conversation id của workspace-a KHÔNG được rò rỉ vào state hiện tại
    //    (đã thuộc workspace-b).
    expect(
      fcc.cofounderConversationIdForTest,
      isNull,
      reason:
          'conversation-id tạo cho workspace CŨ không được gán vào state sau khi đã chuyển workspace',
    );
  });

  test(
      'sendChatMessage() still adopts the conversation id when no workspace switch happened (guard is not overly aggressive)',
      () async {
    Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final fcc = FounderCommandCenterController();
    await Future<void>.delayed(const Duration(milliseconds: 10));

    final sendFuture = fcc.sendChatMessage('hello, no switch happens');
    await Future<void>.delayed(Duration.zero);

    pendingCreateConversation.complete(
      http.Response(jsonEncode({'id': 'conversation-normal'}), 201),
    );
    await sendFuture;

    expect(fcc.cofounderConversationIdForTest, 'conversation-normal');
  });
}
