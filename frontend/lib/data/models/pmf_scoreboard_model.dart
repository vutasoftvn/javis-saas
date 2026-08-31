/// Trạng thái hợp đồng chỉ số
enum MetricContractStatus { draft, active, retired, unknown }

/// Chất lượng của snapshot telemetry
enum MetricSnapshotQuality { valid, stale, incomplete, rejected, unknown }

/// Kết quả phân loại PMF Scoreboard
enum PmfScoreboardResult {
  insufficientData,
  mixed,
  promising,
  concerning,
  unknown,
}

/// Mức độ trưởng thành của từng chiều kích
enum MaturityLevel { notAssessed, early, repeatable, governed, unknown }

/// Model Hợp đồng chỉ số đo lường (Metric Contract)
class MetricContract {
  final String id;
  final String workspaceId;
  final String projectId;
  final String metricKey;
  final String displayName;
  final String unit;
  final MetricContractStatus status;
  final int versionNumber;
  final String? numeratorDefinition;
  final String? denominatorDefinition;
  final String? cohortDefinition;
  final Map<String, dynamic> sourceMapping;
  final String cadence;
  final DateTime? freshUntil;
  final String? decisionUse;
  final String? approvalRef;
  final DateTime createdAt;

  const MetricContract({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.metricKey,
    required this.displayName,
    required this.unit,
    required this.status,
    required this.versionNumber,
    this.numeratorDefinition,
    this.denominatorDefinition,
    this.cohortDefinition,
    this.sourceMapping = const {},
    this.cadence = 'weekly',
    this.freshUntil,
    this.decisionUse,
    this.approvalRef,
    required this.createdAt,
  });

  factory MetricContract.fromJson(Map<String, dynamic> json) {
    MetricContractStatus parseStatus(String? val) {
      switch (val?.toUpperCase()) {
        case 'DRAFT':
          return MetricContractStatus.draft;
        case 'ACTIVE':
          return MetricContractStatus.active;
        case 'RETIRED':
          return MetricContractStatus.retired;
        default:
          return MetricContractStatus.unknown;
      }
    }

    return MetricContract(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString() ?? '',
      metricKey: json['metricKey']?.toString() ?? '',
      displayName: json['displayName']?.toString() ?? '',
      unit: json['unit']?.toString() ?? '',
      status: parseStatus(json['status']?.toString()),
      versionNumber: (json['versionNumber'] as num?)?.toInt() ?? 1,
      numeratorDefinition: json['numeratorDefinition']?.toString(),
      denominatorDefinition: json['denominatorDefinition']?.toString(),
      cohortDefinition: json['cohortDefinition']?.toString(),
      sourceMapping: json['sourceMapping'] is Map<String, dynamic>
          ? json['sourceMapping'] as Map<String, dynamic>
          : {},
      cadence: json['cadence']?.toString() ?? 'weekly',
      freshUntil: json['freshUntil'] != null
          ? DateTime.tryParse(json['freshUntil'].toString())
          : null,
      decisionUse: json['decisionUse']?.toString(),
      approvalRef: json['approvalRef']?.toString(),
      createdAt: json['createdAt'] != null
          ? DateTime.tryParse(json['createdAt'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

/// Model Snapshot dữ liệu chỉ số telemetry
class MetricSnapshot {
  final String id;
  final String workspaceId;
  final String projectId;
  final String contractVersionId;
  final String sourceSystem;
  final String sourceWindow;
  final String sourceRecordId;
  final String payloadHash;
  final DateTime observedAt;
  final DateTime capturedAt;
  final double value;
  final double? numerator;
  final double? denominator;
  final MetricSnapshotQuality qualityStatus;
  final Map<String, dynamic> qualityChecks;
  final String? evidenceIngestionId;

  const MetricSnapshot({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.contractVersionId,
    required this.sourceSystem,
    required this.sourceWindow,
    required this.sourceRecordId,
    required this.payloadHash,
    required this.observedAt,
    required this.capturedAt,
    required this.value,
    this.numerator,
    this.denominator,
    required this.qualityStatus,
    this.qualityChecks = const {},
    this.evidenceIngestionId,
  });

  factory MetricSnapshot.fromJson(Map<String, dynamic> json) {
    MetricSnapshotQuality parseQuality(String? val) {
      switch (val?.toUpperCase()) {
        case 'VALID':
          return MetricSnapshotQuality.valid;
        case 'STALE':
          return MetricSnapshotQuality.stale;
        case 'INCOMPLETE':
          return MetricSnapshotQuality.incomplete;
        case 'REJECTED':
          return MetricSnapshotQuality.rejected;
        default:
          return MetricSnapshotQuality.unknown;
      }
    }

    return MetricSnapshot(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString() ?? '',
      contractVersionId: json['contractVersionId']?.toString() ?? '',
      sourceSystem: json['sourceSystem']?.toString() ?? '',
      sourceWindow: json['sourceWindow']?.toString() ?? '',
      sourceRecordId: json['sourceRecordId']?.toString() ?? '',
      payloadHash: json['payloadHash']?.toString() ?? '',
      observedAt: json['observedAt'] != null
          ? DateTime.tryParse(json['observedAt'].toString()) ?? DateTime.now()
          : DateTime.now(),
      capturedAt: json['capturedAt'] != null
          ? DateTime.tryParse(json['capturedAt'].toString()) ?? DateTime.now()
          : DateTime.now(),
      value: (json['value'] as num?)?.toDouble() ?? 0.0,
      numerator: (json['numerator'] as num?)?.toDouble(),
      denominator: (json['denominator'] as num?)?.toDouble(),
      qualityStatus: parseQuality(json['qualityStatus']?.toString()),
      qualityChecks: json['qualityChecks'] is Map<String, dynamic>
          ? json['qualityChecks'] as Map<String, dynamic>
          : {},
      evidenceIngestionId: json['evidenceIngestionId']?.toString(),
    );
  }
}

/// Thành phần cấu thành điểm số PMF
class ScoreComponent {
  final String componentKey;
  final String sourceType;
  final String sourceId;
  final double rawScore;
  final double weight;
  final double weightedScore;
  final String qualityStatus;
  final String? notes;

  const ScoreComponent({
    required this.componentKey,
    required this.sourceType,
    required this.sourceId,
    required this.rawScore,
    required this.weight,
    required this.weightedScore,
    required this.qualityStatus,
    this.notes,
  });

  factory ScoreComponent.fromJson(Map<String, dynamic> json) {
    return ScoreComponent(
      componentKey: json['componentKey']?.toString() ?? '',
      sourceType: json['sourceType']?.toString() ?? '',
      sourceId: json['sourceId']?.toString() ?? '',
      rawScore: (json['rawScore'] as num?)?.toDouble() ?? 0.0,
      weight: (json['weight'] as num?)?.toDouble() ?? 1.0,
      weightedScore: (json['weightedScore'] as num?)?.toDouble() ?? 0.0,
      qualityStatus: json['qualityStatus']?.toString() ?? '',
      notes: json['notes']?.toString(),
    );
  }
}

/// Lượt tính toán Bảng điểm PMF
class PmfScoreboardRun {
  final String id;
  final String workspaceId;
  final String projectId;
  final List<String> contractVersionIds;
  final List<String> inputSnapshotIds;
  final List<String> reviewedEvidenceIds;
  final String policyVersion;
  final List<ScoreComponent> scoreComponents;
  final List<String> missingDataFlags;
  final List<String> reliabilityFlags;
  final String calculationHash;
  final PmfScoreboardResult result;
  final Map<String, dynamic> humanReviewState;
  final DateTime calculatedAt;

  const PmfScoreboardRun({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    this.contractVersionIds = const [],
    this.inputSnapshotIds = const [],
    this.reviewedEvidenceIds = const [],
    this.policyVersion = 'v1',
    this.scoreComponents = const [],
    this.missingDataFlags = const [],
    this.reliabilityFlags = const [],
    required this.calculationHash,
    required this.result,
    this.humanReviewState = const {},
    required this.calculatedAt,
  });

  factory PmfScoreboardRun.fromJson(Map<String, dynamic> json) {
    PmfScoreboardResult parseResult(String? val) {
      switch (val?.toUpperCase()) {
        case 'INSUFFICIENT_DATA':
          return PmfScoreboardResult.insufficientData;
        case 'MIXED':
          return PmfScoreboardResult.mixed;
        case 'PROMISING':
          return PmfScoreboardResult.promising;
        case 'CONCERNING':
          return PmfScoreboardResult.concerning;
        default:
          return PmfScoreboardResult.unknown;
      }
    }

    final rawComponents = json['scoreComponents'] as List? ?? [];
    final components = rawComponents
        .map((c) => ScoreComponent.fromJson(c as Map<String, dynamic>))
        .toList();

    return PmfScoreboardRun(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString() ?? '',
      contractVersionIds: (json['contractVersionIds'] as List? ?? [])
          .map((e) => e.toString())
          .toList(),
      inputSnapshotIds: (json['inputSnapshotIds'] as List? ?? [])
          .map((e) => e.toString())
          .toList(),
      reviewedEvidenceIds: (json['reviewedEvidenceIds'] as List? ?? [])
          .map((e) => e.toString())
          .toList(),
      policyVersion: json['policyVersion']?.toString() ?? 'v1',
      scoreComponents: components,
      missingDataFlags: (json['missingDataFlags'] as List? ?? [])
          .map((e) => e.toString())
          .toList(),
      reliabilityFlags: (json['reliabilityFlags'] as List? ?? [])
          .map((e) => e.toString())
          .toList(),
      calculationHash: json['calculationHash']?.toString() ?? '',
      result: parseResult(json['result']?.toString()),
      humanReviewState: json['humanReviewState'] is Map<String, dynamic>
          ? json['humanReviewState'] as Map<String, dynamic>
          : {},
      calculatedAt: json['calculatedAt'] != null
          ? DateTime.tryParse(json['calculatedAt'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

/// Chi tiết một chiều kích trưởng thành
class MaturityDimension {
  final MaturityLevel level;
  final String rationale;
  final List<String> missingEvidence;

  const MaturityDimension({
    required this.level,
    required this.rationale,
    this.missingEvidence = const [],
  });

  factory MaturityDimension.fromJson(Map<String, dynamic> json) {
    MaturityLevel parseLevel(String? val) {
      switch (val?.toUpperCase()) {
        case 'NOT_ASSESSED':
          return MaturityLevel.notAssessed;
        case 'EARLY':
          return MaturityLevel.early;
        case 'REPEATABLE':
          return MaturityLevel.repeatable;
        case 'GOVERNED':
          return MaturityLevel.governed;
        default:
          return MaturityLevel.unknown;
      }
    }

    return MaturityDimension(
      level: parseLevel(json['level']?.toString()),
      rationale: json['rationale']?.toString() ?? '',
      missingEvidence: (json['missingEvidence'] as List? ?? [])
          .map((e) => e.toString())
          .toList(),
    );
  }
}

/// Đánh giá mức độ trưởng thành (Maturity Assessment)
class MaturityAssessment {
  final String id;
  final String workspaceId;
  final String projectId;
  final String? scoreboardRunId;
  final MaturityDimension measurement;
  final MaturityDimension value;
  final MaturityDimension retention;
  final MaturityDimension commercial;
  final MaturityDimension operational;
  final DateTime assessedAt;

  const MaturityAssessment({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    this.scoreboardRunId,
    required this.measurement,
    required this.value,
    required this.retention,
    required this.commercial,
    required this.operational,
    required this.assessedAt,
  });

  factory MaturityAssessment.fromJson(Map<String, dynamic> json) {
    final dims = json['dimensions'] as Map<String, dynamic>? ?? {};

    return MaturityAssessment(
      id: json['id']?.toString() ?? '',
      workspaceId: json['workspaceId']?.toString() ?? '',
      projectId: json['projectId']?.toString() ?? '',
      scoreboardRunId: json['scoreboardRunId']?.toString(),
      measurement: MaturityDimension.fromJson(
        dims['measurement'] as Map<String, dynamic>? ?? {},
      ),
      value: MaturityDimension.fromJson(
        dims['value'] as Map<String, dynamic>? ?? {},
      ),
      retention: MaturityDimension.fromJson(
        dims['retention'] as Map<String, dynamic>? ?? {},
      ),
      commercial: MaturityDimension.fromJson(
        dims['commercial'] as Map<String, dynamic>? ?? {},
      ),
      operational: MaturityDimension.fromJson(
        dims['operational'] as Map<String, dynamic>? ?? {},
      ),
      assessedAt: json['assessedAt'] != null
          ? DateTime.tryParse(json['assessedAt'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}
