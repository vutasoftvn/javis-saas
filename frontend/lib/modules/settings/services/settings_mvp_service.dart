import 'package:http/http.dart' as http;

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/settings_models.dart';

class SettingsMvpService {
  final MvpRequestClient _client;

  SettingsMvpService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  // 1. Members
  Future<ApiResult<List<WorkspaceMemberModel>>> listMembers() async {
    return _client.request<List<WorkspaceMemberModel>>(
      MvpEndpoint.settingsMemberList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => WorkspaceMemberModel.fromJson(e))
            .toList();
      },
    );
  }

  // 2. Connectors
  Future<ApiResult<List<ConnectorStatusModel>>> listConnectors() async {
    return _client.request<List<ConnectorStatusModel>>(
      MvpEndpoint.settingsConnectorList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => ConnectorStatusModel.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<ConnectorStatusModel>> installConnector(String connectorKey) async {
    return _client.request<ConnectorStatusModel>(
      MvpEndpoint.settingsConnectorInstall,
      pathParams: {'connectorKey': connectorKey},
      decode: (json) => ConnectorStatusModel.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<ConnectorStatusModel>> revokeConnector(String connectorKey) async {
    return _client.request<ConnectorStatusModel>(
      MvpEndpoint.settingsConnectorRevoke,
      pathParams: {'connectorKey': connectorKey},
      decode: (json) => ConnectorStatusModel.fromJson(json as Map<String, dynamic>),
    );
  }

  // 3. Runtime Nodes
  Future<ApiResult<List<RuntimeNodeModel>>> listRuntimeNodes() async {
    return _client.request<List<RuntimeNodeModel>>(
      MvpEndpoint.settingsRuntimeNodeList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => RuntimeNodeModel.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<Map<String, dynamic>>> revokeRuntimeNode(String nodeId) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.settingsRuntimeNodeRevoke,
      pathParams: {'nodeId': nodeId},
      decode: (json) => json as Map<String, dynamic>,
    );
  }

  // 4. Audit Events
  Future<ApiResult<List<WorkspaceAuditEventModel>>> listAuditEvents() async {
    return _client.request<List<WorkspaceAuditEventModel>>(
      MvpEndpoint.settingsAuditEventList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => WorkspaceAuditEventModel.fromJson(e))
            .toList();
      },
    );
  }

  // 5. Skills
  Future<ApiResult<List<SkillSettingModel>>> listSkills() async {
    return _client.request<List<SkillSettingModel>>(
      MvpEndpoint.settingsSkillList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => SkillSettingModel.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<SkillSettingModel>> updateSkill(
    String skillKey, {
    bool? enabled,
    Map<String, dynamic>? config,
  }) async {
    return _client.request<SkillSettingModel>(
      MvpEndpoint.settingsSkillUpdate,
      pathParams: {'skillKey': skillKey},
      body: {
        'enabled': ?enabled,
        'config': ?config,
      },
      decode: (json) => SkillSettingModel.fromJson(json as Map<String, dynamic>),
    );
  }
}
