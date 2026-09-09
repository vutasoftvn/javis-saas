// Founder Trial R1 — legacy surface removed from the MVP contract. Every
// request here now returns MvpRequestClient.unavailable(); the retained
// class shell keeps callers compiling until the module is deleted.
// ignore_for_file: unused_field, unused_import, unused_element
import 'package:http/http.dart' as http;

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/settings_models.dart';

class SettingsMvpService {
  final MvpRequestClient _client;

  // Task 4 — state cục bộ (cache theo skillKey) chỉ được cập nhật khi response
  // PUT trả về `revision` LỚN HƠN revision đã biết. Đây là cơ chế chặn
  // "response cũ/lặp bị coi là thành công": ví dụ 1 request PUT bị lặp lại
  // (retry mạng) mà server trả về policy đã cũ hơn state hiện tại (do 1
  // request khác trả về sau xen giữa) sẽ KHÔNG ghi đè state mới hơn.
  final Map<String, SkillSettingModel> _cachedSkillsByKey = {};

  SettingsMvpService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  /// Snapshot state cục bộ hiện biết cho 1 skill (đã qua revision guard),
  /// hoặc `null` nếu chưa từng đọc/ghi thành công cho skill đó.
  SkillSettingModel? cachedSkill(String skillKey) => _cachedSkillsByKey[skillKey];

  // 1. Members
  Future<ApiResult<List<WorkspaceMemberModel>>> listMembers() async {
    return MvpRequestClient.unavailable<List<WorkspaceMemberModel>>('settingsMemberList was removed from the Founder Trial R1 contract');
  }

  // 2. Connectors
  Future<ApiResult<List<ConnectorStatusModel>>> listConnectors() async {
    return MvpRequestClient.unavailable<List<ConnectorStatusModel>>('settingsConnectorList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<ConnectorStatusModel>> installConnector(String connectorKey) async {
    return MvpRequestClient.unavailable<ConnectorStatusModel>('settingsConnectorInstall was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<ConnectorStatusModel>> revokeConnector(String connectorKey) async {
    return MvpRequestClient.unavailable<ConnectorStatusModel>('settingsConnectorRevoke was removed from the Founder Trial R1 contract');
  }

  // 3. Runtime Nodes
  Future<ApiResult<List<RuntimeNodeModel>>> listRuntimeNodes() async {
    return MvpRequestClient.unavailable<List<RuntimeNodeModel>>('settingsRuntimeNodeList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<Map<String, dynamic>>> revokeRuntimeNode(String nodeId) async {
    return MvpRequestClient.unavailable<Map<String, dynamic>>('settingsRuntimeNodeRevoke was removed from the Founder Trial R1 contract');
  }

  // 4. Audit Events
  Future<ApiResult<List<WorkspaceAuditEventModel>>> listAuditEvents() async {
    return MvpRequestClient.unavailable<List<WorkspaceAuditEventModel>>('settingsAuditEventList was removed from the Founder Trial R1 contract');
  }

  // 5. Skills
  Future<ApiResult<List<SkillSettingModel>>> listSkills() async {
    final result = await MvpRequestClient.unavailable<List<SkillSettingModel>>('settingsSkillList was removed from the Founder Trial R1 contract');

    // GET là nguồn đọc đầy đủ nhất từ control plane tại thời điểm gọi — luôn
    // dùng để refresh cache theo revision guard (không áp thẳng vô điều
    // kiện: 1 GET trả về chậm hơn 1 PUT đã áp dụng cục bộ trước đó không
    // được phép làm lùi state).
    if (result is ApiSuccess<List<SkillSettingModel>>) {
      for (final skill in result.data) {
        _applyIfNewerRevision(skill);
      }
    }
    return result;
  }

  Future<ApiResult<SkillSettingModel>> updateSkill(
    String skillKey, {
    bool? enabled,
    Map<String, dynamic>? config,
  }) async {
    final result = await MvpRequestClient.unavailable<SkillSettingModel>('settingsSkillUpdate was removed from the Founder Trial R1 contract');

    // Task 4 — chỉ áp state cục bộ sau `ApiSuccess` có `revision` LỚN HƠN
    // revision hiện tại đã biết cho đúng skillKey này. `ApiResult` trả về
    // caller giữ nguyên (caller vẫn thấy đúng response HTTP thật), nhưng
    // cache nội bộ (`cachedSkill`) không bị 1 response cũ/lặp đè lên.
    if (result is ApiSuccess<SkillSettingModel>) {
      _applyIfNewerRevision(result.data);
    }
    return result;
  }

  void _applyIfNewerRevision(SkillSettingModel incoming) {
    final current = _cachedSkillsByKey[incoming.skillKey];
    if (current == null || incoming.revision > current.revision) {
      _cachedSkillsByKey[incoming.skillKey] = incoming;
    }
  }
}
