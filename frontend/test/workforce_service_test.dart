import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/agents/models/workforce_models.dart';
import 'package:frontend/modules/agents/services/workforce_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'ws_1001',
    });
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('workforce 503 is unavailable, not empty roster', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({'code': 'unavailable', 'message': 'Service temporarily unavailable'}),
        503,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = WorkforceService(client: requestClient);

    final result = await service.listAssignments();
    expect(result, isA<ApiFailure<List<WorkforceAssignment>>>());
    expect((result as ApiFailure<List<WorkforceAssignment>>).failure.code, ApiFailureCode.unavailable);
  });

  test('empty assignment response returns ApiSuccess with empty dataState', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': [],
          'meta': {
            'dataState': 'empty',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'agent_db', 'ref': 'agent.workforce_assignments'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = WorkforceService(client: requestClient);

    final result = await service.listAssignments();
    expect(result, isA<ApiSuccess<List<WorkforceAssignment>>>());
    final success = result as ApiSuccess<List<WorkforceAssignment>>;
    expect(success.data, isEmpty);
    expect(success.meta.dataState, ApiDataState.empty);
    expect(success.meta.sources.first.kind, 'agent_db');
  });

  test('create assignment returns populated ApiSuccess', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, contains('/agent/workforce/assignments'));
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['functional_key'], 'campaign_planner');

      return http.Response(
        jsonEncode({
          'data': {
            'assignment_id': 'asg_123',
            'workspace_id': 'ws_1001',
            'functional_key': 'campaign_planner',
            'spec_id': 'cosa.campaign_planner',
            'spec_version': '1.0.0',
            'definition_hash': 'sha256:abc',
            'reports_to_assignment_id': null,
            'configured_by': 'user_1',
            'status': 'ACTIVE',
            'created_at': '2026-08-31T12:00:00.000Z',
            'retired_at': null,
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'agent_db', 'ref': 'agent.workforce_assignments'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = WorkforceService(client: requestClient);

    final result = await service.createAssignment(functionalKey: 'campaign_planner');
    expect(result, isA<ApiSuccess<WorkforceAssignment>>());
    final success = result as ApiSuccess<WorkforceAssignment>;
    expect(success.data.assignmentId, 'asg_123');
    expect(success.data.functionalKey, 'campaign_planner');
    expect(success.data.status, 'ACTIVE');
  });

  test('get health returns health list with not_observed', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, contains('/agent/workforce/health'));

      return http.Response(
        jsonEncode({
          'data': [
            {
              'assignment_id': 'asg_123',
              'functional_key': 'campaign_planner',
              'status': 'not_observed',
              'observed_at': null,
              'source_ref': null,
              'last_run_id': null,
              'message': 'No runs observed',
            }
          ],
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'agent_db', 'ref': 'agent.workforce_assignments'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = WorkforceService(client: requestClient);

    final result = await service.getHealth();
    expect(result, isA<ApiSuccess<List<WorkforceHealth>>>());
    final success = result as ApiSuccess<List<WorkforceHealth>>;
    expect(success.data.length, 1);
    expect(success.data.first.status, 'not_observed');
  });

  test('decide approval submits decision truthfully', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, contains('/agent/workforce/approvals/appr_123/decision'));
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['decision'], 'APPROVED');

      return http.Response(
        jsonEncode({
          'data': {
            'approval_id': 'appr_123',
            'status': 'APPROVED',
            'decided_at': '2026-08-31T12:00:00.000Z',
            'reason': 'Looks good',
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'agent_db', 'ref': 'agent.approvals'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = WorkforceService(client: requestClient);

    final result = await service.decideApproval('appr_123', 'APPROVED', reason: 'Looks good');
    expect(result, isA<ApiSuccess<WorkforceApprovalDecision>>());
    final success = result as ApiSuccess<WorkforceApprovalDecision>;
    expect(success.data.approvalId, 'appr_123');
    expect(success.data.status, 'APPROVED');
    expect(success.data.reason, 'Looks good');
  });
}
