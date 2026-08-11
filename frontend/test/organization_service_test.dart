import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/organization_service.dart';
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

  group('getOrgOverview', () {
    test('returns the overview payload on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/org/workspace-1');
        return http.Response(jsonEncode({'name': 'COSA Global'}), 200);
      });

      final overview = await OrganizationService().getOrgOverview();

      expect(overview?['name'], 'COSA Global');
    });

    test('returns null when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      final overview = await OrganizationService().getOrgOverview();

      expect(overview, isNull);
    });
  });

  group('getOrgChart', () {
    test('returns the chart payload on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/org/workspace-1/chart');
        return http.Response(jsonEncode({'departments': []}), 200);
      });

      final chart = await OrganizationService().getOrgChart();

      expect(chart?['departments'], isEmpty);
    });
  });

  group('getCommandCenter', () {
    test('returns the command center payload on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/org/workspace-1/command-center');
        return http.Response(jsonEncode({}), 200);
      });

      final data = await OrganizationService().getCommandCenter();

      expect(data, isNotNull);
    });
  });

  group('getDailyBriefing', () {
    test('returns the briefing payload on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/org/workspace-1/daily-briefing');
        return http.Response(jsonEncode({}), 200);
      });

      final data = await OrganizationService().getDailyBriefing();

      expect(data, isNotNull);
    });
  });

  group('hireAIEmployee', () {
    test('posts the hire payload and returns the created employee on 201', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/org/workspace-1/hire-ai');
        final body = jsonDecode(request.body);
        expect(body['role_title'], 'Marketing Lead');
        return http.Response(jsonEncode({'id': 'emp-1'}), 201);
      });

      final employee = await OrganizationService().hireAIEmployee({'role_title': 'Marketing Lead'});

      expect(employee?['id'], 'emp-1');
    });

    test('returns null when the backend does not return 201', () async {
      ApiClient.client = MockClient((request) async => http.Response('bad request', 400));

      final employee = await OrganizationService().hireAIEmployee({'role_title': 'x'});

      expect(employee, isNull);
    });
  });
}
