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

  test('fetches executive advisor roles with truthful Company contract fields', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/operations/projects/proj-101/executive-roles');

      return http.Response(
        jsonEncode({
          'data': {
            'roles': [
              {
                'roleKey': 'cfo',
                'label': 'CFO Advisor',
                'advisoryRemit': 'Financial modeling and cash runway advisory',
                'displayState': 'ACTIVE',
                'runtimeReadiness': 'READY',
                'requiredProfileKey': 'finance',
                'version': 2,
                'actorId': 'user-1',
                'activatedAt': '2026-09-11T12:00:00.000Z',
              },
              {
                'roleKey': 'chief_of_staff',
                'label': 'Chief of Staff',
                'advisoryRemit': 'Điều phối thực thi liên phòng ban',
                'displayState': 'AVAILABLE_NOT_ACTIVATED',
                'runtimeReadiness': 'READY',
                'requiredProfileKey': 'operations',
                'version': 1,
              },
              {
                'roleKey': 'coo',
                'label': 'Chief Operating Officer',
                'advisoryRemit': 'Thiết kế hệ thống vận hành và tối ưu nguồn lực',
                'displayState': 'UNAVAILABLE',
                'runtimeReadiness': 'READY',
                'requiredProfileKey': 'operations',
                'version': 1,
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
    expect(roles, hasLength(3));

    expect(roles[0].roleKey, 'cfo');
    expect(roles[0].title, 'CFO Advisor');
    expect(roles[0].description, 'Financial modeling and cash runway advisory');
    expect(roles[0].activationState, ExecutiveActivationState.active);
    expect(roles[0].underlyingProfileKey, 'finance');
    expect(roles[0].domain, 'finance');
    expect(roles[0].assignmentVersion, 2);
    expect(roles[0].activatedBy, 'user-1');

    expect(roles[1].roleKey, 'chief_of_staff');
    expect(roles[1].title, 'Chief of Staff');
    expect(roles[1].activationState, ExecutiveActivationState.availableNotActivated);
    expect(roles[1].underlyingProfileKey, 'operations');

    expect(roles[2].roleKey, 'coo');
    expect(roles[2].title, 'Chief Operating Officer');
    expect(roles[2].activationState, ExecutiveActivationState.unavailable);
    expect(roles[2].disabledReason, 'UNDERLYING_PROFILE_UNAVAILABLE');
  });

  test('CPO remains unavailable until Company reports active Product profile', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': {
            'roles': [
              {
                'roleKey': 'cpo',
                'label': 'CPO Advisor',
                'advisoryRemit': 'Định hướng sản phẩm và ưu tiên roadmap',
                'displayState': 'UNAVAILABLE',
                'runtimeReadiness': 'READY',
                'requiredProfileKey': 'product',
                'version': 1,
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
    expect(roles, hasLength(1));

    final cpo = roles[0];
    expect(cpo.roleKey, 'cpo');
    expect(cpo.activationState, ExecutiveActivationState.unavailable);
    expect(cpo.underlyingProfileKey, 'product');
    expect(cpo.disabledReason, 'UNDERLYING_PROFILE_UNAVAILABLE');
  });

  test('CHRO remains unavailable until Company reports active People profile', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': {
            'roles': [
              {
                'roleKey': 'chro',
                'label': 'CHRO Advisor',
                'advisoryRemit': 'Thiết kế tổ chức, quy trình tuyển dụng, rủi ro con người',
                'displayState': 'UNAVAILABLE',
                'runtimeReadiness': 'READY',
                'requiredProfileKey': 'people',
                'version': 1,
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
    expect(roles, hasLength(1));

    final chro = roles[0];
    expect(chro.roleKey, 'chro');
    expect(chro.activationState, ExecutiveActivationState.unavailable);
    expect(chro.underlyingProfileKey, 'people');
    expect(chro.disabledReason, 'UNDERLYING_PROFILE_UNAVAILABLE');
  });

  test('CISO remains unavailable until Company reports active Security profile', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': {
            'roles': [
              {
                'roleKey': 'ciso',
                'label': 'CISO Advisor',
                'advisoryRemit': 'Threat modeling, kiểm soát quyền riêng tư, khoảng trống tuân thủ',
                'displayState': 'UNAVAILABLE',
                'runtimeReadiness': 'READY',
                'requiredProfileKey': 'security',
                'version': 1,
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
    expect(roles, hasLength(1));

    final ciso = roles[0];
    expect(ciso.roleKey, 'ciso');
    expect(ciso.activationState, ExecutiveActivationState.unavailable);
    expect(ciso.underlyingProfileKey, 'security');
    expect(ciso.disabledReason, 'UNDERLYING_PROFILE_UNAVAILABLE');
  });

  test('GC remains unavailable until Company reports active Legal profile', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': {
            'roles': [
              {
                'roleKey': 'gc',
                'label': 'General Counsel',
                'advisoryRemit': 'Legal and regulatory issue spotting, policy risk resolution, escalation',
                'displayState': 'UNAVAILABLE',
                'runtimeReadiness': 'READY',
                'requiredProfileKey': 'legal',
                'version': 1,
                'disabledReason': 'UNDERLYING_PROFILE_UNAVAILABLE',
              },
            ],
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-13T12:00:00Z',
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
    expect(roles, hasLength(1));

    final gc = roles[0];
    expect(gc.roleKey, 'gc');
    expect(gc.activationState, ExecutiveActivationState.unavailable);
    expect(gc.underlyingProfileKey, 'legal');
    expect(gc.disabledReason, 'UNDERLYING_PROFILE_UNAVAILABLE');
  });

  test('CDO remains unavailable until Company reports active Data profile', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': {
            'roles': [
              {
                'roleKey': 'cdo',
                'label': 'Chief Data Officer',
                'advisoryRemit':
                    'Data governance, quality, rights management, scoped knowledge integrity',
                'displayState': 'UNAVAILABLE',
                'runtimeReadiness': 'READY',
                'requiredProfileKey': 'data',
                'version': 1,
                'disabledReason': 'UNDERLYING_PROFILE_UNAVAILABLE',
              },
            ],
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-13T12:00:00Z',
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
    expect(roles, hasLength(1));

    final cdo = roles[0];
    expect(cdo.roleKey, 'cdo');
    expect(cdo.activationState, ExecutiveActivationState.unavailable);
    expect(cdo.underlyingProfileKey, 'data');
    expect(cdo.disabledReason, 'UNDERLYING_PROFILE_UNAVAILABLE');
  });

  test(
      'CAIO remains unavailable until Company reports active AI Governance profile',
      () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': {
            'roles': [
              {
                'roleKey': 'caio',
                'label': 'Chief AI Officer',
                'advisoryRemit':
                    'Model evaluation, provider governance, prompt safety, red-team assessment',
                'displayState': 'UNAVAILABLE',
                'runtimeReadiness': 'READY',
                'requiredProfileKey': 'ai_governance',
                'version': 1,
                'disabledReason': 'UNDERLYING_PROFILE_UNAVAILABLE',
              },
            ],
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-13T12:00:00Z',
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
    expect(roles, hasLength(1));

    final caio = roles[0];
    expect(caio.roleKey, 'caio');
    expect(caio.activationState, ExecutiveActivationState.unavailable);
    expect(caio.underlyingProfileKey, 'ai_governance');
    expect(caio.disabledReason, 'UNDERLYING_PROFILE_UNAVAILABLE');
  });

  test('activates an executive role via workspace-scoped endpoint and decodes mutation receipt truthfully',
      () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(
        request.url.path,
        '/operations/workspaces/ws-1/executive-roles/chief_of_staff/activate',
      );
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['expectedVersion'], 1);

      return http.Response(
        jsonEncode({
          'data': {
            'id': 'mut-cos-1',
            'roleKey': 'chief_of_staff',
            'state': 'ACTIVE',
            'version': 2,
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
      workspaceId: 'ws-1',
      roleKey: 'chief_of_staff',
      expectedVersion: 1,
    );
    expect(result, isA<ApiSuccess<ExecutiveRoleMutationReceipt>>());
    final receipt = (result as ApiSuccess<ExecutiveRoleMutationReceipt>).data;
    expect(receipt.id, 'mut-cos-1');
    expect(receipt.roleKey, 'chief_of_staff');
    expect(receipt.state, 'ACTIVE');
    expect(receipt.version, 2);
  });

  test('disables an executive role via workspace-scoped endpoint and decodes mutation receipt truthfully',
      () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(
        request.url.path,
        '/operations/workspaces/ws-1/executive-roles/coo/disable',
      );
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['expectedVersion'], 2);
      expect(body['reason'], 'Strategic pause');

      return http.Response(
        jsonEncode({
          'data': {
            'id': 'mut-coo-2',
            'roleKey': 'coo',
            'state': 'DISABLED',
            'version': 3,
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

    final result = await service.disableRole(
      workspaceId: 'ws-1',
      roleKey: 'coo',
      expectedVersion: 2,
      reason: 'Strategic pause',
    );
    expect(result, isA<ApiSuccess<ExecutiveRoleMutationReceipt>>());
    final receipt = (result as ApiSuccess<ExecutiveRoleMutationReceipt>).data;
    expect(receipt.id, 'mut-coo-2');
    expect(receipt.roleKey, 'coo');
    expect(receipt.state, 'DISABLED');
    expect(receipt.version, 3);
  });

  test('handles activation error faithfully without local success fabrication', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'error': {
            'code': 'failed_precondition',
            'message': 'Underlying profile operations is not active',
          },
        }),
        412,
        headers: {'content-type': 'application/json'},
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = ExecutiveAdvisoryBoardService(client: requestClient);

    final result = await service.activateRole(
      workspaceId: 'ws-1',
      roleKey: 'coo',
      expectedVersion: 1,
    );
    expect(result, isA<ApiFailure<ExecutiveRoleMutationReceipt>>());
  });
}
