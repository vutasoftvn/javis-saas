// frontend/lib/data/models/workspace_company_identity_model.dart
class WorkspaceCompanyIdentity {
  const WorkspaceCompanyIdentity({
    required this.workspaceId,
    this.vision,
    this.mission,
    this.coreValues,
  });

  final String workspaceId;
  final String? vision;
  final String? mission;
  final String? coreValues;

  bool get isComplete =>
      (vision?.trim().isNotEmpty ?? false) &&
      (mission?.trim().isNotEmpty ?? false) &&
      (coreValues?.trim().isNotEmpty ?? false);

  factory WorkspaceCompanyIdentity.fromJson(Map<String, dynamic> json) {
    return WorkspaceCompanyIdentity(
      workspaceId: json['id']?.toString() ?? '',
      vision: json['vision'] as String?,
      mission: json['mission'] as String?,
      coreValues: json['coreValues'] as String?,
    );
  }
}
