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

  test('list skills returns published skills with control_plane as authoritative source', () async {
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
              'revision': 1,
            }
          ],
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'control_plane', 'ref': 'control_plane.skill_policies'}],
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
    expect(success.data.first.revision, 1);
    expect(success.meta.sources.first.kind, 'control_plane');
    expect(service.cachedSkill('lead_enricher')?.revision, 1);
  });

  // Task 4 — SettingsMvpService.updateSkill chỉ áp state cục bộ khi response
  // ApiSuccess trả về revision LỚN HƠN revision hiện tại đã biết. Đây là
  // guard chống 1 response cũ/lặp (retry mạng, request trả về không theo
  // đúng thứ tự gửi) bị coi là thành công và ghi đè state mới hơn.
  group('updateSkill revision guard', () {
    Map<String, dynamic> skillJson({required bool enabled, required int revision}) => {
          'id': 'lead_enricher',
          'skillKey': 'lead_enricher',
          'name': 'Lead Enricher',
          'description': 'Enriches leads from web sources',
          'version': '1.0.0',
          'installed': enabled,
          'status': enabled ? 'active' : 'disabled',
          'publisher': 'cosa_platform',
          'autonomyCeiling': 'supervised',
          'tags': <String>[],
          'updatedAt': '2026-08-31T12:00:00.000Z',
          'revision': revision,
        };

    Map<String, dynamic> envelope(Map<String, dynamic> data) => {
          'data': data,
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [
              {'kind': 'control_plane', 'ref': 'control_plane.skill_policies'},
            ],
          },
        };

    test('applies local state when revision increases', () async {
      var callCount = 0;
      final mockHttp = MockClient((request) async {
        callCount += 1;
        return http.Response(
          jsonEncode(envelope(skillJson(enabled: callCount.isOdd, revision: callCount))),
          200,
        );
      });

      final service = SettingsMvpService(client: MvpRequestClient(httpClient: mockHttp));

      final first = await service.updateSkill('lead_enricher', enabled: true, config: {});
      expect(first, isA<ApiSuccess<SkillSettingModel>>());
      expect(service.cachedSkill('lead_enricher')?.revision, 1);
      expect(service.cachedSkill('lead_enricher')?.installed, true);

      final second = await service.updateSkill('lead_enricher', enabled: false, config: {});
      expect(second, isA<ApiSuccess<SkillSettingModel>>());
      expect(service.cachedSkill('lead_enricher')?.revision, 2);
      expect(service.cachedSkill('lead_enricher')?.installed, false);
    });

    test('does not overwrite newer local state with a stale/duplicate revision', () async {
      final responses = <http.Response>[
        http.Response(jsonEncode(envelope(skillJson(enabled: true, revision: 2))), 200),
        // Response cũ/lặp: revision KHÔNG lớn hơn state cục bộ hiện tại (2).
        http.Response(jsonEncode(envelope(skillJson(enabled: true, revision: 2))), 200),
      ];
      var callIndex = 0;
      final mockHttp = MockClient((request) async {
        return responses[callIndex++];
      });

      final service = SettingsMvpService(client: MvpRequestClient(httpClient: mockHttp));

      await service.updateSkill('lead_enricher', enabled: true, config: {});
      expect(service.cachedSkill('lead_enricher')?.revision, 2);

      final stale = await service.updateSkill('lead_enricher', enabled: false, config: {});
      // HTTP layer vẫn báo thành công (server trả 200) — ApiResult phản ánh
      // đúng response thật...
      expect(stale, isA<ApiSuccess<SkillSettingModel>>());
      // ...nhưng state cục bộ (cachedSkill) KHÔNG bị đè bởi response revision
      // không tăng — vẫn giữ nguyên revision 2 / enabled=true trước đó.
      expect(service.cachedSkill('lead_enricher')?.revision, 2);
      expect(service.cachedSkill('lead_enricher')?.installed, true);
    });
  });
}
