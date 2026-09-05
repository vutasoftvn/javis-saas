class PermissionDefinitionModel {
  final String permissionKey;
  final String domain;
  final String? description;

  const PermissionDefinitionModel({
    required this.permissionKey,
    required this.domain,
    this.description,
  });

  factory PermissionDefinitionModel.fromJson(Map<String, dynamic> json) {
    return PermissionDefinitionModel(
      permissionKey: json['permissionKey'] as String? ?? '',
      domain: json['domain'] as String? ?? '',
      description: json['description'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
    'permissionKey': permissionKey,
    'domain': domain,
    'description': description,
  };
}

class RolePermissionModel {
  final String permissionKey;
  final String effect;
  final Map<String, dynamic> conditions;

  const RolePermissionModel({
    required this.permissionKey,
    required this.effect,
    required this.conditions,
  });

  factory RolePermissionModel.fromJson(Map<String, dynamic> json) {
    return RolePermissionModel(
      permissionKey: json['permissionKey'] as String? ?? '',
      effect: json['effect'] as String? ?? 'DENY',
      conditions: (json['conditions'] as Map<String, dynamic>?) ?? {},
    );
  }

  Map<String, dynamic> toJson() => {
    'permissionKey': permissionKey,
    'effect': effect,
    'conditions': conditions,
  };
}

class WorkspaceRoleModel {
  final String id;
  final String roleKey;
  final String name;
  final bool isSystem;
  final List<RolePermissionModel> permissions;

  const WorkspaceRoleModel({
    required this.id,
    required this.roleKey,
    required this.name,
    required this.isSystem,
    required this.permissions,
  });

  factory WorkspaceRoleModel.fromJson(Map<String, dynamic> json) {
    final permsList = json['permissions'] as List? ?? [];
    return WorkspaceRoleModel(
      id: json['id'] as String? ?? '',
      roleKey: json['roleKey'] as String? ?? '',
      name: json['name'] as String? ?? '',
      isSystem: json['isSystem'] as bool? ?? false,
      permissions: permsList
          .whereType<Map<String, dynamic>>()
          .map((e) => RolePermissionModel.fromJson(e))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'roleKey': roleKey,
    'name': name,
    'isSystem': isSystem,
    'permissions': permissions.map((p) => p.toJson()).toList(),
  };
}

class MemberRoleAssignmentModel {
  final String id;
  final String workforceMemberId;
  final String roleId;
  final String? roleKey;
  final String? roleName;
  final String? projectId;
  final String? legalEntityId;
  final String validFrom;
  final String? validUntil;

  const MemberRoleAssignmentModel({
    required this.id,
    required this.workforceMemberId,
    required this.roleId,
    this.roleKey,
    this.roleName,
    this.projectId,
    this.legalEntityId,
    required this.validFrom,
    this.validUntil,
  });

  factory MemberRoleAssignmentModel.fromJson(Map<String, dynamic> json) {
    return MemberRoleAssignmentModel(
      id: json['id'] as String? ?? '',
      workforceMemberId: json['workforceMemberId'] as String? ?? '',
      roleId: json['roleId'] as String? ?? '',
      roleKey: json['roleKey'] as String?,
      roleName: json['roleName'] as String?,
      projectId: json['projectId'] as String?,
      legalEntityId: json['legalEntityId'] as String?,
      validFrom: json['validFrom'] as String? ?? '',
      validUntil: json['validUntil'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'workforceMemberId': workforceMemberId,
    'roleId': roleId,
    if (roleKey != null) 'roleKey': roleKey,
    if (roleName != null) 'roleName': roleName,
    if (projectId != null) 'projectId': projectId,
    if (legalEntityId != null) 'legalEntityId': legalEntityId,
    'validFrom': validFrom,
    if (validUntil != null) 'validUntil': validUntil,
  };
}

class PermissionsDataModel {
  final List<PermissionDefinitionModel> catalog;
  final List<WorkspaceRoleModel> roles;
  final List<MemberRoleAssignmentModel> assignments;
  final int version;
  final Map<String, String> effectivePermissions;

  const PermissionsDataModel({
    required this.catalog,
    required this.roles,
    required this.assignments,
    required this.version,
    required this.effectivePermissions,
  });

  factory PermissionsDataModel.fromJson(Map<String, dynamic> json) {
    final catalogList = json['catalog'] as List? ?? [];
    final rolesList = json['roles'] as List? ?? [];
    final assignmentsList = json['assignments'] as List? ?? [];
    final effectiveMap = json['effectivePermissions'] as Map<String, dynamic>? ?? {};

    return PermissionsDataModel(
      catalog: catalogList
          .whereType<Map<String, dynamic>>()
          .map((e) => PermissionDefinitionModel.fromJson(e))
          .toList(),
      roles: rolesList
          .whereType<Map<String, dynamic>>()
          .map((e) => WorkspaceRoleModel.fromJson(e))
          .toList(),
      assignments: assignmentsList
          .whereType<Map<String, dynamic>>()
          .map((e) => MemberRoleAssignmentModel.fromJson(e))
          .toList(),
      version: json['version'] as int? ?? 1,
      effectivePermissions: effectiveMap.map(
        (k, v) => MapEntry(k, v.toString()),
      ),
    );
  }

  Map<String, dynamic> toJson() => {
    'catalog': catalog.map((c) => c.toJson()).toList(),
    'roles': roles.map((r) => r.toJson()).toList(),
    'assignments': assignments.map((a) => a.toJson()).toList(),
    'version': version,
    'effectivePermissions': effectivePermissions,
  };
}

class SimulateImpactModel {
  final String memberId;
  final String action;
  final String effect;
  final String reason;

  const SimulateImpactModel({
    required this.memberId,
    required this.action,
    required this.effect,
    required this.reason,
  });

  factory SimulateImpactModel.fromJson(Map<String, dynamic> json) {
    return SimulateImpactModel(
      memberId: json['memberId'] as String? ?? '',
      action: json['action'] as String? ?? '',
      effect: json['effect'] as String? ?? 'DENY',
      reason: json['reason'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'memberId': memberId,
    'action': action,
    'effect': effect,
    'reason': reason,
  };
}

class SimulatePermissionsResponse {
  final Map<String, dynamic> decision;
  final List<SimulateImpactModel> impacts;

  const SimulatePermissionsResponse({
    required this.decision,
    required this.impacts,
  });

  factory SimulatePermissionsResponse.fromJson(Map<String, dynamic> json) {
    final impactsList = json['impacts'] as List? ?? [];
    return SimulatePermissionsResponse(
      decision: (json['decision'] as Map<String, dynamic>?) ?? {},
      impacts: impactsList
          .whereType<Map<String, dynamic>>()
          .map((e) => SimulateImpactModel.fromJson(e))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
    'decision': decision,
    'impacts': impacts.map((i) => i.toJson()).toList(),
  };
}
