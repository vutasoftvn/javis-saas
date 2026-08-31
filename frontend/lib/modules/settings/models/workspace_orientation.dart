class WorkspaceOrientation {
  const WorkspaceOrientation({
    required this.workspaceId,
    this.vision,
    this.mission,
    this.coreValues,
  });

  final String workspaceId;
  final String? vision;
  final String? mission;
  final String? coreValues;

  bool get hasContent =>
      (vision?.trim().isNotEmpty ?? false) ||
      (mission?.trim().isNotEmpty ?? false) ||
      (coreValues?.trim().isNotEmpty ?? false);

  factory WorkspaceOrientation.fromJson(Map<String, dynamic> json) {
    return WorkspaceOrientation(
      workspaceId: json['id']?.toString() ?? '',
      vision: json['vision'] as String?,
      mission: json['mission'] as String?,
      coreValues: json['coreValues'] as String?,
    );
  }
}
