import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/plugins_service.dart';
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

  group('getPlugins', () {
    test('returns the plugins list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/plugins/');
        return http.Response(
          jsonEncode({
            'plugins': [
              {'id': 'plugin-1', 'slug': 'gmail'},
            ],
          }),
          200,
        );
      });

      final plugins = await PluginsService().getPlugins();

      expect(plugins, hasLength(1));
    });

    test('returns an empty list when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      final plugins = await PluginsService().getPlugins();

      expect(plugins, isEmpty);
    });
  });

  group('enablePlugin', () {
    test('returns true on 200', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/plugins/workspace-plugins/plugin-1/enable');
        return http.Response('{}', 200);
      });

      final ok = await PluginsService().enablePlugin('plugin-1');

      expect(ok, isTrue);
    });

    test('returns false when the caller lacks the owner role', () async {
      ApiClient.client = MockClient((request) async => http.Response('forbidden', 403));

      final ok = await PluginsService().enablePlugin('plugin-1');

      expect(ok, isFalse);
    });
  });

  group('disablePlugin', () {
    test('returns true on 200', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/plugins/workspace-plugins/plugin-1/disable');
        return http.Response('{}', 200);
      });

      final ok = await PluginsService().disablePlugin('plugin-1');

      expect(ok, isTrue);
    });
  });
}
