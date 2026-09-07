import 'package:flutter/foundation.dart';

@immutable
class WorkspaceMemberModel {
  final String id;
  final String workspaceId;
  final String userId;
  final String roleId;
  final String? email;
  final String? fullName;
  final DateTime createdAt;

  const WorkspaceMemberModel({
    required this.id,
    required this.workspaceId,
    required this.userId,
    required this.roleId,
    this.email,
    this.fullName,
    required this.createdAt,
  });

  factory WorkspaceMemberModel.fromJson(Map<String, dynamic> json) {
    return WorkspaceMemberModel(
      id: json['id'] as String? ?? '',
      workspaceId: json['workspaceId'] as String? ?? json['workspace_id'] as String? ?? '',
      userId: json['userId'] as String? ?? json['user_id'] as String? ?? '',
      roleId: json['roleId'] as String? ?? json['role_id'] as String? ?? 'member',
      email: json['email'] as String?,
      fullName: json['fullName'] as String? ?? json['full_name'] as String?,
      createdAt: DateTime.tryParse(json['createdAt'] as String? ?? json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class ConnectorStatusModel {
  final String id;
  final String connectorKey;
  final String state;
  final List<String> grantedScopes;
  final DateTime? observedAt;
  final DateTime? expiresAt;
  final String? reason;

  const ConnectorStatusModel({
    required this.id,
    required this.connectorKey,
    required this.state,
    this.grantedScopes = const [],
    this.observedAt,
    this.expiresAt,
    this.reason,
  });

  factory ConnectorStatusModel.fromJson(Map<String, dynamic> json) {
    return ConnectorStatusModel(
      id: json['id'] as String? ?? '',
      connectorKey: json['connectorKey'] as String? ?? json['connector_key'] as String? ?? '',
      state: json['state'] as String? ?? 'not_connected',
      grantedScopes: (json['grantedScopes'] as List? ?? json['granted_scopes'] as List? ?? []).map((e) => e.toString()).toList(),
      observedAt: json['observedAt'] != null ? DateTime.tryParse(json['observedAt'] as String) : (json['observed_at'] != null ? DateTime.tryParse(json['observed_at'] as String) : null),
      expiresAt: json['expiresAt'] != null ? DateTime.tryParse(json['expiresAt'] as String) : (json['expires_at'] != null ? DateTime.tryParse(json['expires_at'] as String) : null),
      reason: json['reason'] as String?,
    );
  }
}

@immutable
class RuntimeNodeModel {
  final String id;
  final String workspaceId;
  final String nodeId;
  final String runtimeRole;
  final String presence;
  final DateTime? lastHeartbeatAt;
  final String status;

  const RuntimeNodeModel({
    required this.id,
    required this.workspaceId,
    required this.nodeId,
    required this.runtimeRole,
    required this.presence,
    this.lastHeartbeatAt,
    required this.status,
  });

  factory RuntimeNodeModel.fromJson(Map<String, dynamic> json) {
    return RuntimeNodeModel(
      id: json['id'] as String? ?? '',
      workspaceId: json['workspaceId'] as String? ?? json['workspace_id'] as String? ?? '',
      nodeId: json['nodeId'] as String? ?? json['node_id'] as String? ?? '',
      runtimeRole: json['runtimeRole'] as String? ?? json['runtime_role'] as String? ?? '',
      presence: json['presence'] as String? ?? 'OFFLINE',
      lastHeartbeatAt: json['lastHeartbeatAt'] != null ? DateTime.tryParse(json['lastHeartbeatAt'] as String) : (json['last_heartbeat_at'] != null ? DateTime.tryParse(json['last_heartbeat_at'] as String) : null),
      status: json['status'] as String? ?? 'unknown',
    );
  }
}

@immutable
class SkillSettingModel {
  final String id;
  final String skillKey;
  final String name;
  final String description;
  final String version;
  final bool installed;
  final String status;
  final String publisher;
  final String autonomyCeiling;
  final List<String> tags;
  final DateTime updatedAt;
  // Task 4 — control plane (services/cosa) là nguồn sự thật, tăng dần mỗi
  // lần persist thành công. Skill chưa từng có policy nào trả revision 0.
  // SettingsMvpService dùng field này để chặn 1 response cũ/lặp đè lên state
  // mới hơn đã áp dụng cục bộ.
  final int revision;

  const SkillSettingModel({
    required this.id,
    required this.skillKey,
    required this.name,
    required this.description,
    required this.version,
    required this.installed,
    required this.status,
    required this.publisher,
    required this.autonomyCeiling,
    this.tags = const [],
    required this.updatedAt,
    this.revision = 0,
  });

  factory SkillSettingModel.fromJson(Map<String, dynamic> json) {
    return SkillSettingModel(
      id: json['id'] as String? ?? '',
      skillKey: json['skillKey'] as String? ?? json['skill_key'] as String? ?? '',
      name: json['name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      version: json['version'] as String? ?? '1.0.0',
      installed: json['installed'] as bool? ?? false,
      status: json['status'] as String? ?? 'available',
      publisher: json['publisher'] as String? ?? 'cosa_platform',
      autonomyCeiling: json['autonomyCeiling'] as String? ?? json['autonomy_ceiling'] as String? ?? 'supervised',
      tags: (json['tags'] as List? ?? []).map((e) => e.toString()).toList(),
      updatedAt: DateTime.tryParse(json['updatedAt'] as String? ?? json['updated_at'] as String? ?? '') ?? DateTime.now(),
      revision: (json['revision'] as num?)?.toInt() ?? 0,
    );
  }
}

@immutable
class WorkspaceAuditEventModel {
  final String eventId;
  final String workspaceId;
  final String actorId;
  final String eventType;
  final String targetKind;
  final String targetId;
  final dynamic details;
  final DateTime createdAt;

  const WorkspaceAuditEventModel({
    required this.eventId,
    required this.workspaceId,
    required this.actorId,
    required this.eventType,
    required this.targetKind,
    required this.targetId,
    this.details,
    required this.createdAt,
  });

  factory WorkspaceAuditEventModel.fromJson(Map<String, dynamic> json) {
    return WorkspaceAuditEventModel(
      eventId: json['eventId'] as String? ?? json['event_id'] as String? ?? '',
      workspaceId: json['workspaceId'] as String? ?? json['workspace_id'] as String? ?? '',
      actorId: json['actorId'] as String? ?? json['actor_id'] as String? ?? '',
      eventType: json['eventType'] as String? ?? json['event_type'] as String? ?? '',
      targetKind: json['targetKind'] as String? ?? json['target_kind'] as String? ?? '',
      targetId: json['targetId'] as String? ?? json['target_id'] as String? ?? '',
      details: json['details'],
      createdAt: DateTime.tryParse(json['createdAt'] as String? ?? json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

/// Task 4 (plan 2026-09-07-local-first-model-routing) — 1 provider profile
/// đã cấu hình cho workspace. KHÔNG BAO GIỜ có field nào chứa API key — chỉ
/// [credentialConfigured] (bool) cho biết đã có credential hay chưa. Server
/// (`apps/cosa/api/model_policy_schemas.py::ModelProviderDetailView`) đảm bảo
/// điều này ở boundary; model này CHỦ ĐỘNG không khai báo field `apiKey` để
/// không có chỗ nào ở client vô tình mong đợi/parse ra giá trị đó.
@immutable
class ModelProviderModel {
  final String profileId;
  final String providerType;
  final String modelId;
  final bool credentialConfigured;
  final String? baseUrl;
  final List<String> allowedModelIds;
  final double? budgetUsdLimit;
  final int? maxConcurrency;
  final String status;

  const ModelProviderModel({
    required this.profileId,
    required this.providerType,
    required this.modelId,
    required this.credentialConfigured,
    this.baseUrl,
    this.allowedModelIds = const [],
    this.budgetUsdLimit,
    this.maxConcurrency,
    required this.status,
  });

  bool get isActive => status == 'ACTIVE';

  factory ModelProviderModel.fromJson(Map<String, dynamic> json) {
    return ModelProviderModel(
      profileId: json['profileId'] as String? ?? json['profile_id'] as String? ?? '',
      providerType: json['providerType'] as String? ?? json['provider_type'] as String? ?? '',
      modelId: json['modelId'] as String? ?? json['model_id'] as String? ?? '',
      credentialConfigured: json['credentialConfigured'] as bool? ??
          json['credential_configured'] as bool? ??
          false,
      baseUrl: json['baseUrl'] as String? ?? json['base_url'] as String?,
      allowedModelIds: ((json['allowedModelIds'] ?? json['allowed_model_ids']) as List? ?? [])
          .map((e) => e.toString())
          .toList(),
      budgetUsdLimit: ((json['budgetUsdLimit'] ?? json['budget_usd_limit']) as num?)?.toDouble(),
      maxConcurrency: ((json['maxConcurrency'] ?? json['max_concurrency']) as num?)?.toInt(),
      status: json['status'] as String? ?? 'ACTIVE',
    );
  }
}

/// Task 4 — kết quả `POST /agent/settings/model-providers/:profileId/test`.
/// [liveCallAttempted] phân biệt tầng structural (dựng client, giải mã
/// credential) với tầng live-call thật (budget cố định `max_tokens=1`) — UI
/// KHÔNG được tự suy luận "usable" từ việc profile "trông đã cấu hình"; chỉ
/// [ok]=true từ chính response này mới được coi là "đã kiểm tra thành công".
@immutable
class ModelProviderTestResultModel {
  final String profileId;
  final String providerType;
  final String modelId;
  final bool ok;
  final bool liveCallAttempted;
  final String detail;

  const ModelProviderTestResultModel({
    required this.profileId,
    required this.providerType,
    required this.modelId,
    required this.ok,
    required this.liveCallAttempted,
    required this.detail,
  });

  factory ModelProviderTestResultModel.fromJson(Map<String, dynamic> json) {
    return ModelProviderTestResultModel(
      profileId: json['profileId'] as String? ?? json['profile_id'] as String? ?? '',
      providerType: json['providerType'] as String? ?? json['provider_type'] as String? ?? '',
      modelId: json['modelId'] as String? ?? json['model_id'] as String? ?? '',
      ok: json['ok'] as bool? ?? false,
      liveCallAttempted:
          json['liveCallAttempted'] as bool? ?? json['live_call_attempted'] as bool? ?? false,
      detail: json['detail'] as String? ?? '',
    );
  }
}

/// Task 4 — route model đã resolve cho 1 agent_profile, hiển thị precedence
/// (AGENT_PROFILE override > WORKSPACE default > system default) và fallback
/// tường minh. Đây là dữ liệu ĐỌC — client không tự tính lại precedence.
@immutable
class ModelPolicyModel {
  final String scope;
  final String scopeKey;
  final String primaryProfileId;
  final List<String> fallbackProfileIds;
  final String resolvedProfileId;
  final String resolvedProviderType;
  final String resolvedModelId;
  final bool isSystemDefault;

  const ModelPolicyModel({
    required this.scope,
    required this.scopeKey,
    required this.primaryProfileId,
    this.fallbackProfileIds = const [],
    required this.resolvedProfileId,
    required this.resolvedProviderType,
    required this.resolvedModelId,
    required this.isSystemDefault,
  });

  factory ModelPolicyModel.fromJson(Map<String, dynamic> json) {
    return ModelPolicyModel(
      scope: json['scope'] as String? ?? 'WORKSPACE',
      scopeKey: json['scopeKey'] as String? ?? json['scope_key'] as String? ?? '',
      primaryProfileId:
          json['primaryProfileId'] as String? ?? json['primary_profile_id'] as String? ?? '',
      fallbackProfileIds:
          ((json['fallbackProfileIds'] ?? json['fallback_profile_ids']) as List? ?? [])
              .map((e) => e.toString())
              .toList(),
      resolvedProfileId:
          json['resolvedProfileId'] as String? ?? json['resolved_profile_id'] as String? ?? '',
      resolvedProviderType: json['resolvedProviderType'] as String? ??
          json['resolved_provider_type'] as String? ??
          '',
      resolvedModelId:
          json['resolvedModelId'] as String? ?? json['resolved_model_id'] as String? ?? '',
      isSystemDefault:
          json['isSystemDefault'] as bool? ?? json['is_system_default'] as bool? ?? true,
    );
  }
}
