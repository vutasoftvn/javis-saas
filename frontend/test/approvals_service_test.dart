import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:get/get.dart';
import 'package:frontend/core/controllers/company_scope_controller.dart';
import 'package:frontend/modules/approvals/services/approvals_service.dart';
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

  group('getApprovals', () {
    test('appends the status filter when provided', () async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path.contains('/agent-platform/approvals')) {
          return http.Response('not found', 404);
        }
        if (request.url.path.contains('/workforce/approvals')) {
          expect(request.url.query, 'status=pending');
          return http.Response(jsonEncode({'approvals': []}), 200);
        }
        expect(request.url.query, 'workspace_id=workspace-1&status=pending');
        return http.Response(jsonEncode({'approvals': []}), 200);
      });

      await ApprovalsService().getApprovals(status: 'pending');
    });

    test('returns an empty list when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        return http.Response('not found', 404);
      });

      final approvals = await ApprovalsService().getApprovals();

      expect(approvals, isEmpty);
    });

    test('forwards scope parameters when present', () async {
      final scope = Get.find<CompanyScopeController>();
      scope.setScope(operatingUnitId: 201, offeringId: 301, initiativeId: 401);

      ApiClient.client = MockClient((request) async {
        if (request.url.path.contains('/agent-platform/approvals') || request.url.path.contains('/workforce/approvals')) {
          expect(request.url.queryParameters['operating_unit_id'], '201');
          expect(request.url.queryParameters['offering_id'], '301');
          expect(request.url.queryParameters['initiative_id'], '401');
          return http.Response(jsonEncode({'approvals': []}), 200);
        }
        return http.Response('not found', 404);
      });

      await ApprovalsService().getApprovals();
    });
  });

  group('approveStep', () {
    test('returns true on 200', () async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path.contains('/agent-platform/approvals')) {
          return http.Response('not found', 404);
        }
        if (request.url.path.contains('/workforce/approvals')) {
          expect(request.url.path, '/api/v1/workforce/approvals/step-1/approve');
          return http.Response('{}', 200);
        }
        expect(request.url.path, '/api/v1/workflows/steps/step-1/approve');
        return http.Response('{}', 200);
      });

      final ok = await ApprovalsService().approveStep('step-1');

      expect(ok, isTrue);
    });

    test('returns false on a non-200 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('bad request', 400));

      final ok = await ApprovalsService().approveStep('step-1');

      expect(ok, isFalse);
    });
  });

  group('rejectStep', () {
    test('returns true on 200', () async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path.contains('/agent-platform/approvals')) {
          return http.Response('not found', 404);
        }
        if (request.url.path.contains('/workforce/approvals')) {
          expect(request.url.path, '/api/v1/workforce/approvals/step-1/reject');
          return http.Response('{}', 200);
        }
        expect(request.url.path, '/api/v1/workflows/steps/step-1/reject');
        return http.Response('{}', 200);
      });

      final ok = await ApprovalsService().rejectStep('step-1');

      expect(ok, isTrue);
    });
  });
}
