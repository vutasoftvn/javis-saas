// Task 6 — SSE / multipart / form transport phải đi qua CÙNG resolver, offline
// guard, token selector, và X-Workspace-Id header như các JSON method hiện có
// của ApiClient (get/post/...). Test cả các primitive dùng chung LẪN các caller
// thật (RealtimeService, VoiceService qua sendMultipart trực tiếp, VaultService,
// ChatService hub) để đảm bảo migration khỏi `Uri.parse(ApiClient.baseUrl)` không
// làm mất routing REMOTE_ACCESS / offline guard.
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/realtime_service.dart';
import 'package:frontend/modules/hologram_hub/services/chat_service.dart';
import 'package:frontend/modules/vault/services/vault_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({
      'local_session_token': 'LOCAL_SESSION',
      'platform_access_token': 'PLATFORM_ACCESS',
      'workspace_id': 'workspace-1',
    });
    ApiClient.setBaseUrl('http://company.local');
    ApiClient.setPlatformBaseUrl('http://platform.local');
    ApiClient.setRelayBaseUrl('http://gateway.local');
    ApiClient.clearRuntimeContext();
  });

  tearDown(() {
    ApiClient.client = realClient;
    ApiClient.clearRuntimeContext();
  });

  group('ApiClient.openSse', () {
    test('REMOTE_ACCESS ⇒ target /relay + local-session token + X-Workspace-Id', () async {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'ONLINE');
      http.Request? captured;
      ApiClient.client = MockClient((request) async {
        captured = request;
        return http.Response('', 200);
      });

      await ApiClient.openSse('/events/stream');

      expect(captured!.url.path, '/relay/events/stream');
      expect(captured!.headers['X-Workspace-Id'], 'workspace-1');
      expect(captured!.headers['Authorization'], 'Bearer LOCAL_SESSION');
      expect(captured!.headers['Accept'], 'text/event-stream');
    });

    test('REMOTE_ACCESS + OFFLINE ⇒ throws ApiOfflineException, KHÔNG gửi request', () async {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'OFFLINE');
      var sent = false;
      ApiClient.client = MockClient((request) async {
        sent = true;
        return http.Response('', 200);
      });

      await expectLater(
        () => ApiClient.openSse('/events/stream'),
        throwsA(isA<ApiOfflineException>()),
      );
      expect(sent, isFalse);
    });
  });

  group('ApiClient.sendMultipart', () {
    test('REMOTE_ACCESS ⇒ target /relay + local-session token + X-Workspace-Id', () async {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'ONLINE');
      http.Request? captured;
      ApiClient.client = MockClient((request) async {
        captured = request;
        return http.Response('{}', 200);
      });

      await ApiClient.sendMultipart(
        '/chat/transcribe-voice?workspace_id=workspace-1',
        fields: {'language': 'vi'},
        files: [http.MultipartFile.fromBytes('file', [1, 2, 3], filename: 'voice.m4a')],
      );

      expect(captured!.url.path, '/relay/chat/transcribe-voice');
      expect(captured!.headers['X-Workspace-Id'], 'workspace-1');
      expect(captured!.headers['Authorization'], 'Bearer LOCAL_SESSION');
    });

    test('REMOTE_ACCESS + OFFLINE ⇒ throws ApiOfflineException, KHÔNG gửi request', () async {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'OFFLINE');
      var sent = false;
      ApiClient.client = MockClient((request) async {
        sent = true;
        return http.Response('{}', 200);
      });

      await expectLater(
        () => ApiClient.sendMultipart('/chat/transcribe-voice', files: const []),
        throwsA(isA<ApiOfflineException>()),
      );
      expect(sent, isFalse);
    });
  });

  group('ApiClient.sendForm', () {
    test('REMOTE_ACCESS ⇒ target /relay + local-session token + X-Workspace-Id + form-encoded body', () async {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'ONLINE');
      http.Request? captured;
      ApiClient.client = MockClient((request) async {
        captured = request;
        return http.Response('{}', 200);
      });

      await ApiClient.sendForm(
        '/vault/documents/notes%2Fplan.md?workspace_id=workspace-1',
        {'content': 'hello', 'kind': 'wiki'},
      );

      expect(captured!.url.path, '/relay/vault/documents/notes%2Fplan.md');
      expect(captured!.headers['X-Workspace-Id'], 'workspace-1');
      expect(captured!.headers['Authorization'], 'Bearer LOCAL_SESSION');
      expect(captured!.headers['content-type'], contains('application/x-www-form-urlencoded'));
      expect(captured!.bodyFields['content'], 'hello');
    });

    test('REMOTE_ACCESS + OFFLINE ⇒ throws ApiOfflineException, KHÔNG gửi request', () async {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'OFFLINE');
      var sent = false;
      ApiClient.client = MockClient((request) async {
        sent = true;
        return http.Response('{}', 200);
      });

      await expectLater(
        () => ApiClient.sendForm('/vault/documents/x', {'content': 'a'}),
        throwsA(isA<ApiOfflineException>()),
      );
      expect(sent, isFalse);
    });
  });

  group('real callers migrated off Uri.parse(ApiClient.baseUrl)', () {
    test('RealtimeService SSE stream đi qua relay khi REMOTE_ACCESS', () async {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'ONLINE');
      http.Request? captured;
      ApiClient.client = MockClient((request) async {
        captured = request;
        return http.Response('', 200);
      });

      await RealtimeService().connect();
      RealtimeService().disconnect();

      expect(captured, isNotNull);
      expect(captured!.url.path, '/relay/events/stream');
      expect(captured!.headers['X-Workspace-Id'], 'workspace-1');
      expect(captured!.headers['Authorization'], 'Bearer LOCAL_SESSION');
    });

    test('VaultService.writeDocument đi qua relay + form-encoded khi REMOTE_ACCESS', () async {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'ONLINE');
      http.Request? captured;
      ApiClient.client = MockClient((request) async {
        captured = request;
        return http.Response('{}', 200);
      });

      await VaultService().writeDocument('notes/plan.md', 'hello world');

      expect(captured!.url.path, '/relay/vault/documents/notes%2Fplan.md');
      expect(captured!.url.queryParameters['workspace_id'], 'workspace-1');
      expect(captured!.headers['X-Workspace-Id'], 'workspace-1');
      expect(captured!.headers['Authorization'], 'Bearer LOCAL_SESSION');
      expect(captured!.bodyFields['content'], 'hello world');
    });

    test('VaultService.writeDocument KHÔNG gửi request khi REMOTE_ACCESS + OFFLINE', () async {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'OFFLINE');
      var sent = false;
      ApiClient.client = MockClient((request) async {
        sent = true;
        return http.Response('{}', 200);
      });

      await expectLater(
        () => VaultService().writeDocument('notes/plan.md', 'hello world'),
        throwsA(anything),
      );
      expect(sent, isFalse);
    });

    test('ChatService (hologram hub) sendUserMessage đi qua relay khi REMOTE_ACCESS', () async {
      ApiClient.setRuntimeContext(mode: 'REMOTE_ACCESS', presence: 'ONLINE');
      http.Request? captured;
      ApiClient.client = MockClient((request) async {
        captured = request;
        return http.Response(jsonEncode({'id': 'm1'}), 200);
      });

      await ChatService().sendUserMessage(
        sessionId: 'session-1',
        content: 'hi',
        clientMessageId: 'cmid-1',
      );

      expect(captured!.url.path, '/relay/chat/sessions/session-1/messages');
      expect(captured!.url.queryParameters['workspace_id'], 'workspace-1');
      expect(captured!.headers['X-Workspace-Id'], 'workspace-1');
      expect(captured!.headers['Authorization'], 'Bearer LOCAL_SESSION');
      expect(jsonDecode(captured!.body)['content'], 'hi');
    });
  });
}
