import 'package:uuid/uuid.dart';

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/founder_asset.dart';

/// Client cho Founder-configurable asset surface
/// (`operations.founder_asset.command` / `operations.founder_asset.library`
/// trong `shared/contracts/mvp-surface.json`) — clone-only trên built-in
/// Role/Agent/Skill/Workflow, publish version mới immutable. Built-in
/// KHÔNG BAO GIỜ được sửa/xoá trực tiếp qua đây (CLAUDE.md: "Founder-
/// configurable assets" — chỉ clone thành draft rồi publish).
class FounderAssetService {
  final MvpRequestClient _client;
  final Uuid _uuid;

  FounderAssetService({MvpRequestClient? client, Uuid? uuid})
    : _client = client ?? MvpRequestClient(),
      _uuid = uuid ?? const Uuid();

  Future<ApiResult<List<FounderAssetLibraryItem>>> listLibrary() {
    return _client.request<List<FounderAssetLibraryItem>>(
      MvpEndpoint.operationsFounderAssetLibrary,
      decode: (raw) {
        if (raw is List) {
          return raw
              .map((e) => FounderAssetLibraryItem.fromJson(e as Map<String, dynamic>))
              .toList();
        }
        throw const FormatException('Invalid response format for founder asset library');
      },
    );
  }

  /// Clone 1 asset (built-in hoặc asset khác trong workspace) thành draft mới
  /// thuộc `targetScopeWorkspaceId` — giữ lineage `{originAssetId, version}`.
  /// `projectId`/`metadata` (task-8-report.md bước 1) — C2 dùng `metadata: {name,
  /// description}` khi clone AGENT để đặt tên/mô tả ngay lúc tạo draft.
  Future<ApiResult<FounderAssetCommandResult>> cloneAsset({
    required FounderAssetKind assetKind,
    required String sourceAssetId,
    String? sourceVersion,
    required String reason,
    String? projectId,
    Map<String, dynamic>? metadata,
  }) {
    return _commandAsset(
      assetKind: assetKind,
      operation: 'CLONE',
      assetRef: {'assetId': sourceAssetId, 'version': ?sourceVersion},
      reason: reason,
      projectId: projectId,
      metadata: metadata,
    );
  }

  /// Task 9 (C2) bước 3 — sửa nội dung draft (tên/mô tả/addendum/capability_refs). `assetRef`
  /// phải là `updatedAssetRef` của lệnh trước đó (CLONE); `content` là TOÀN BỘ manifest mới
  /// (task-8-report.md mục 3 — khoá lạ sẽ bị backend từ chối).
  Future<ApiResult<FounderAssetCommandResult>> editDraft({
    required FounderAssetKind assetKind,
    required FounderAssetRef assetRef,
    required Map<String, dynamic> content,
    required String reason,
    String? projectId,
  }) {
    return _commandAsset(
      assetKind: assetKind,
      operation: 'EDIT_DRAFT',
      assetRef: {
        'assetId': assetRef.assetId,
        'version': ?assetRef.version,
        'definitionHash': ?assetRef.definitionHash,
      },
      reason: reason,
      projectId: projectId,
      metadata: {'content': content},
    );
  }

  /// Task 9 (C2) bước 4 — đánh giá draft; FAIL/REJECTED trả `safeReasonCode` qua
  /// `getEvents` (task-8-report.md mục 4).
  Future<ApiResult<FounderAssetCommandResult>> evaluate({
    required FounderAssetKind assetKind,
    required FounderAssetRef assetRef,
    required String reason,
    String? projectId,
  }) {
    return _commandAsset(
      assetKind: assetKind,
      operation: 'EVALUATE',
      assetRef: {
        'assetId': assetRef.assetId,
        'version': ?assetRef.version,
        'definitionHash': ?assetRef.definitionHash,
      },
      reason: reason,
      projectId: projectId,
    );
  }

  /// Publish 1 draft đã evaluate PASS — `assetId` + `version` + `expectedHash`
  /// phải khớp CHÍNH XÁC `targetRef` của command EVALUATE gần nhất (optimistic
  /// concurrency, chặn publish nhầm bản đã bị người khác sửa — xem
  /// `sameAssetRef()` phía `founder-asset-authoring.service.ts`).
  Future<ApiResult<FounderAssetCommandResult>> publishAsset({
    required FounderAssetKind assetKind,
    required String assetId,
    required String version,
    required String expectedHash,
    required String reason,
    String? projectId,
  }) {
    return _commandAsset(
      assetKind: assetKind,
      operation: 'PUBLISH',
      assetRef: {'assetId': assetId, 'version': version, 'definitionHash': expectedHash},
      reason: reason,
      projectId: projectId,
    );
  }

  /// Task 9 (C2) bước 2 — poll trạng thái 1 lệnh (`metadata.status` PENDING/SUCCESS/FAILED/
  /// REJECTED). Trả danh sách vì backend có thể ghi nhiều dòng cho cùng `commandId`; caller lấy
  /// dòng mới nhất (task-8-report.md mục 2). Route KHÔNG có trong `mvp-surface.json` enabled
  /// entry cũ — thêm mới ở Task 9 (`operations.founder_asset.events`).
  Future<ApiResult<List<FounderAssetEvent>>> getEvents({required String commandId}) {
    return _client.request<List<FounderAssetEvent>>(
      MvpEndpoint.operationsFounderAssetEvents,
      query: {'commandId': commandId},
      decode: (raw) {
        if (raw is Map<String, dynamic> && raw['events'] is List) {
          return (raw['events'] as List)
              .whereType<Map<String, dynamic>>()
              .map(FounderAssetEvent.fromJson)
              .toList();
        }
        throw const FormatException('Invalid response format for founder asset events');
      },
    );
  }

  /// Task 9 (C2) bước 6 — tạo Workspace Agent từ 1 clone ĐÃ PUBLISH (task-8-report.md mục 6).
  Future<ApiResult<WorkspaceAgentDto>> createWorkspaceAgent({
    required String agentAssetId,
    required String agentAssetVersion,
    required String agentDefinitionHash,
    String? idempotencyKey,
  }) {
    return _client.request<WorkspaceAgentDto>(
      MvpEndpoint.operationsFounderAssetWorkspaceAgentCreate,
      body: {
        'agentAssetId': agentAssetId,
        'agentAssetVersion': agentAssetVersion,
        'agentDefinitionHash': agentDefinitionHash,
        'idempotencyKey': idempotencyKey ?? _uuid.v4(),
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return WorkspaceAgentDto.fromJson(raw);
        }
        throw const FormatException('Invalid response format for workspace agent');
      },
    );
  }

  Future<ApiResult<FounderAssetCommandResult>> _commandAsset({
    required FounderAssetKind assetKind,
    required String operation,
    required Map<String, dynamic> assetRef,
    required String reason,
    String? projectId,
    Map<String, dynamic>? metadata,
  }) {
    return _client.request<FounderAssetCommandResult>(
      MvpEndpoint.operationsFounderAssetCommand,
      body: {
        'assetKind': assetKind.toWire(),
        'operation': operation,
        'assetRef': assetRef,
        'reason': reason,
        'idempotencyKey': _uuid.v4(),
        'projectId': ?projectId,
        'metadata': ?metadata,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return FounderAssetCommandResult.fromJson(raw);
        }
        throw const FormatException('Invalid response format for founder asset command');
      },
    );
  }
}
