import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:get/get.dart';
import 'package:frontend/core/controllers/company_scope_controller.dart';
import 'package:frontend/modules/workflows/services/workflows_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    Get.reset();
    Get.put(CompanyScopeController());
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('getDefinitions', () {
    test('returns the definitions list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/workflows/definitions');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({
            'definitions': [
              {'id': 'def-1', 'name': 'Onboarding'},
            ],
          }),
          200,
        );
      });

      final defs = await WorkflowsService().getDefinitions();

      expect(defs, hasLength(1));
      expect(defs.first['name'], 'Onboarding');
    });

    test('returns an empty list when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      final defs = await WorkflowsService().getDefinitions();

      expect(defs, isEmpty);
    });

    test('forwards scope parameters when present', () async {
      SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
      final scope = Get.find<CompanyScopeController>();
      scope.setScope(operatingUnitId: 201, offeringId: 301, initiativeId: 401);

      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['operating_unit_id'], '201');
        expect(request.url.queryParameters['offering_id'], '301');
        expect(request.url.queryParameters['initiative_id'], '401');
        return http.Response(jsonEncode({'definitions': []}), 200);
      });

      await WorkflowsService().getDefinitions();
    });
  });

  group('getRuns', () {
    test('forwards limit and offset as query params', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['limit'], '10');
        expect(request.url.queryParameters['offset'], '20');
        return http.Response(jsonEncode({'runs': []}), 200);
      });

      await WorkflowsService().getRuns(limit: 10, offset: 20);
    });

    test('forwards scope parameters when present', () async {
      final scope = Get.find<CompanyScopeController>();
      scope.setScope(operatingUnitId: 201, offeringId: 301, initiativeId: 401);

      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['operating_unit_id'], '201');
        expect(request.url.queryParameters['offering_id'], '301');
        expect(request.url.queryParameters['initiative_id'], '401');
        return http.Response(jsonEncode({'runs': []}), 200);
      });

      await WorkflowsService().getRuns(limit: 10, offset: 20);
    });
  });

  group('triggerRun', () {
    test('posts the input payload and returns the created run on 201', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/workflows/definitions/def-1/run');
        expect(jsonDecode(request.body), {
          'input_jsonb': {'foo': 'bar'},
        });
        return http.Response(jsonEncode({'id': 'run-1', 'status': 'running'}), 201);
      });

      final run = await WorkflowsService().triggerRun('def-1', input: {'foo': 'bar'});

      expect(run?['id'], 'run-1');
    });

    test('returns null when the backend does not return 201', () async {
      ApiClient.client = MockClient((request) async => http.Response('bad request', 400));

      final run = await WorkflowsService().triggerRun('def-1');

      expect(run, isNull);
    });
  });

  group('getRunDetails', () {
    test('returns the run detail on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/workflows/runs/run-1');
        return http.Response(jsonEncode({'id': 'run-1', 'status': 'completed'}), 200);
      });

      final run = await WorkflowsService().getRunDetails('run-1');

      expect(run?['status'], 'completed');
    });

    test('returns null on a non-200 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('not found', 404));

      final run = await WorkflowsService().getRunDetails('missing');

      expect(run, isNull);
    });
  });
}
