import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/settings/models/settings_models.dart';
import 'package:frontend/modules/settings/services/settings_mvp_service.dart';

http.Response _envelope(Object data) => http.Response(
      jsonEncode({
        'data': data,
        'meta': {
          'dataState': 'populated',
          'observedAt': '2026-09-26T00:00:00Z',
          'sources': [
            {'kind': 'control_plane', 'ref': 'cosa.organization_memberships'},
          ],
        },
      }),
      200,
      headers: {'content-type': 'application/json'},
    );

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': 'org-1'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('listMembers gọi /platform/organizations/:organizationId/members', () async {
    final mockHttp = MockClient((request) async {
      expect(request.url.path, '/platform/organizations/org-1/members');
      return _envelope([
        {
          'id': 'm1',
          'organizationId': 'org-1',
          'userId': 'u1',
          'roleId': 'founder',
          'email': 'a@b.c',
          'fullName': 'A',
          'createdAt': '2026-09-26T00:00:00Z',
        },
      ]);
    });
    final service = SettingsMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.listMembers();

    expect((result as ApiSuccess<List<WorkspaceMemberModel>>).data.single.roleId, 'founder');
  });

  test('installConnector dùng connectorKey trong path', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/platform/organizations/org-1/connectors/gmail/install');
      return _envelope({
        'id': 'c1',
        'connectorKey': 'gmail',
        'state': 'enabled',
        'grantedScopes': <String>[],
        'observedAt': null,
        'expiresAt': null,
        'reason': null,
      });
    });
    final service = SettingsMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.installConnector('gmail');

    expect((result as ApiSuccess<ConnectorStatusModel>).data.state, 'enabled');
  });

  test('runtime node không có id/status -> suy từ nodeId/revokedAt', () async {
    final mockHttp = MockClient((request) async {
      expect(request.url.path, '/platform/organizations/org-1/runtime-nodes');
      return _envelope([
        {
          'nodeId': 'node-1',
          'organizationId': 'org-1',
          'runtimeRole': 'desktop_worker',
          'presence': 'ONLINE',
          'lastHeartbeatAt': '2026-09-26T00:00:00Z',
          'registeredAt': '2026-09-26T00:00:00Z',
          'revokedAt': null,
        },
      ]);
    });
    final service = SettingsMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final node = (await service.listRuntimeNodes() as ApiSuccess<List<RuntimeNodeModel>>).data.single;

    expect(node.id, 'node-1');
    expect(node.status, 'active');
  });

  test('updateSkill PUT /agent/settings/skills/:skillKey và cập nhật cache theo revision', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'PUT');
      expect(request.url.path, '/agent/settings/skills/crm.lead_triage');
      expect(jsonDecode(request.body), {'enabled': false});
      return _envelope({
        'id': 'crm.lead_triage',
        'skillKey': 'crm.lead_triage',
        'name': 'Lead triage',
        'description': '',
        'version': '1.0.0',
        'installed': false,
        'status': 'disabled',
        'publisher': 'cosa_platform',
        'autonomyCeiling': 'supervised',
        'tags': <String>[],
        'updatedAt': '2026-09-26T00:00:00Z',
        'revision': 3,
      });
    });
    final service = SettingsMvpService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.updateSkill('crm.lead_triage', enabled: false);

    expect(result, isA<ApiSuccess<SkillSettingModel>>());
    expect(service.cachedSkill('crm.lead_triage')?.revision, 3);
  });
}
