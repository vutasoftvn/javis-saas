import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/workforce/models/workforce_mvp_models.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'ws_1001',
    });
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('404 workforce response is shown as failure, not an empty list', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(jsonEncode({'message': 'Not found'}), 404);
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.listRuns();
    expect(result, isA<ApiFailure<List<WorkforceRun>>>());
    expect((result as ApiFailure<List<WorkforceRun>>).failure.statusCode, 404);
  });

  test('500 approvals response is a failure, never a synthesized empty list', () async {
    final mockHttp = MockClient((request) async {
      return http.Response('Server error', 500);
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.listApprovals();
    expect(result, isA<ApiFailure<List<WorkforceApproval>>>());
  });

  test('listRuns decodes MVP envelope into WorkforceRun list', () async {
    final mockHttp = MockClient((request) async {
      expect(request.url.path, '/agent/workforce/runs');
      return http.Response(
        jsonEncode({
          'data': [
            {
              'run_id': 'run_1',
              'workspace_id': 'ws_1001',
              'agent_spec_id': 'spec_1',
              'agent_spec_version': 'v1',
              'definition_hash': 'hash1',
              'status': 'completed',
              'created_at': '2026-08-31T12:00:00.000Z',
            },
          ],
          'meta': {
            'data_state': 'populated',
            'observed_at': '2026-08-31T12:00:00.000Z',
            'sources': [
              {'kind': 'agent_db', 'ref': 'agent.runs'},
            ],
          },
        }),
        200,
      );
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.listRuns();
    expect(result, isA<ApiSuccess<List<WorkforceRun>>>());
    final success = result as ApiSuccess<List<WorkforceRun>>;
    expect(success.data.single.runId, 'run_1');
    expect(success.data.single.status, 'completed');
  });

  test('getComposition never fabricates a default pack list on failure', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(jsonEncode({'message': 'unavailable'}), 503);
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.getComposition();
    expect(result, isA<ApiFailure<List<WorkforceCompositionEntry>>>());
  });

  test('getComposition decodes real composition entries only', () async {
    final mockHttp = MockClient((request) async {
      expect(request.url.path, '/agent/workforce/composition');
      return http.Response(
        jsonEncode({
          'data': [
            {
              'functional_key': 'campaign_planner',
              'title': 'Campaign Planner',
              'description': 'Plans campaigns',
              'spec_id': 'spec_cp',
              'spec_version': 'v1',
              'definition_hash': 'hash_cp',
              'allowed_capability_prefixes': ['marketing.'],
              'assigned': true,
              'assignment_id': 'assign_1',
              'status': 'ACTIVE',
              'eligibility_reasons': ['already_assigned'],
            },
          ],
          'meta': {
            'data_state': 'populated',
            'observed_at': '2026-08-31T12:00:00.000Z',
            'sources': [
              {'kind': 'agent_db', 'ref': 'agent.workforce_assignments'},
            ],
          },
        }),
        200,
      );
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.getComposition();
    expect(result, isA<ApiSuccess<List<WorkforceCompositionEntry>>>());
    final success = result as ApiSuccess<List<WorkforceCompositionEntry>>;
    expect(success.data.single.functionalKey, 'campaign_planner');
    expect(success.data.single.assigned, isTrue);
    expect(success.data.length, 1);
  });

  test('decideApproval posts approved flag and reason, decodes decision', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/agent/workforce/approvals/app_1/decision');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['approved'], isTrue);
      expect(body['reason'], 'looks good');
      return http.Response(
        jsonEncode({
          'data': {
            'approval_id': 'app_1',
            'run_id': 'run_1',
            'status': 'approved',
            'reviewer': 'user:alice',
            'reason': 'looks good',
            'decided_at': '2026-08-31T12:05:00.000Z',
          },
          'meta': {
            'data_state': 'populated',
            'observed_at': '2026-08-31T12:05:00.000Z',
            'sources': [
              {'kind': 'agent_db', 'ref': 'agent.approvals'},
            ],
          },
        }),
        200,
      );
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.decideApproval('app_1', approved: true, reason: 'looks good');
    expect(result, isA<ApiSuccess<WorkforceApprovalDecision>>());
    final success = result as ApiSuccess<WorkforceApprovalDecision>;
    expect(success.data.status, 'approved');
    expect(success.data.reviewer, 'user:alice');
  });

  test('decideApproval 404 (tenant isolation) surfaces as ApiFailure', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(jsonEncode({'detail': 'Approval not found'}), 404);
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.decideApproval('app_x', approved: true);
    expect(result, isA<ApiFailure<WorkforceApprovalDecision>>());
    expect((result as ApiFailure<WorkforceApprovalDecision>).failure.code, ApiFailureCode.notFound);
  });

  test('listRunEvents decodes run event stream honestly', () async {
    final mockHttp = MockClient((request) async {
      expect(request.url.path, '/agent/workforce/runs/run_1/events');
      return http.Response(
        jsonEncode({
          'data': [
            {
              'event_id': 'evt_1',
              'run_id': 'run_1',
              'sequence': 1,
              'event_type': 'started',
              'payload': {'foo': 'bar'},
              'created_at': '2026-08-31T12:00:00.000Z',
            },
          ],
          'meta': {
            'data_state': 'populated',
            'observed_at': '2026-08-31T12:00:00.000Z',
            'sources': [
              {'kind': 'agent_db', 'ref': 'agent.run_stream_events'},
            ],
          },
        }),
        200,
      );
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.listRunEvents('run_1');
    expect(result, isA<ApiSuccess<List<WorkforceRunEvent>>>());
    final success = result as ApiSuccess<List<WorkforceRunEvent>>;
    expect(success.data.single.eventType, 'started');
    expect(success.data.single.payload['foo'], 'bar');
  });
}
