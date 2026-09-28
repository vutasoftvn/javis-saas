/// Founder-configurable asset (docs/superpowers/specs/
/// 2026-09-13-founder-configurable-agent-skill-workflow-design.md) —
/// Workspace-scoped clone của một built-in Role/Agent/Skill/Workflow, qua
/// vòng đời CLONE -> EDIT_DRAFT -> EVALUATE -> PUBLISH. Built-in KHÔNG bao
/// giờ sửa/xoá được trực tiếp; đây là bản draft thuộc Workspace.
enum FounderAssetKind {
  agent,
  skill,
  workflow;

  static FounderAssetKind fromWire(String value) {
    switch (value.toUpperCase()) {
      case 'AGENT':
        return FounderAssetKind.agent;
      case 'WORKFLOW':
        return FounderAssetKind.workflow;
      case 'SKILL':
      default:
        return FounderAssetKind.skill;
    }
  }

  String toWire() => name.toUpperCase();
}

class FounderAssetDeploymentCounts {
  final int active;
  final int paused;
  final int retired;

  const FounderAssetDeploymentCounts({
    required this.active,
    required this.paused,
    required this.retired,
  });

  factory FounderAssetDeploymentCounts.fromJson(Map<String, dynamic> json) {
    return FounderAssetDeploymentCounts(
      active: (json['active'] as num?)?.toInt() ?? 0,
      paused: (json['paused'] as num?)?.toInt() ?? 0,
      retired: (json['retired'] as num?)?.toInt() ?? 0,
    );
  }
}

/// Một dòng trong thư viện asset Workspace — trạng thái lineage tổng hợp từ
/// `founder_asset_events` (xem `founder-asset-query.service.ts::listFounderAssetLibrary`).
class FounderAssetLibraryItem {
  final String assetId;
  final FounderAssetKind assetKind;
  final String? originAssetId;
  final String? version;
  final String? definitionHash;
  final String lifecycle;
  final String lastOperation;
  final FounderAssetDeploymentCounts deployments;

  const FounderAssetLibraryItem({
    required this.assetId,
    required this.assetKind,
    required this.lifecycle,
    required this.lastOperation,
    required this.deployments,
    this.originAssetId,
    this.version,
    this.definitionHash,
  });

  bool get isEvaluated =>
      lastOperation == 'EVALUATE' || lastOperation == 'PUBLISH' || lifecycle == 'PASS';

  bool get isPublished => lifecycle == 'PUBLISHED' || lastOperation == 'PUBLISH';

  factory FounderAssetLibraryItem.fromJson(Map<String, dynamic> json) {
    return FounderAssetLibraryItem(
      assetId: json['assetId'] as String? ?? '',
      assetKind: FounderAssetKind.fromWire(json['assetKind'] as String? ?? 'SKILL'),
      originAssetId: json['originAssetId'] as String?,
      version: json['version'] as String?,
      definitionHash: json['definitionHash'] as String?,
      lifecycle: json['lifecycle'] as String? ?? 'PENDING',
      lastOperation: json['lastOperation'] as String? ?? 'CLONE',
      deployments: json['deployments'] is Map<String, dynamic>
          ? FounderAssetDeploymentCounts.fromJson(json['deployments'] as Map<String, dynamic>)
          : const FounderAssetDeploymentCounts(active: 0, paused: 0, retired: 0),
    );
  }
}

/// Kết quả 1 command CLONE/EVALUATE/PUBLISH — luôn `PENDING` ngay sau khi
/// gọi (xử lý async qua outbox -> apps/cosa -> status callback), không phải
/// trạng thái cuối cùng.
class FounderAssetCommandResult {
  final String commandId;
  final String assetKind;
  final String operation;
  final String status;
  final String idempotencyKey;

  const FounderAssetCommandResult({
    required this.commandId,
    required this.assetKind,
    required this.operation,
    required this.status,
    required this.idempotencyKey,
  });

  factory FounderAssetCommandResult.fromJson(Map<String, dynamic> json) {
    return FounderAssetCommandResult(
      commandId: json['commandId'] as String? ?? '',
      assetKind: json['assetKind'] as String? ?? '',
      operation: json['operation'] as String? ?? '',
      status: json['status'] as String? ?? 'PENDING',
      idempotencyKey: json['idempotencyKey'] as String? ?? '',
    );
  }
}

/// Ref tới 1 bản asset chính xác (id + version + hash) — dùng để pin PUBLISH khớp tuyệt đối
/// bản đã EVALUATE PASS (task-8-report.md mục "API/luồng C2").
class FounderAssetRef {
  final String assetId;
  final String? version;
  final String? definitionHash;

  const FounderAssetRef({required this.assetId, this.version, this.definitionHash});

  factory FounderAssetRef.fromJson(Map<String, dynamic> json) => FounderAssetRef(
        assetId: json['assetId'] as String? ?? '',
        version: json['version'] as String?,
        definitionHash: json['definitionHash'] as String?,
      );
}

/// Task 9 (C2) — 1 dòng trả về từ `GET /operations/founder/assets/events?commandId=` (poll
/// trạng thái 1 lệnh CLONE/EDIT_DRAFT/EVALUATE/PUBLISH — task-8-report.md bước 2). Field nằm
/// trong `metadata` (JSONB) phía backend, KHÔNG có bọc `{data, meta}` — xem
/// `getFounderAssetEventsApi` (`services/company/operations/handlers/
/// founder-asset-authoring.handler.ts`).
class FounderAssetEvent {
  final String commandId;
  final String? status;
  final FounderAssetRef? updatedAssetRef;
  final String? safeReasonCode;
  final Map<String, dynamic>? agentManifest;

  const FounderAssetEvent({
    required this.commandId,
    this.status,
    this.updatedAssetRef,
    this.safeReasonCode,
    this.agentManifest,
  });

  bool get isSuccess => status == 'SUCCESS';
  bool get isFailed => status == 'FAILED' || status == 'REJECTED';
  bool get isPending => status == null || status == 'PENDING';

  factory FounderAssetEvent.fromJson(Map<String, dynamic> json) {
    final metadata = json['metadata'] is Map<String, dynamic>
        ? json['metadata'] as Map<String, dynamic>
        : const <String, dynamic>{};
    final updatedRef = metadata['updatedAssetRef'];
    return FounderAssetEvent(
      commandId: (json['id'] ?? json['commandId'])?.toString() ?? '',
      status: metadata['status'] as String?,
      updatedAssetRef:
          updatedRef is Map<String, dynamic> ? FounderAssetRef.fromJson(updatedRef) : null,
      safeReasonCode: metadata['safeReasonCode'] as String?,
      agentManifest:
          metadata['agentManifest'] is Map<String, dynamic> ? metadata['agentManifest'] as Map<String, dynamic> : null,
    );
  }
}

/// Kết quả `POST /operations/founder/assets/workspace-agents` (task-8-report.md bước 6).
class WorkspaceAgentDto {
  final String id;
  final String agentAssetId;
  final String agentAssetVersion;
  final String agentDefinitionHash;
  final String originKind;
  final String state;

  const WorkspaceAgentDto({
    required this.id,
    required this.agentAssetId,
    required this.agentAssetVersion,
    required this.agentDefinitionHash,
    required this.originKind,
    required this.state,
  });

  factory WorkspaceAgentDto.fromJson(Map<String, dynamic> json) => WorkspaceAgentDto(
        id: json['id'] as String? ?? '',
        agentAssetId: json['agentAssetId'] as String? ?? '',
        agentAssetVersion: json['agentAssetVersion'] as String? ?? '',
        agentDefinitionHash: json['agentDefinitionHash'] as String? ?? '',
        originKind: json['originKind'] as String? ?? '',
        state: json['state'] as String? ?? '',
      );
}
