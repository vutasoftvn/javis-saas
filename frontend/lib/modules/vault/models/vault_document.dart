import 'package:flutter/foundation.dart';

/// Task 12 (plan local-first-enterprise-knowledge) — trạng thái document thật
/// từ backend (`apps/cosa/knowledge_ingestion/local_repository.py::LocalIngestionState`
/// nối với `vault.documents.state`). Không suy diễn UI state riêng — hiển thị
/// đúng string backend trả, map sang label/màu ở view.
enum VaultDocumentState {
  draft,
  queued,
  validating,
  converting,
  reviewPending,
  published,
  rejected,
  failed,
  archived,
  purgePending,
  purged,
  unknown;

  static VaultDocumentState fromBackend(String raw) {
    switch (raw) {
      case 'DRAFT':
        return VaultDocumentState.draft;
      case 'QUEUED':
        return VaultDocumentState.queued;
      case 'VALIDATING':
        return VaultDocumentState.validating;
      case 'CONVERTING':
        return VaultDocumentState.converting;
      case 'REVIEW_PENDING':
        return VaultDocumentState.reviewPending;
      case 'PUBLISHED':
        return VaultDocumentState.published;
      case 'REJECTED':
        return VaultDocumentState.rejected;
      case 'FAILED':
        return VaultDocumentState.failed;
      case 'ARCHIVED':
        return VaultDocumentState.archived;
      case 'PURGE_PENDING':
        return VaultDocumentState.purgePending;
      case 'PURGED':
        return VaultDocumentState.purged;
      default:
        return VaultDocumentState.unknown;
    }
  }
}

@immutable
class VaultDocument {
  const VaultDocument({
    required this.documentId,
    required this.workspaceId,
    required this.title,
    required this.kind,
    required this.state,
    this.currentVersionId,
    this.knowledgeSourceId,
    required this.createdBy,
    required this.createdAt,
    required this.updatedAt,
    required this.canReview,
    required this.canPublish,
    required this.canManage,
  });

  final String documentId;
  final String workspaceId;
  final String title;
  final String kind;
  final VaultDocumentState state;
  final String? currentVersionId;
  final String? knowledgeSourceId;
  final String createdBy;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  // Task 12 — render nút review/publish/manage(archive/purge) CHỈ khi backend
  // trả grant tường minh (KnowledgeAuthorization.resolve() phía server) —
  // không tự suy diễn theo role người dùng tự khai ở client.
  final bool canReview;
  final bool canPublish;
  final bool canManage;

  factory VaultDocument.fromJson(Map<String, dynamic> json) {
    return VaultDocument(
      documentId: json['document_id'] as String? ?? '',
      workspaceId: json['workspace_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      kind: json['kind'] as String? ?? 'document',
      state: VaultDocumentState.fromBackend(json['state'] as String? ?? ''),
      currentVersionId: json['current_version_id'] as String?,
      knowledgeSourceId: json['knowledge_source_id'] as String?,
      createdBy: json['created_by'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? ''),
      canReview: json['can_review'] as bool? ?? false,
      canPublish: json['can_publish'] as bool? ?? false,
      canManage: json['can_manage'] as bool? ?? false,
    );
  }
}

@immutable
class VaultDocumentUpload {
  const VaultDocumentUpload({
    required this.documentId,
    required this.uploadId,
    required this.uploadUrl,
    required this.expiresAt,
    required this.maxBytes,
  });

  final String documentId;
  final String uploadId;
  // Opaque, server-generated one-time URL — KHÔNG BAO GIỜ tự dựng URL này ở
  // client (chứa ticket secret trong query, xem apps/cosa/api/vault_routes.py).
  final String uploadUrl;
  final DateTime? expiresAt;
  final int maxBytes;

  factory VaultDocumentUpload.fromJson(Map<String, dynamic> json) {
    return VaultDocumentUpload(
      documentId: json['document_id'] as String? ?? '',
      uploadId: json['upload_id'] as String? ?? '',
      uploadUrl: json['upload_url'] as String? ?? '',
      expiresAt: DateTime.tryParse(json['expires_at'] as String? ?? ''),
      maxBytes: (json['max_bytes'] as num?)?.toInt() ?? 0,
    );
  }
}

@immutable
class VaultUploadStatus {
  const VaultUploadStatus({required this.uploadId, required this.state});

  final String uploadId;
  final String state;

  factory VaultUploadStatus.fromJson(Map<String, dynamic> json) {
    return VaultUploadStatus(
      uploadId: json['upload_id'] as String? ?? '',
      state: json['state'] as String? ?? '',
    );
  }
}

@immutable
class VaultArchiveOrPurgeResult {
  const VaultArchiveOrPurgeResult({required this.documentId, required this.accepted});

  final String documentId;
  final bool accepted;

  factory VaultArchiveOrPurgeResult.fromJson(Map<String, dynamic> json) {
    return VaultArchiveOrPurgeResult(
      documentId: json['document_id'] as String? ?? '',
      accepted: json['accepted'] as bool? ?? false,
    );
  }
}
