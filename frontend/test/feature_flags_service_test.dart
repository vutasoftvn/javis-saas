import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/feature_flags_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': '123'});
  });

  tearDown(() => ApiClient.client = realClient);

  test('loads resolved flags for the current workspace', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.path, '/api/v1/platform/feature-flags');
      expect(request.url.queryParameters['workspace_id'], '123');
      return http.Response(jsonEncode({'flags': {'finance_function_v13': true}}), 200);
    });

    expect(await FeatureFlagsService().load(), {'finance_function_v13': true});
  });
}
