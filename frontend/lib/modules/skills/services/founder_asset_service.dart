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
  Future<ApiResult<FounderAssetCommandResult>> cloneAsset({
    required FounderAssetKind assetKind,
    required String sourceAssetId,
    String? sourceVersion,
    required String reason,
  }) {
    return _commandAsset(
      assetKind: assetKind,
      operation: 'CLONE',
      assetRef: {'assetId': sourceAssetId, 'version': ?sourceVersion},
      reason: reason,
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
  }) {
    return _commandAsset(
      assetKind: assetKind,
      operation: 'PUBLISH',
      assetRef: {'assetId': assetId, 'version': version, 'definitionHash': expectedHash},
      reason: reason,
    );
  }

  Future<ApiResult<FounderAssetCommandResult>> _commandAsset({
    required FounderAssetKind assetKind,
    required String operation,
    required Map<String, dynamic> assetRef,
    required String reason,
  }) {
    return _client.request<FounderAssetCommandResult>(
      MvpEndpoint.operationsFounderAssetCommand,
      body: {
        'assetKind': assetKind.toWire(),
        'operation': operation,
        'assetRef': assetRef,
        'reason': reason,
        'idempotencyKey': _uuid.v4(),
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
