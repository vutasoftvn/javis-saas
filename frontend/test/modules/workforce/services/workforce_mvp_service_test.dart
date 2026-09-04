// frontend/test/modules/workforce/services/workforce_mvp_service_test.dart
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_auth_resolver.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/modules/workforce/models/workforce_mvp_models.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';

class MockAuthResolver implements ApiAuthResolver {
  @override
  Future<String?> tokenFor(ApiPlane plane) async => 'test-token';

  @override
  Future<String?> workspaceId() async => 'workspace-test';
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-test'});
  });
  test('listRoster calls /agent/workforce/roster and decodes entries', () async {
    final mockHttp = MockClient((request) async {
      expect(request.url.path, '/agent/workforce/roster');
      return http.Response(
        jsonEncode({
          'data': [
            {
              'id': 1, 'key': 'cashflow_planner', 'name': 'Cashflow Planner',
              'role_title': 'x', 'department': 'Finance', 'agent_type': 'specialist',
              'default_model_profile': 'reasoning', 'risk_level': 2,
              'status': 'available', 'enabled': true,
            },
          ],
          'meta': {'data_state': 'populated', 'observed_at': '2026-09-04T12:00:00.000Z', 'sources': []},
        }),
        200,
      );
    });
    final service = WorkforceMvpService(
      client: MvpRequestClient(httpClient: mockHttp, authResolver: MockAuthResolver()),
    );

    final result = await service.listRoster();

    expect(result, isA<ApiSuccess<List<WorkforceRosterEntry>>>());
    final data = (result as ApiSuccess<List<WorkforceRosterEntry>>).data;
    expect(data.single.key, 'cashflow_planner');
  });

  test('getStageRoster calls /agent/workforce/stage-roster/:stageCode with path param', () async {
    final mockHttp = MockClient((request) async {
      expect(request.url.path, '/agent/workforce/stage-roster/P2');
      return http.Response(
        jsonEncode({
          'data': {
            'stage': {'stage_code': 'P2', 'task_count': 0},
            'roster': [],
            'summary': {'total': 0, 'high_priority': 0, 'medium': 0, 'locked': 0},
          },
          'meta': {'data_state': 'empty', 'observed_at': '2026-09-04T12:00:00.000Z', 'sources': []},
        }),
        200,
      );
    });
    final service = WorkforceMvpService(
      client: MvpRequestClient(httpClient: mockHttp, authResolver: MockAuthResolver()),
    );

    final result = await service.getStageRoster('P2');

    expect(result, isA<ApiSuccess<WorkforceStageRoster>>());
  });

  test('listExceptions propagates a 500 as ApiFailure, never a fabricated empty summary', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(jsonEncode({'detail': 'boom'}), 500);
    });
    final service = WorkforceMvpService(
      client: MvpRequestClient(httpClient: mockHttp, authResolver: MockAuthResolver()),
    );

    final result = await service.listExceptions();

    expect(result, isA<ApiFailure<WorkforceExceptionSummary>>());
  });
}
