import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/channels_service.dart';
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

  group('getChannelsConfig', () {
    test('returns the config payload on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/channels');
        return http.Response(jsonEncode({'telegram': {'is_enabled': false}}), 200);
      });

      final config = await ChannelsService().getChannelsConfig();

      expect(config['telegram']['is_enabled'], isFalse);
    });

    test('returns an error map when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      final config = await ChannelsService().getChannelsConfig();

      expect(config['status'], 'error');
    });

    test('parses the backend detail message on failure', () async {
      ApiClient.client = MockClient(
        (request) async => http.Response(
          jsonEncode({'detail': 'Token không hợp lệ'}),
          400,
          headers: {'content-type': 'application/json; charset=utf-8'},
        ),
      );

      final config = await ChannelsService().getChannelsConfig();

      expect(config, {'status': 'error', 'message': 'Token không hợp lệ'});
    });

    test('falls back to the raw body when the error response is not JSON', () async {
      ApiClient.client = MockClient((request) async => http.Response('Internal Server Error', 500));

      final config = await ChannelsService().getChannelsConfig();

      expect(config, {'status': 'error', 'message': 'Internal Server Error'});
    });
  });

  group('saveTelegramChannel', () {
    test('posts the token and enabled flag', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/channels/telegram/save');
        final body = jsonDecode(request.body);
        expect(body['is_enabled'], isTrue);
        expect(body['bot_token'], 'abc123');
        return http.Response(jsonEncode({'status': 'ok'}), 200);
      });

      final result = await ChannelsService().saveTelegramChannel(isEnabled: true, botToken: 'abc123');

      expect(result['status'], 'ok');
    });
  });

  group('testTelegramChannel', () {
    test('posts to the test endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/channels/telegram/test');
        return http.Response(jsonEncode({'status': 'ok'}), 200);
      });

      final result = await ChannelsService().testTelegramChannel();

      expect(result['status'], 'ok');
    });
  });

  group('saveZaloChannel / testZaloChannel', () {
    test('save posts to the zalo save endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/channels/zalo/save');
        return http.Response(jsonEncode({'status': 'ok'}), 200);
      });

      await ChannelsService().saveZaloChannel(isEnabled: true, botToken: 'zalo-token');
    });

    test('test posts to the zalo test endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/channels/zalo/test');
        return http.Response(jsonEncode({'status': 'ok'}), 200);
      });

      await ChannelsService().testZaloChannel();
    });
  });

  group('getChatbots', () {
    test('unwraps a top-level list response', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/channels/list');
        return http.Response(jsonEncode([
          {'id': 'bot-1'},
        ]), 200);
      });

      final bots = await ChannelsService().getChatbots();

      expect(bots, hasLength(1));
    });

    test('unwraps a {bots: [...]} map response', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(jsonEncode({
          'bots': [
            {'id': 'bot-1'},
          ],
        }), 200);
      });

      final bots = await ChannelsService().getChatbots();

      expect(bots, hasLength(1));
    });

    test('returns an empty list on failure', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final bots = await ChannelsService().getChatbots();

      expect(bots, isEmpty);
    });
  });
}
