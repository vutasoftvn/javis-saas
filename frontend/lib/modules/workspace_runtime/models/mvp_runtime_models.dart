import '../../../core/network/api_result.dart';

class MvpRuntimeItem {
  final String id;
  final String workspaceId;
  final String sourceKind;
  final String sourceId;
  final String title;
  final String? description;
  final String state;
  final String severity;
  final ApiSourceRef sourceRef;
  final String? actionUrl;
  final String createdAt;
  final String observedAt;

  const MvpRuntimeItem({
    required this.id,
    required this.workspaceId,
    required this.sourceKind,
    required this.sourceId,
    required this.title,
    this.description,
    required this.state,
    required this.severity,
    required this.sourceRef,
    this.actionUrl,
    required this.createdAt,
    required this.observedAt,
  });

  factory MvpRuntimeItem.fromJson(Map<String, dynamic> json) {
    final rawRef = json['sourceRef'] as Map<String, dynamic>? ?? {};
    final sourceRef = ApiSourceRef(
      kind: rawRef['kind'] as String? ?? json['sourceKind']?.toString() ?? 'unknown',
      ref: rawRef['ref'] as String? ?? json['sourceId']?.toString() ?? '',
      observedAt: rawRef['observed_at'] != null || rawRef['observedAt'] != null
          ? DateTime.tryParse((rawRef['observed_at'] ?? rawRef['observedAt']).toString())
          : null,
    );

    return MvpRuntimeItem(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      sourceKind: json['sourceKind']?.toString() ?? '',
      sourceId: json['sourceId']?.toString() ?? '',
      title: json['title'] as String? ?? '',
      description: json['description'] as String?,
      state: json['state'] as String? ?? '',
      severity: json['severity'] as String? ?? 'MEDIUM',
      sourceRef: sourceRef,
      actionUrl: json['actionUrl'] as String?,
      createdAt: json['createdAt'] as String? ?? '',
      observedAt: json['observedAt'] as String? ?? '',
    );
  }
}

class MvpRuntimeItemDetail extends MvpRuntimeItem {
  final Map<String, dynamic> payload;
  final List<String> dependencies;

  const MvpRuntimeItemDetail({
    required super.id,
    required super.workspaceId,
    required super.sourceKind,
    required super.sourceId,
    required super.title,
    super.description,
    required super.state,
    required super.severity,
    required super.sourceRef,
    super.actionUrl,
    required super.createdAt,
    required super.observedAt,
    required this.payload,
    required this.dependencies,
  });

  factory MvpRuntimeItemDetail.fromJson(Map<String, dynamic> json) {
    final item = MvpRuntimeItem.fromJson(json);
    final rawDeps = json['dependencies'] as List<dynamic>? ?? [];
    return MvpRuntimeItemDetail(
      id: item.id,
      workspaceId: item.workspaceId,
      sourceKind: item.sourceKind,
      sourceId: item.sourceId,
      title: item.title,
      description: item.description,
      state: item.state,
      severity: item.severity,
      sourceRef: item.sourceRef,
      actionUrl: item.actionUrl,
      createdAt: item.createdAt,
      observedAt: item.observedAt,
      payload: json['payload'] as Map<String, dynamic>? ?? {},
      dependencies: rawDeps.map((d) => d.toString()).toList(),
    );
  }
}

class MvpSourceStatus {
  final String sourceKind;
  final String plane;
  final String status;
  final String lastObservedAt;

  const MvpSourceStatus({
    required this.sourceKind,
    required this.plane,
    required this.status,
    required this.lastObservedAt,
  });

  factory MvpSourceStatus.fromJson(Map<String, dynamic> json) {
    return MvpSourceStatus(
      sourceKind: json['sourceKind'] as String? ?? '',
      plane: json['plane'] as String? ?? '',
      status: json['status'] as String? ?? 'HEALTHY',
      lastObservedAt: json['lastObservedAt'] as String? ?? '',
    );
  }
}
