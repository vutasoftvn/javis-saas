// Contract Organization typed (spec 2026-09-25 §7) — khớp DTO
// `services/company/operations/services/organization-overview.service.ts`.

class OrganizationOverview {
  const OrganizationOverview({
    required this.organizationId,
    required this.name,
    required this.lifecycleStage,
    required this.viewerRole,
    required this.canManageWorkforce,
    required this.humanMemberCount,
    required this.aiMemberCount,
  });

  final String organizationId;
  final String name;
  final String lifecycleStage;
  final String viewerRole;
  final bool canManageWorkforce;
  final int humanMemberCount;
  final int aiMemberCount;

  factory OrganizationOverview.fromJson(Map<String, dynamic> json) {
    return OrganizationOverview(
      organizationId: _requireString(json, 'organizationId'),
      name: _requireString(json, 'name'),
      lifecycleStage: _requireString(json, 'lifecycleStage'),
      viewerRole: _requireString(json, 'viewerRole'),
      canManageWorkforce: _requireBool(json, 'canManageWorkforce'),
      humanMemberCount: _requireInt(json, 'humanMemberCount'),
      aiMemberCount: _requireInt(json, 'aiMemberCount'),
    );
  }
}

class OrganizationWorkforceMember {
  const OrganizationWorkforceMember({
    required this.id,
    required this.memberType,
    required this.roleTitle,
    required this.managerMemberId,
    required this.status,
    required this.workspaceAgentId,
  });

  final String id;
  final String memberType;
  final String roleTitle;
  final String? managerMemberId;
  final String status;
  final String? workspaceAgentId;

  bool get isAi => memberType == 'AI_AGENT';

  factory OrganizationWorkforceMember.fromJson(Map<String, dynamic> json) {
    final memberType = _requireString(json, 'memberType');
    if (memberType != 'HUMAN' && memberType != 'AI_AGENT') {
      throw FormatException('Unknown memberType: $memberType');
    }
    return OrganizationWorkforceMember(
      id: _requireString(json, 'id'),
      memberType: memberType,
      roleTitle: _requireString(json, 'roleTitle'),
      managerMemberId: json['managerMemberId'] as String?,
      status: _requireString(json, 'status'),
      workspaceAgentId: json['workspaceAgentId'] as String?,
    );
  }
}

class OrganizationWorkforce {
  const OrganizationWorkforce({required this.organizationId, required this.members});

  final String organizationId;
  final List<OrganizationWorkforceMember> members;

  factory OrganizationWorkforce.fromJson(Map<String, dynamic> json) {
    final raw = json['members'];
    if (raw is! List) {
      throw const FormatException('members must be a list');
    }
    return OrganizationWorkforce(
      organizationId: _requireString(json, 'organizationId'),
      members: raw
          .map((m) => OrganizationWorkforceMember.fromJson(m as Map<String, dynamic>))
          .toList(growable: false),
    );
  }
}

String _requireString(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! String || value.isEmpty) {
    throw FormatException('Missing or invalid "$key"');
  }
  return value;
}

bool _requireBool(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! bool) {
    throw FormatException('Missing or invalid "$key"');
  }
  return value;
}

int _requireInt(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! int) {
    throw FormatException('Missing or invalid "$key"');
  }
  return value;
}
