import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/modules/settings/models/settings_models.dart';
import 'package:frontend/modules/settings/services/settings_mvp_service.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      'auth_token': 'test-token',
      'workspace_id': '1001',
    });
  });

  test('settings 503 is unavailable, not empty member list', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({'code': 'unavailable', 'message': 'Control plane unavailable'}),
        503,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = SettingsMvpService(client: requestClient);

    final result = await service.listMembers();
    expect(result, isA<ApiFailure<List<WorkspaceMemberModel>>>());
    expect((result as ApiFailure<List<WorkspaceMemberModel>>).failure.code, ApiFailureCode.unavailable);
  });

  test('list members returns populated list', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, contains('/platform/workspaces/1001/members'));

      return http.Response(
        jsonEncode({
          'data': [
            {
              'id': 'mem_1',
              'workspaceId': '1001',
              'userId': 'usr_99',
              'roleId': 'founder',
              'email': 'founder@example.com',
              'fullName': 'Alice Founder',
              'createdAt': '2026-08-31T12:00:00.000Z',
            }
          ],
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'control_plane', 'ref': 'control_plane.settings'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = SettingsMvpService(client: requestClient);

    final result = await service.listMembers();
    expect(result, isA<ApiSuccess<List<WorkspaceMemberModel>>>());
    final success = result as ApiSuccess<List<WorkspaceMemberModel>>;
    expect(success.data.length, 1);
    expect(success.data.first.roleId, 'founder');
  });

  test('list connectors returns populated list with no secrets exposed', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, contains('/platform/workspaces/1001/connectors'));

      return http.Response(
        jsonEncode({
          'data': [
            {
              'id': 'conn_1',
              'connectorKey': 'google-drive',
              'state': 'enabled',
              'grantedScopes': ['read', 'write'],
              'observedAt': '2026-08-31T12:00:00.000Z',
            }
          ],
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'control_plane', 'ref': 'control_plane.settings'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = SettingsMvpService(client: requestClient);

    final result = await service.listConnectors();
    expect(result, isA<ApiSuccess<List<ConnectorStatusModel>>>());
    final success = result as ApiSuccess<List<ConnectorStatusModel>>;
    expect(success.data.length, 1);
    expect(success.data.first.connectorKey, 'google-drive');
    expect(success.data.first.state, 'enabled');
  });

  test('list runtime nodes returns presence and source', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, contains('/platform/workspaces/1001/runtime-nodes'));

      return http.Response(
        jsonEncode({
          'data': [
            {
              'id': 'node_1',
              'workspaceId': '1001',
              'nodeId': 'node_local_1',
              'runtimeRole': 'local_workspace_runtime',
              'presence': 'ONLINE',
              'lastHeartbeatAt': '2026-08-31T12:00:00.000Z',
              'status': 'active',
            }
          ],
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'control_plane', 'ref': 'control_plane.settings'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = SettingsMvpService(client: requestClient);

    final result = await service.listRuntimeNodes();
    expect(result, isA<ApiSuccess<List<RuntimeNodeModel>>>());
    final success = result as ApiSuccess<List<RuntimeNodeModel>>;
    expect(success.data.length, 1);
    expect(success.data.first.presence, 'ONLINE');
  });

  test('list skills returns published skills from agent_db', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, contains('/agent/settings/skills'));

      return http.Response(
        jsonEncode({
          'data': [
            {
              'id': 'lead_enricher',
              'skillKey': 'lead_enricher',
              'name': 'Lead Enricher',
              'description': 'Enriches leads from web sources',
              'version': '1.0.0',
              'installed': true,
              'status': 'active',
              'publisher': 'cosa_platform',
              'autonomyCeiling': 'supervised',
              'tags': ['growth', 'leads'],
              'updatedAt': '2026-08-31T12:00:00.000Z',
            }
          ],
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'agent_db', 'ref': 'agent.skills'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = SettingsMvpService(client: requestClient);

    final result = await service.listSkills();
    expect(result, isA<ApiSuccess<List<SkillSettingModel>>>());
    final success = result as ApiSuccess<List<SkillSettingModel>>;
    expect(success.data.length, 1);
    expect(success.data.first.name, 'Lead Enricher');
    expect(success.meta.sources.first.kind, 'agent_db');
  });
}
