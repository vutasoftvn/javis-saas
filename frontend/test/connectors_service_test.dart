import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/settings/services/connectors_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('getConnectors', () {
    test('returns the connectors list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/connectors/');
        return http.Response(
          jsonEncode({
            'connectors': [
              {'id': 'conn-1'},
            ],
          }),
          200,
        );
      });

      final connectors = await ConnectorsService().getConnectors();

      expect(connectors, hasLength(1));
    });
  });

  group('createConnector', () {
    test('posts name and config and returns the created connector', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['name'], 'slack');
        expect(body['config_jsonb'], {'token': 'x'});
        return http.Response(jsonEncode({'id': 'conn-2'}), 201);
      });

      final connector = await ConnectorsService().createConnector('slack', {'token': 'x'});

      expect(connector?['id'], 'conn-2');
    });
  });

  group('deleteConnector', () {
    test('returns true on 200', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        return http.Response('{}', 200);
      });

      final ok = await ConnectorsService().deleteConnector('conn-1');

      expect(ok, isTrue);
    });
  });

  group('getGoogleStatus', () {
    test('returns the status payload on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/connectors/google/status');
        return http.Response(jsonEncode({'connected': false, 'needs_reconnect': true}), 200);
      });

      final status = await ConnectorsService().getGoogleStatus();

      expect(status?['needs_reconnect'], isTrue);
    });
  });

  group('startGoogleOAuth', () {
    test('returns the authorize URL on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['login_hint'], 'a@b.com');
        return http.Response(jsonEncode({'authorize_url': 'https://accounts.google.com/x'}), 200);
      });

      final url = await ConnectorsService().startGoogleOAuth(loginHint: 'a@b.com');

      expect(url, 'https://accounts.google.com/x');
    });

    test('throws with the backend detail message on failure', () async {
      ApiClient.client = MockClient(
        (request) async => http.Response(
          jsonEncode({'detail': 'OAuth chưa cấu hình'}),
          400,
          headers: {'content-type': 'application/json; charset=utf-8'},
        ),
      );

      expect(
        () => ConnectorsService().startGoogleOAuth(),
        throwsA(isA<Exception>().having((e) => e.toString(), 'message', contains('OAuth chưa cấu hình'))),
      );
    });
  });

  group('getEmailApprovals', () {
    test('scopes by sessionId when provided', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['session_id'], 'sess-1');
        return http.Response(jsonEncode({'approvals': []}), 200);
      });

      await ConnectorsService().getEmailApprovals(sessionId: 'sess-1');
    });
  });

  group('decideEmailApproval', () {
    test('posts to the approve action and returns null on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/connectors/email-approvals/appr-1/approve');
        return http.Response('{}', 200);
      });

      final error = await ConnectorsService().decideEmailApproval('appr-1', approve: true);

      expect(error, isNull);
    });

    test('posts to the reject action on approve:false', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/connectors/email-approvals/appr-1/reject');
        return http.Response('{}', 200);
      });

      await ConnectorsService().decideEmailApproval('appr-1', approve: false);
    });

    test('returns the backend detail message on failure', () async {
      ApiClient.client = MockClient(
        (request) async => http.Response(
          jsonEncode({'detail': 'Đã được duyệt trước đó'}),
          409,
          headers: {'content-type': 'application/json; charset=utf-8'},
        ),
      );

      final error = await ConnectorsService().decideEmailApproval('appr-1', approve: true);

      expect(error, 'Đã được duyệt trước đó');
    });
  });

  group('Zalo QR flow', () {
    test('startZaloQr returns the session payload on 202', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/connectors/zalo/sessions');
        return http.Response(jsonEncode({'id': 'qr-1', 'status': 'pending'}), 202);
      });

      final session = await ConnectorsService().startZaloQr();

      expect(session?['id'], 'qr-1');
    });

    test('getZaloQrStatus returns the status payload', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/connectors/zalo/sessions/qr-1');
        return http.Response(jsonEncode({'status': 'confirmed'}), 200);
      });

      final status = await ConnectorsService().getZaloQrStatus('qr-1');

      expect(status?['status'], 'confirmed');
    });

    test('cancelZaloQr returns true on 200', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/connectors/zalo/sessions/qr-1/cancel');
        return http.Response('{}', 200);
      });

      final ok = await ConnectorsService().cancelZaloQr('qr-1');

      expect(ok, isTrue);
    });
  });
}
