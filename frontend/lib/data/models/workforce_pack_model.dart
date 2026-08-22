/// Workforce Pack Model (F4 Specification).
library;

class WorkforcePackModel {
  final String key;
  final String name;
  final String? roleTitle;
  final String? department;
  final String category; // ORCHESTRATOR | DOMAIN | OPTIONAL_DOMAIN | LEGACY
  final bool isCore;
  final bool isActive;
  final String? description;
  final int toolsCount;

  WorkforcePackModel({
    required this.key,
    required this.name,
    this.roleTitle,
    this.department,
    required this.category,
    required this.isCore,
    required this.isActive,
    this.description,
    this.toolsCount = 0,
  });

  factory WorkforcePackModel.fromJson(Map<String, dynamic> json) {
    return WorkforcePackModel(
      key: json['key'] ?? '',
      name: json['name'] ?? '',
      roleTitle: json['role_title'],
      department: json['department'],
      category: json['category'] ?? 'DOMAIN',
      isCore: json['is_core'] ?? true,
      isActive: json['is_active'] ?? true,
      description: json['description'],
      toolsCount: json['tools_count'] ?? 0,
    );
  }
}
