import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/hologram_hub/models/executive_advisory_board.dart';
import 'package:frontend/modules/hologram_hub/services/executive_advisory_board_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'workspace_id': '1001',
    });
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('fetches executive advisor roles with truthful states', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/operations/projects/proj-101/executive-roles');

      return http.Response(
        jsonEncode({
          'data': {
            'roles': [
              {
                'roleKey': 'cfo',
                'title': 'CFO Advisor',
                'domain': 'finance',
                'advisoryLevel': 'L1',
                'description': 'Financial modeling and cash runway advisory',
                'capabilities': ['read_metrics', 'propose_budget'],
                'activationState': 'ACTIVE',
                'underlyingProfileKey': 'finance',
                'assignmentStatus': 'ACTIVE',
                'specHash': 'spec-hash-1',
                'assignmentVersion': 1,
              },
              {
                'roleKey': 'ciso',
                'title': 'CISO Advisor',
                'domain': 'security',
                'advisoryLevel': 'L1',
                'description': 'Security and compliance guidance',
                'capabilities': ['audit_compliance'],
                'activationState': 'UNAVAILABLE',
                'underlyingProfileKey': 'security',
                'assignmentStatus': 'UNASSIGNED',
                'specHash': 'spec-hash-2',
                'disabledReason': 'UNDERLYING_PROFILE_UNAVAILABLE',
              },
            ],
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-11T12:00:00Z',
            'sources': [
              {'kind': 'company_db', 'ref': 'operating'}
            ],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = ExecutiveAdvisoryBoardService(client: requestClient);

    final result = await service.fetchRoles('proj-101');
    expect(result, isA<ApiSuccess<List<ExecutiveAdvisorRole>>>());
    final roles = (result as ApiSuccess<List<ExecutiveAdvisorRole>>).data;
    expect(roles, hasLength(2));

    expect(roles[0].roleKey, 'cfo');
    expect(roles[0].activationState, ExecutiveActivationState.active);
    expect(roles[0].assignmentVersion, 1);

    expect(roles[1].roleKey, 'ciso');
    expect(roles[1].activationState, ExecutiveActivationState.unavailable);
    expect(roles[1].disabledReason, 'UNDERLYING_PROFILE_UNAVAILABLE');
  });

  test('activates an executive role with expected version', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(
        request.url.path,
        '/operations/projects/proj-101/executive-roles/cfo/activate',
      );
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['expectedVersion'], 1);

      return http.Response(
        jsonEncode({
          'data': {
            'roleKey': 'cfo',
            'title': 'CFO Advisor',
            'domain': 'finance',
            'advisoryLevel': 'L1',
            'description': 'Financial modeling',
            'capabilities': ['read_metrics'],
            'activationState': 'ACTIVE',
            'underlyingProfileKey': 'finance',
            'assignmentStatus': 'ACTIVE',
            'specHash': 'hash-cfo',
            'assignmentVersion': 2,
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-11T12:00:00Z',
            'sources': [
              {'kind': 'company_db', 'ref': 'operating'}
            ],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = ExecutiveAdvisoryBoardService(client: requestClient);

    final result = await service.activateRole(
      projectId: 'proj-101',
      roleKey: 'cfo',
      expectedVersion: 1,
    );
    expect(result, isA<ApiSuccess<ExecutiveAdvisorRole>>());
    final role = (result as ApiSuccess<ExecutiveAdvisorRole>).data;
    expect(role.activationState, ExecutiveActivationState.active);
    expect(role.assignmentVersion, 2);
  });

  test('handles activation error faithfully without local success fabrication', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'error': {
            'code': 'failed_precondition',
            'message': 'Underlying profile finance is not active',
          },
        }),
        412,
        headers: {'content-type': 'application/json'},
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = ExecutiveAdvisoryBoardService(client: requestClient);

    final result = await service.activateRole(
      projectId: 'proj-101',
      roleKey: 'cfo',
      expectedVersion: 1,
    );
    expect(result, isA<ApiFailure<ExecutiveAdvisorRole>>());
  });
}
