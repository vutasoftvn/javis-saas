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

class AgentCapabilityGrantModel {
  final String id;
  final String workspaceId;
  final String agentWorkforceMemberId;
  final String capabilityId;
  final String? projectId;
  final String? legalEntityId;
  final Map<String, dynamic> constraints;
  final String validFrom;
  final String? validUntil;
  final String status;
  final String? grantedByFounderMemberId;
  final String? revokedAt;
  final String? revokeReason;

  const AgentCapabilityGrantModel({
    required this.id,
    required this.workspaceId,
    required this.agentWorkforceMemberId,
    required this.capabilityId,
    this.projectId,
    this.legalEntityId,
    this.constraints = const {},
    required this.validFrom,
    this.validUntil,
    required this.status,
    this.grantedByFounderMemberId,
    this.revokedAt,
    this.revokeReason,
  });

  factory AgentCapabilityGrantModel.fromJson(Map<String, dynamic> json) {
    return AgentCapabilityGrantModel(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      agentWorkforceMemberId: json['agentWorkforceMemberId']?.toString() ?? '',
      capabilityId: json['capabilityId'] as String? ?? '',
      projectId: json['projectId']?.toString(),
      legalEntityId: json['legalEntityId']?.toString(),
      constraints: (json['constraints'] as Map<String, dynamic>?) ?? {},
      validFrom: json['validFrom'] as String? ?? '',
      validUntil: json['validUntil'] as String?,
      status: json['status'] as String? ?? 'ACTIVE',
      grantedByFounderMemberId: json['grantedByFounderMemberId']?.toString(),
      revokedAt: json['revokedAt'] as String?,
      revokeReason: json['revokeReason'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'workspaceId': workspaceId,
    'agentWorkforceMemberId': agentWorkforceMemberId,
    'capabilityId': capabilityId,
    if (projectId != null) 'projectId': projectId,
    if (legalEntityId != null) 'legalEntityId': legalEntityId,
    'constraints': constraints,
    'validFrom': validFrom,
    if (validUntil != null) 'validUntil': validUntil,
    'status': status,
    if (grantedByFounderMemberId != null) 'grantedByFounderMemberId': grantedByFounderMemberId,
    if (revokedAt != null) 'revokedAt': revokedAt,
    if (revokeReason != null) 'revokeReason': revokeReason,
  };
}

class CapabilityBindingModel {
  final String id;
  final String capabilityId;
  final String permissionKey;
  final String domain;
  final String riskClass;
  final bool approvalRequired;
  final String? description;

  const CapabilityBindingModel({
    required this.id,
    required this.capabilityId,
    required this.permissionKey,
    required this.domain,
    required this.riskClass,
    required this.approvalRequired,
    this.description,
  });

  factory CapabilityBindingModel.fromJson(Map<String, dynamic> json) {
    return CapabilityBindingModel(
      id: json['id']?.toString() ?? '',
      capabilityId: json['capabilityId'] as String? ?? '',
      permissionKey: json['permissionKey'] as String? ?? '',
      domain: json['domain'] as String? ?? '',
      riskClass: json['riskClass'] as String? ?? 'READ',
      approvalRequired: json['approvalRequired'] as bool? ?? false,
      description: json['description'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'capabilityId': capabilityId,
    'permissionKey': permissionKey,
    'domain': domain,
    'riskClass': riskClass,
    'approvalRequired': approvalRequired,
    if (description != null) 'description': description,
  };
}

class AuthorityMemberModel {
  final String id;
  final String workspaceId;
  final String memberType;
  final String? humanUserId;
  final String? agentSpecId;
  final String? roleTitle;
  final String status;

  const AuthorityMemberModel({
    required this.id,
    required this.workspaceId,
    required this.memberType,
    this.humanUserId,
    this.agentSpecId,
    this.roleTitle,
    required this.status,
  });

  factory AuthorityMemberModel.fromJson(Map<String, dynamic> json) {
    return AuthorityMemberModel(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      memberType: json['memberType'] as String? ?? 'HUMAN',
      humanUserId: json['humanUserId']?.toString(),
      agentSpecId: json['agentSpecId'] as String?,
      roleTitle: json['roleTitle'] as String?,
      status: json['status'] as String? ?? 'active',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'workspaceId': workspaceId,
    'memberType': memberType,
    if (humanUserId != null) 'humanUserId': humanUserId,
    if (agentSpecId != null) 'agentSpecId': agentSpecId,
    if (roleTitle != null) 'roleTitle': roleTitle,
    'status': status,
  };
}

class WorkspaceAuthorityOverviewModel {
  final List<WorkspaceRoleModel> roles;
  final List<MemberRoleAssignmentModel> assignments;
  final List<AgentCapabilityGrantModel> grants;
  final List<CapabilityBindingModel> bindings;
  final List<Map<String, dynamic>> events;
  final List<AuthorityMemberModel> members;
  final int authorizationEpoch;
  final int policyVersion;

  const WorkspaceAuthorityOverviewModel({
    required this.roles,
    required this.assignments,
    required this.grants,
    required this.bindings,
    required this.events,
    required this.members,
    required this.authorizationEpoch,
    required this.policyVersion,
  });

  factory WorkspaceAuthorityOverviewModel.fromJson(Map<String, dynamic> json) {
    final rolesList = json['roles'] as List? ?? [];
    final assignmentsList = json['assignments'] as List? ?? [];
    final grantsList = json['grants'] as List? ?? [];
    final bindingsList = json['bindings'] as List? ?? [];
    final eventsList = json['events'] as List? ?? [];
    final membersList = json['members'] as List? ?? [];

    return WorkspaceAuthorityOverviewModel(
      roles: rolesList
          .whereType<Map<String, dynamic>>()
          .map((e) => WorkspaceRoleModel.fromJson(e))
          .toList(),
      assignments: assignmentsList
          .whereType<Map<String, dynamic>>()
          .map((e) => MemberRoleAssignmentModel.fromJson(e))
          .toList(),
      grants: grantsList
          .whereType<Map<String, dynamic>>()
          .map((e) => AgentCapabilityGrantModel.fromJson(e))
          .toList(),
      bindings: bindingsList
          .whereType<Map<String, dynamic>>()
          .map((e) => CapabilityBindingModel.fromJson(e))
          .toList(),
      events: eventsList.whereType<Map<String, dynamic>>().toList(),
      members: membersList
          .whereType<Map<String, dynamic>>()
          .map((e) => AuthorityMemberModel.fromJson(e))
          .toList(),
      authorizationEpoch: (json['authorizationEpoch'] as num?)?.toInt() ?? 1,
      policyVersion: (json['policyVersion'] as num?)?.toInt() ?? 1,
    );
  }
}

