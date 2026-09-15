import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/modules/hologram_hub/models/executive_advisory_board.dart';
import 'package:frontend/modules/hologram_hub/services/executive_advisory_board_service.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/services/secure_storage_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws'});
    await SecureStorageService.write('auth_token', 'token');
  });
  test(
    'decodes separate Workspace office and Project deployment states',
    () async {
      final httpClient = MockClient(
        (request) async => http.Response(
          jsonEncode({
            'data': {
              'roles': [
                {
                  'roleKey': 'cfo',
                  'label': 'CFO',
                  'advisoryRemit': 'Cash',
                  'requiredProfileKey': 'finance',
                  'officeState': 'ACTIVE',
                  'projectDeploymentState': 'INACTIVE',
                  'stageEligibility': 'ALLOWED',
                  'effectiveState': 'DEPLOYMENT_INACTIVE',
                  'workspaceOfficeVersion': 4,
                },
              ],
            },
            'meta': {
              'dataState': 'populated',
              'observedAt': '2026-09-15T00:00:00Z',
              'sources': [],
            },
          }),
          200,
          headers: {'content-type': 'application/json'},
        ),
      );
      final result = await ExecutiveAdvisoryBoardService(
        client: MvpRequestClient(httpClient: httpClient),
      ).fetchRoles('project');
      final role =
          (result as ApiSuccess<List<ExecutiveAdvisorRole>>).data.single;
      expect(role.officeState, ExecutiveOfficeState.active);
      expect(
        role.projectDeploymentState,
        ExecutiveProjectDeploymentState.inactive,
      );
      expect(role.effectiveState, ExecutiveEffectiveState.deploymentInactive);
      expect(role.workspaceOfficeVersion, 4);
    },
  );
  test('Workspace office mutation sends its CAS version', () async {
    final httpClient = MockClient((request) async {
      final body = jsonDecode(request.body);
      expect(body['expectedVersion'], 4);
      return http.Response(
        jsonEncode({
          'data': {
            'id': 'm',
            'roleKey': 'cfo',
            'state': 'ACTIVE',
            'version': 5,
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-15T00:00:00Z',
            'sources': [],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final result = await ExecutiveAdvisoryBoardService(
      client: MvpRequestClient(httpClient: httpClient),
    ).activateRole(workspaceId: 'ws', roleKey: 'cfo', expectedVersion: 4);
    expect(result.isSuccess, isTrue);
  });

  test(
    'rejects a legacy or incomplete role shape instead of inventing effective state',
    () async {
      final httpClient = MockClient(
        (request) async => http.Response(
          jsonEncode({
            'data': {
              'roles': [
                {
                  'roleKey': 'cfo',
                  'label': 'CFO',
                  'advisoryRemit': 'Cash',
                  'requiredProfileKey': 'finance',
                  'officeState': 'ACTIVE',
                  // projectDeploymentState intentionally missing.
                  'stageEligibility': 'ALLOWED',
                  'effectiveState': 'EFFECTIVE',
                  'workspaceOfficeVersion': 1,
                },
              ],
            },
            'meta': {
              'dataState': 'populated',
              'observedAt': '2026-09-15T00:00:00Z',
              'sources': [],
            },
          }),
          200,
          headers: {'content-type': 'application/json'},
        ),
      );

      final result = await ExecutiveAdvisoryBoardService(
        client: MvpRequestClient(httpClient: httpClient),
      ).fetchRoles('project');

      expect(result, isA<ApiFailure<List<ExecutiveAdvisorRole>>>());
    },
  );
}
