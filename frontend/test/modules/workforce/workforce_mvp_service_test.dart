import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/data/models/verification_report_model.dart';
import 'package:frontend/modules/agents/models/workforce_models.dart' as agent_models;
import 'package:frontend/modules/agents/services/workforce_service.dart';
import 'package:frontend/modules/workforce/models/workforce_mvp_models.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';

http.Response _envelope(Object data) => http.Response(
      jsonEncode({
        'data': data,
        'meta': {
          'dataState': 'populated',
          'observedAt': '2026-09-26T00:00:00Z',
          'sources': [
            {'kind': 'agent_db', 'ref': 'agent.workforce_assignments'},
          ],
        },
      }),
      200,
      headers: {'content-type': 'application/json'},
    );

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('listRoster gọi /agent/workforce/roster thật (không còn stub R1)', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/agent/workforce/roster');
      return _envelope([
        {
          'id': 1,
          'key': 'operations',
          'name': 'Operations',
          'role_title': 'COO',
          'department': 'Operations',
          'agent_type': 'functional',
          'default_model_profile': 'default',
          'risk_level': 2,
          'status': 'ACTIVE',
          'enabled': true,
        },
      ]);
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.listRoster();

    final roster = (result as ApiSuccess<List<WorkforceRosterEntry>>).data;
    expect(roster.single.key, 'operations');
  });

  test('decideApproval POST decision với approvalId trong path', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/agent/workforce/approvals/ap-1/decision');
      expect(jsonDecode(request.body), {'approved': true, 'reason': 'ok'});
      return _envelope({
        'approval_id': 'ap-1',
        'status': 'APPROVED',
        'decided_at': '2026-09-26T00:00:00Z',
        'reason': 'ok',
      });
    });
    final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.decideApproval('ap-1', approved: true, reason: 'ok');

    expect(result, isA<ApiSuccess<WorkforceApprovalDecision>>());
  });

  test('WorkforceService.createAssignment gửi company_workforce_member_id', () async {
    final mockHttp = MockClient((request) async {
      expect(request.url.path, '/agent/workforce/assignments');
      expect(jsonDecode(request.body), {
        'functional_key': 'operations',
        'company_workforce_member_id': 'wm-1',
      });
      return _envelope({
        'assignment_id': 'as-1',
        'workspace_id': '1001',
        'functional_key': 'operations',
        'spec_id': 'cosa.agents.operations',
        'spec_version': '1.0.0',
        'definition_hash': 'h',
        'configured_by': 'user:1',
        'status': 'ACTIVE',
        'created_at': '2026-09-26T00:00:00Z',
      });
    });
    final service = WorkforceService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.createAssignment(
      functionalKey: 'operations',
      companyWorkforceMemberId: 'wm-1',
    );

    expect((result as ApiSuccess<agent_models.WorkforceAssignment>).data.assignmentId, 'as-1');
  });

  test('lỗi backend trả ApiFailure, không nuốt thành rỗng', () async {
    final mockHttp = MockClient((_) async => http.Response('{"detail":"boom"}', 503));
    final service = WorkforceService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.listSchedules();

    expect(result, isA<ApiFailure<List<agent_models.WorkforceSchedule>>>());
  });

  group('listVerificationReports', () {
    test('một request theo lô, phân tích verdict/criteria theo taskId', () async {
      var calls = 0;
      final mockHttp = MockClient((request) async {
        calls++;
        expect(request.method, 'GET');
        expect(request.url.path, '/agent/workforce/verification-reports');
        expect(request.url.queryParameters['taskIds'], 't1,t2');
        return _envelope([
          {
            'reportId': 'vr_1',
            'taskId': 't1',
            'runId': 'run_1',
            'verifierRunId': null,
            'verdict': 'FAIL',
            'mode': 'deterministic',
            'criteriaResults': [
              {
                'id': 'c1',
                'required': true,
                'check': 'deterministic',
                'verdict': 'fail',
                'reason': 'artifact_not_found',
              },
            ],
            'createdAt': '2026-01-01T12:00:00Z',
          },
          {
            'reportId': 'vr_2',
            'taskId': 't2',
            'runId': 'run_2',
            'verdict': 'weird',
            'mode': 'llm',
            'criteriaResults': null,
            'createdAt': 'not-a-date',
          },
        ]);
      });
      final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

      final map = await service.listVerificationReports(['t1', 't2', 't1', '']);

      expect(calls, 1);
      expect(map.keys, unorderedEquals(['t1', 't2']));
      expect(map['t1']!.verdict, VerificationVerdict.fail);
      expect(map['t1']!.criteria.single.id, 'c1');
      expect(map['t1']!.criteria.single.required, isTrue);
      expect(map['t1']!.criteria.single.reason, 'artifact_not_found');
      expect(map['t1']!.createdAt, DateTime.utc(2026, 1, 1, 12));
      expect(map['t2']!.verdict, VerificationVerdict.inconclusive);
      expect(map['t2']!.criteria, isEmpty);
      expect(map['t2']!.createdAt, isNull);
    });

    test('danh sách rỗng không gọi mạng', () async {
      final mockHttp = MockClient((_) async => fail('không được gọi mạng'));
      final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

      expect(await service.listVerificationReports(const []), isEmpty);
    });

    test('403 ném StateError', () async {
      final mockHttp = MockClient((_) async => http.Response('{"detail":"no"}', 403));
      final service = WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp));

      await expectLater(service.listVerificationReports(['t1']), throwsStateError);
    });
  });
}
