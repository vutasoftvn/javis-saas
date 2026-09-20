import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/services/okr_weekly_generator_service.dart';
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

  group('OkrWeeklyGeneratorService', () {
    test('calls POST /operations/objectives/:id/generate-weekly-cycle', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(
          request.url.path,
          '/operations/objectives/obj-1/generate-weekly-cycle',
        );
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['durationWeeks'], 6);
        return http.Response(
          jsonEncode({
            'success': true,
            'generatedPlans': 6,
          }),
          200,
        );
      });

      final result = await OkrWeeklyGeneratorService().generate('obj-1', 6);
      expect(result['success'], isTrue);
      expect(result['generatedPlans'], 6);
    });

    test('rejects durationWeeks outside 1..12 range', () async {
      expect(
        () => OkrWeeklyGeneratorService().generate('obj-1', 0),
        throwsArgumentError,
      );
      expect(
        () => OkrWeeklyGeneratorService().generate('obj-1', 13),
        throwsArgumentError,
      );
    });
  });
}
