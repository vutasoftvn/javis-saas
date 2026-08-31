import 'package:flutter/foundation.dart';

@immutable
class VaultDocument {
  final String documentId;
  final String workspaceId;
  final String title;
  final String kind;
  final String state;
  final String? currentVersionId;
  final String? knowledgeSourceId;
  final String createdBy;
  final DateTime createdAt;
  final DateTime updatedAt;

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
  });

  factory VaultDocument.fromJson(Map<String, dynamic> json) {
    return VaultDocument(
      documentId: json['document_id'] as String? ?? '',
      workspaceId: json['workspace_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      kind: json['kind'] as String? ?? 'document',
      state: json['state'] as String? ?? 'DRAFT',
      currentVersionId: json['current_version_id'] as String?,
      knowledgeSourceId: json['knowledge_source_id'] as String?,
      createdBy: json['created_by'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class VaultDocumentVersion {
  final String versionId;
  final String workspaceId;
  final String documentId;
  final Map<String, dynamic> objectRef;
  final String checksumSha256;
  final int sizeBytes;
  final String sourceUri;
  final String createdBy;
  final DateTime createdAt;

  const VaultDocumentVersion({
    required this.versionId,
    required this.workspaceId,
    required this.documentId,
    required this.objectRef,
    required this.checksumSha256,
    required this.sizeBytes,
    required this.sourceUri,
    required this.createdBy,
    required this.createdAt,
  });

  factory VaultDocumentVersion.fromJson(Map<String, dynamic> json) {
    return VaultDocumentVersion(
      versionId: json['version_id'] as String? ?? '',
      workspaceId: json['workspace_id'] as String? ?? '',
      documentId: json['document_id'] as String? ?? '',
      objectRef: json['object_ref'] as Map<String, dynamic>? ?? {},
      checksumSha256: json['checksum_sha256'] as String? ?? '',
      sizeBytes: json['size_bytes'] as int? ?? 0,
      sourceUri: json['source_uri'] as String? ?? '',
      createdBy: json['created_by'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

@immutable
class VaultDocumentDetail {
  final String documentId;
  final String workspaceId;
  final String title;
  final String kind;
  final String state;
  final String? currentVersionId;
  final String? knowledgeSourceId;
  final String createdBy;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<VaultDocumentVersion> versions;

  const VaultDocumentDetail({
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
    this.versions = const [],
  });

  factory VaultDocumentDetail.fromJson(Map<String, dynamic> json) {
    return VaultDocumentDetail(
      documentId: json['document_id'] as String? ?? '',
      workspaceId: json['workspace_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      kind: json['kind'] as String? ?? 'document',
      state: json['state'] as String? ?? 'DRAFT',
      currentVersionId: json['current_version_id'] as String?,
      knowledgeSourceId: json['knowledge_source_id'] as String?,
      createdBy: json['created_by'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ?? DateTime.now(),
      versions: (json['versions'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map((e) => VaultDocumentVersion.fromJson(e))
              .toList() ??
          [],
    );
  }
}

@immutable
class VaultUploadTicket {
  final String ticketId;
  final String documentId;
  final String uploadUrl;
  final DateTime expiresAt;
  final int maxBytes;
  final String mediaType;

  const VaultUploadTicket({
    required this.ticketId,
    required this.documentId,
    required this.uploadUrl,
    required this.expiresAt,
    required this.maxBytes,
    required this.mediaType,
  });

  factory VaultUploadTicket.fromJson(Map<String, dynamic> json) {
    return VaultUploadTicket(
      ticketId: json['ticket_id'] as String? ?? '',
      documentId: json['document_id'] as String? ?? '',
      uploadUrl: json['upload_url'] as String? ?? '',
      expiresAt: DateTime.tryParse(json['expires_at'] as String? ?? '') ?? DateTime.now(),
      maxBytes: json['max_bytes'] as int? ?? 0,
      mediaType: json['media_type'] as String? ?? 'application/octet-stream',
    );
  }
}

@immutable
class VaultKnowledgeGraphNode {
  final String id;
  final String label;
  final String kind;
  final String sourceRef;
  final Map<String, dynamic> metadata;

  const VaultKnowledgeGraphNode({
    required this.id,
    required this.label,
    required this.kind,
    required this.sourceRef,
    this.metadata = const {},
  });

  factory VaultKnowledgeGraphNode.fromJson(Map<String, dynamic> json) {
    return VaultKnowledgeGraphNode(
      id: json['id'] as String? ?? '',
      label: json['label'] as String? ?? '',
      kind: json['kind'] as String? ?? '',
      sourceRef: json['source_ref'] as String? ?? '',
      metadata: json['metadata'] as Map<String, dynamic>? ?? {},
    );
  }
}

@immutable
class VaultKnowledgeGraphEdge {
  final String sourceId;
  final String targetId;
  final String relation;
  final double weight;

  const VaultKnowledgeGraphEdge({
    required this.sourceId,
    required this.targetId,
    required this.relation,
    this.weight = 1.0,
  });

  factory VaultKnowledgeGraphEdge.fromJson(Map<String, dynamic> json) {
    return VaultKnowledgeGraphEdge(
      sourceId: json['source_id'] as String? ?? '',
      targetId: json['target_id'] as String? ?? '',
      relation: json['relation'] as String? ?? '',
      weight: (json['weight'] as num?)?.toDouble() ?? 1.0,
    );
  }
}

@immutable
class VaultKnowledgeGraph {
  final List<VaultKnowledgeGraphNode> nodes;
  final List<VaultKnowledgeGraphEdge> edges;

  const VaultKnowledgeGraph({
    this.nodes = const [],
    this.edges = const [],
  });

  factory VaultKnowledgeGraph.fromJson(Map<String, dynamic> json) {
    return VaultKnowledgeGraph(
      nodes: (json['nodes'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map((e) => VaultKnowledgeGraphNode.fromJson(e))
              .toList() ??
          [],
      edges: (json['edges'] as List?)
              ?.whereType<Map<String, dynamic>>()
              .map((e) => VaultKnowledgeGraphEdge.fromJson(e))
              .toList() ??
          [],
    );
  }
}

@immutable
class VaultIndexedSource {
  final String sourceId;
  final String workspaceId;
  final String title;
  final String sourceType;
  final String status;
  final int chunkCount;
  final DateTime? indexedAt;

  const VaultIndexedSource({
    required this.sourceId,
    required this.workspaceId,
    required this.title,
    required this.sourceType,
    required this.status,
    this.chunkCount = 0,
    this.indexedAt,
  });

  factory VaultIndexedSource.fromJson(Map<String, dynamic> json) {
    return VaultIndexedSource(
      sourceId: json['source_id'] as String? ?? '',
      workspaceId: json['workspace_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      sourceType: json['source_type'] as String? ?? '',
      status: json['status'] as String? ?? 'INDEXED',
      chunkCount: json['chunk_count'] as int? ?? 0,
      indexedAt: json['indexed_at'] != null ? DateTime.tryParse(json['indexed_at'] as String) : null,
    );
  }
}

@immutable
class VaultRetrievalHit {
  final String sourceId;
  final String title;
  final String content;
  final double score;
  final Map<String, dynamic> metadata;

  const VaultRetrievalHit({
    required this.sourceId,
    required this.title,
    required this.content,
    required this.score,
    this.metadata = const {},
  });

  factory VaultRetrievalHit.fromJson(Map<String, dynamic> json) {
    return VaultRetrievalHit(
      sourceId: json['source_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      content: json['content'] as String? ?? '',
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      metadata: json['metadata'] as Map<String, dynamic>? ?? {},
    );
  }
}
