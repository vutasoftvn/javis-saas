class AiComplianceDeployment {
  final String id;
  final String systemVersionId;
  final String status;
  final String ownerName;
  final String? currentAssessmentId;
  final String assessmentExpiresAt;
  final String providerStatus;
  final String mode;
  final List<String> allowedCapabilities;

  const AiComplianceDeployment({
    required this.id,
    this.systemVersionId = '',
    required this.status,
    required this.ownerName,
    this.currentAssessmentId,
    required this.assessmentExpiresAt,
    required this.providerStatus,
    this.mode = 'ADVISORY_ONLY',
    this.allowedCapabilities = const [],
  });

  factory AiComplianceDeployment.fromJson(Map<String, dynamic> json) {
    return AiComplianceDeployment(
      id: json['id']?.toString() ?? '',
      systemVersionId: json['systemVersionId']?.toString() ?? '',
      status: json['status']?.toString() ?? 'DRAFT',
      ownerName: json['ownerName']?.toString() ?? json['owner_name']?.toString() ?? '',
      currentAssessmentId: json['currentAssessmentId']?.toString(),
      assessmentExpiresAt: json['assessmentExpiresAt']?.toString() ?? json['assessment_expires_at']?.toString() ?? '',
      providerStatus: json['providerStatus']?.toString() ?? json['provider_status']?.toString() ?? '',
      mode: json['mode']?.toString() ?? 'ADVISORY_ONLY',
      allowedCapabilities: (json['allowedCapabilities'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? const [],
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'systemVersionId': systemVersionId,
    'status': status,
    'ownerName': ownerName,
    'currentAssessmentId': currentAssessmentId,
    'assessmentExpiresAt': assessmentExpiresAt,
    'providerStatus': providerStatus,
    'mode': mode,
    'allowedCapabilities': allowedCapabilities,
  };
}

class AiIncidentSummary {
  final String id;
  final String deploymentId;
  final String severity;
  final String status;
  final String summary;
  final String createdAt;

  const AiIncidentSummary({
    required this.id,
    this.deploymentId = '',
    required this.severity,
    required this.status,
    required this.summary,
    required this.createdAt,
  });

  factory AiIncidentSummary.fromJson(Map<String, dynamic> json) {
    return AiIncidentSummary(
      id: json['id']?.toString() ?? '',
      deploymentId: json['deploymentId']?.toString() ?? '',
      severity: json['severity']?.toString() ?? 'LOW',
      status: json['status']?.toString() ?? 'OPEN',
      summary: json['summary']?.toString() ?? '',
      createdAt: json['createdAt']?.toString() ?? json['created_at']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'deploymentId': deploymentId,
    'severity': severity,
    'status': status,
    'summary': summary,
    'createdAt': createdAt,
  };
}

class AiComplianceCenterData {
  final List<AiComplianceDeployment> deployments;
  final List<AiIncidentSummary> recentIncidents;
  final int activeCount;
  final int incidentCount;

  const AiComplianceCenterData({
    required this.deployments,
    required this.recentIncidents,
    required this.activeCount,
    required this.incidentCount,
  });

  factory AiComplianceCenterData.fromJson(Map<String, dynamic> json) {
    final deps = (json['deployments'] as List<dynamic>?)
            ?.map((e) => AiComplianceDeployment.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList() ??
        [];
    final rawIncs = json['recentIncidents'] ?? json['incidents'];
    final incs = (rawIncs as List<dynamic>?)
            ?.map((e) => AiIncidentSummary.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList() ??
        [];
    return AiComplianceCenterData(
      deployments: deps,
      recentIncidents: incs,
      activeCount: (json['activeCount'] as num?)?.toInt() ?? deps.where((d) => d.status == 'APPROVED_FOR_USE').length,
      incidentCount: (json['incidentCount'] as num?)?.toInt() ?? incs.length,
    );
  }
}
