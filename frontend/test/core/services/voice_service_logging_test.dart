import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/core/services/voice_service.dart';
import 'package:frontend/modules/chat/services/agent_chat_service.dart';

/// Regression coverage cho hành vi "không log transcript/response body thô"
/// (Task 7). Khác với phiên bản trước — test này gọi thẳng
/// `VoiceService.uploadAndTranscribe` và `AgentChatService.getConversations`
/// (chính method sản xuất có debugPrint), bắt log thật qua override
/// `debugPrint`, rồi assert log không chứa nội dung nhạy cảm. Nếu ai đó
/// revert lại `debugPrint(... ${response.body} ...)` hay tương tự, test này
/// phải FAIL.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;
  final logs = <String>[];
  late DebugPrintCallback originalDebugPrint;

  setUp(() async {
    realClient = ApiClient.client;
    logs.clear();
    originalDebugPrint = debugPrint;
    debugPrint = (String? message, {int? wrapWidth}) {
      if (message != null) logs.add(message);
    };

    SharedPreferences.setMockInitialValues({});
    await SecureStorageService.write('auth_token', 'test-token');
    await SecureStorageService.write('local_session_token', 'test-local-token');
    await SecureStorageService.write('workspace_id', 'ws-test-voice');
  });

  tearDown(() {
    ApiClient.client = realClient;
    debugPrint = originalDebugPrint;
    ApiClient.clearRuntimeContext();
  });

  group('VoiceService.uploadAndTranscribe real log redaction', () {
    test('successful transcription never logs the transcript text itself', () async {
      const confidentialText = 'confidential transcript top secret strategy';

      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'transcript': confidentialText, 'confidence': 0.98}),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final transcript = await VoiceService().uploadAndTranscribe(
        [1, 2, 3],
        workspaceId: 'ws-test-voice',
      );

      // Method thực sự trả về transcript thật cho caller dùng...
      expect(transcript, equals(confidentialText));
      // ...nhưng KHÔNG được in nó ra log.
      expect(logs.join('\n'), isNot(contains(confidentialText)));
      expect(logs.join('\n'), isNot(contains('confidential transcript')));
    });

    test('failed transcription logs status code but never the response body', () async {
      const privatePayload = '{"error": "secret customer data leaked"}';

      ApiClient.client = MockClient((request) async {
        return http.Response(privatePayload, 500);
      });

      final transcript = await VoiceService().uploadAndTranscribe(
        [1, 2, 3],
        workspaceId: 'ws-test-voice',
      );

      expect(transcript, isNull);
      expect(logs.join('\n'), contains('500'));
      expect(logs.join('\n'), isNot(contains('secret customer data')));
    });
  });

  group('AgentChatService real log redaction', () {
    test('getConversations failure logs status code but never the response body', () async {
      const privateErrorPayload = '{"error": "secret customer data leaked"}';

      ApiClient.client = MockClient((request) async {
        return http.Response(privateErrorPayload, 500);
      });

      final service = AgentChatService();
      await expectLater(service.getConversations(), throwsA(isA<AgentChatApiException>()));

      expect(logs.join('\n'), contains('500'));
      expect(logs.join('\n'), isNot(contains('secret customer data')));
    });
  });
}
