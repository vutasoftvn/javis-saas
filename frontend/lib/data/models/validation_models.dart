class ValidationSessionModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final String currentTopic;
  final String workflowState;
  final bool interviewModeActive;
  final Map<String, dynamic> fieldsStatus;
  final DateTime createdAt;
  final DateTime updatedAt;

  ValidationSessionModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.currentTopic,
    required this.workflowState,
    required this.interviewModeActive,
    required this.fieldsStatus,
    required this.createdAt,
    required this.updatedAt,
  });

  factory ValidationSessionModel.fromJson(Map<String, dynamic> json) {
    return ValidationSessionModel(
      id: json['id'] as int,
      workspaceId: json['workspace_id'] as int,
      projectId: json['project_id'] as int,
      currentTopic: json['current_topic'] ?? 'CUSTOMER',
      workflowState: json['workflow_state'] ?? 'DATA_COLLECTION',
      interviewModeActive: json['interview_mode_active'] ?? false,
      fieldsStatus: json['fields_status_jsonb'] is Map<String, dynamic>
          ? json['fields_status_jsonb'] as Map<String, dynamic>
          : {},
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}

class StructuredClaimModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final int? sessionId;
  final String dimension;
  final String subject;
  final String predicate;
  final dynamic value;
  final String epistemicType;
  final String confirmationStatus;
  final String sourceType;
  final String sourceActor;
  final String? sourceRef;
  final double confidence;
  final int? supersedesId;
  final DateTime createdAt;
  final DateTime updatedAt;

  StructuredClaimModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    this.sessionId,
    required this.dimension,
    required this.subject,
    required this.predicate,
    required this.value,
    required this.epistemicType,
    required this.confirmationStatus,
    required this.sourceType,
    required this.sourceActor,
    this.sourceRef,
    required this.confidence,
    this.supersedesId,
    required this.createdAt,
    required this.updatedAt,
  });

  factory StructuredClaimModel.fromJson(Map<String, dynamic> json) {
    return StructuredClaimModel(
      id: json['id'] as int,
      workspaceId: json['workspace_id'] as int,
      projectId: json['project_id'] as int,
      sessionId: json['session_id'] as int?,
      dimension: json['dimension'] ?? '',
      subject: json['subject'] ?? '',
      predicate: json['predicate'] ?? '',
      value: json['value_jsonb'] ?? json['value'] ?? {},
      epistemicType: json['epistemic_type'] ?? 'ASSUMPTION',
      confirmationStatus: json['confirmation_status'] ?? 'AI_INFERRED',
      sourceType: json['source_type'] ?? 'FOUNDER_CHAT',
      sourceActor: json['source_actor'] ?? 'FOUNDER',
      sourceRef: json['source_ref'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 1.0,
      supersedesId: json['supersedes_id'] as int?,
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}

class ClusterSummaryModel {
  final String title;
  final List<String> summaryItems;
  final String status;

  ClusterSummaryModel({
    required this.title,
    required this.summaryItems,
    required this.status,
  });

  factory ClusterSummaryModel.fromJson(Map<String, dynamic> json) {
    return ClusterSummaryModel(
      title: json['title'] ?? 'SNAPSHOT',
      summaryItems: (json['summary_items'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      status: json['status'] ?? 'ASSUMPTION',
    );
  }
}

class ValidationChatResponseModel {
  final int sessionId;
  final String currentTopic;
  final String aiReply;
  final List<Map<String, dynamic>> extractedClaims;
  final bool isTopicClusterComplete;
  final ClusterSummaryModel? clusterSummary;
  final List<String> nextQuestions;
  final String? suggestedNextTopic;

  ValidationChatResponseModel({
    required this.sessionId,
    required this.currentTopic,
    required this.aiReply,
    required this.extractedClaims,
    required this.isTopicClusterComplete,
    this.clusterSummary,
    required this.nextQuestions,
    this.suggestedNextTopic,
  });

  factory ValidationChatResponseModel.fromJson(Map<String, dynamic> json) {
    return ValidationChatResponseModel(
      sessionId: json['session_id'] as int,
      currentTopic: json['current_topic'] ?? 'CUSTOMER',
      aiReply: json['ai_reply'] ?? '',
      extractedClaims: (json['extracted_claims'] as List<dynamic>?)
              ?.map((e) => e as Map<String, dynamic>)
              .toList() ??
          [],
      isTopicClusterComplete: json['is_topic_cluster_complete'] ?? false,
      clusterSummary: json['cluster_summary'] != null
          ? ClusterSummaryModel.fromJson(
              json['cluster_summary'] as Map<String, dynamic>)
          : null,
      nextQuestions: (json['next_questions'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      suggestedNextTopic: json['suggested_next_topic'] as String?,
    );
  }
}

class DimensionStateModel {
  final String dimension;
  final String pillar;
  final String state;
  final double confidence;
  final String? summary;
  final DateTime updatedAt;

  DimensionStateModel({
    required this.dimension,
    required this.pillar,
    required this.state,
    required this.confidence,
    this.summary,
    required this.updatedAt,
  });

  factory DimensionStateModel.fromJson(Map<String, dynamic> json) {
    return DimensionStateModel(
      dimension: json['dimension'] ?? '',
      pillar: json['pillar'] ?? 'DESIRABILITY',
      state: json['state'] ?? 'UNKNOWN',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      summary: json['summary'] as String?,
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}

class StateVectorModel {
  final int projectId;
  final String projectStage;
  final String workflowState;
  final double overallConfidence;
  final Map<String, DimensionStateModel> dimensions;
  final int criticalAssumptionsCount;
  final int activeExperimentsCount;
  final String? primaryNextBestAction;

  StateVectorModel({
    required this.projectId,
    required this.projectStage,
    required this.workflowState,
    required this.overallConfidence,
    required this.dimensions,
    required this.criticalAssumptionsCount,
    required this.activeExperimentsCount,
    this.primaryNextBestAction,
  });

  factory StateVectorModel.fromJson(Map<String, dynamic> json) {
    final dimsMap = <String, DimensionStateModel>{};
    if (json['dimensions'] is Map) {
      (json['dimensions'] as Map).forEach((k, v) {
        if (v is Map<String, dynamic>) {
          dimsMap[k.toString()] = DimensionStateModel.fromJson(v);
        }
      });
    }

    return StateVectorModel(
      projectId: json['project_id'] as int,
      projectStage: json['project_stage'] ?? 'IDEA',
      workflowState: json['workflow_state'] ?? 'DATA_COLLECTION',
      overallConfidence: (json['overall_confidence'] as num?)?.toDouble() ?? 0.0,
      dimensions: dimsMap,
      criticalAssumptionsCount: json['critical_assumptions_count'] as int? ?? 0,
      activeExperimentsCount: json['active_experiments_count'] as int? ?? 0,
      primaryNextBestAction: json['primary_next_best_action'] as String?,
    );
  }
}

class ValidationAssumptionModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final int? claimId;
  final String category;
  final String statement;
  final int importance;
  final int uncertainty;
  final int impact;
  final int riskScore;
  final String source;
  final String status;
  final double confidence;
  final String? owner;
  final DateTime createdAt;

  ValidationAssumptionModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    this.claimId,
    required this.category,
    required this.statement,
    required this.importance,
    required this.uncertainty,
    required this.impact,
    required this.riskScore,
    required this.source,
    required this.status,
    required this.confidence,
    this.owner,
    required this.createdAt,
  });

  factory ValidationAssumptionModel.fromJson(Map<String, dynamic> json) {
    return ValidationAssumptionModel(
      id: json['id'] as int,
      workspaceId: json['workspace_id'] as int,
      projectId: json['project_id'] as int,
      claimId: json['claim_id'] as int?,
      category: json['category'] ?? 'CUSTOMER',
      statement: json['statement'] ?? '',
      importance: json['importance'] as int? ?? 3,
      uncertainty: json['uncertainty'] as int? ?? 3,
      impact: json['impact'] as int? ?? 3,
      riskScore: json['risk_score'] as int? ?? 9,
      source: json['source'] ?? 'FOUNDER_CHAT',
      status: json['status'] ?? 'UNTESTED',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.5,
      owner: json['owner'] as String?,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class ValidationHypothesisModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final int assumptionId;
  final String action;
  final String targetSegment;
  final String metric;
  final String threshold;
  final int timeframeDays;
  final String statement;
  final bool qualityGatePassed;
  final String status;
  final DateTime createdAt;

  ValidationHypothesisModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.assumptionId,
    required this.action,
    required this.targetSegment,
    required this.metric,
    required this.threshold,
    required this.timeframeDays,
    required this.statement,
    required this.qualityGatePassed,
    required this.status,
    required this.createdAt,
  });

  factory ValidationHypothesisModel.fromJson(Map<String, dynamic> json) {
    return ValidationHypothesisModel(
      id: json['id'] as int,
      workspaceId: json['workspace_id'] as int,
      projectId: json['project_id'] as int,
      assumptionId: json['assumption_id'] as int,
      action: json['action'] ?? '',
      targetSegment: json['target_segment'] ?? '',
      metric: json['metric'] ?? '',
      threshold: json['threshold'] ?? '',
      timeframeDays: json['timeframe_days'] as int? ?? 7,
      statement: json['statement'] ?? '',
      qualityGatePassed: json['quality_gate_passed'] ?? false,
      status: json['status'] ?? 'DRAFT',
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class ValidationExperimentModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final int hypothesisId;
  final String experimentType;
  final String name;
  final String? description;
  final String? smallestUsefulScope;
  final String successThreshold;
  final double budgetAmount;
  final int durationDays;
  final String status;
  final String? resultsSummary;
  final DateTime createdAt;

  ValidationExperimentModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    required this.hypothesisId,
    required this.experimentType,
    required this.name,
    this.description,
    this.smallestUsefulScope,
    required this.successThreshold,
    required this.budgetAmount,
    required this.durationDays,
    required this.status,
    this.resultsSummary,
    required this.createdAt,
  });

  factory ValidationExperimentModel.fromJson(Map<String, dynamic> json) {
    return ValidationExperimentModel(
      id: json['id'] as int,
      workspaceId: json['workspace_id'] as int,
      projectId: json['project_id'] as int,
      hypothesisId: json['hypothesis_id'] as int,
      experimentType: json['experiment_type'] ?? 'CUSTOMER_INTERVIEW',
      name: json['name'] ?? '',
      description: json['description'] as String?,
      smallestUsefulScope: json['smallest_useful_scope'] as String?,
      successThreshold: json['success_threshold'] ?? '',
      budgetAmount: (json['budget_amount'] as num?)?.toDouble() ?? 0.0,
      durationDays: json['duration_days'] as int? ?? 7,
      status: json['status'] ?? 'DRAFT',
      resultsSummary: json['results_summary'] as String?,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class ValidationEvidenceModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final int? assumptionId;
  final int? hypothesisId;
  final int? experimentId;
  final String evidenceType;
  final String sourceType;
  final String? sourceRef;
  final String observation;
  final String? metricName;
  final String? metricValue;
  final String relationship;
  final double confidence;
  final DateTime capturedAt;

  ValidationEvidenceModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    this.assumptionId,
    this.hypothesisId,
    this.experimentId,
    required this.evidenceType,
    required this.sourceType,
    this.sourceRef,
    required this.observation,
    this.metricName,
    this.metricValue,
    required this.relationship,
    required this.confidence,
    required this.capturedAt,
  });

  factory ValidationEvidenceModel.fromJson(Map<String, dynamic> json) {
    return ValidationEvidenceModel(
      id: json['id'] as int,
      workspaceId: json['workspace_id'] as int,
      projectId: json['project_id'] as int,
      assumptionId: json['assumption_id'] as int?,
      hypothesisId: json['hypothesis_id'] as int?,
      experimentId: json['experiment_id'] as int?,
      evidenceType: json['evidence_type'] ?? 'FOUNDER_BELIEF',
      sourceType: json['source_type'] ?? '',
      sourceRef: json['source_ref'] as String?,
      observation: json['observation'] ?? '',
      metricName: json['metric_name'] as String?,
      metricValue: json['metric_value'] as String?,
      relationship: json['relationship'] ?? 'SUPPORTS',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.5,
      capturedAt: DateTime.parse(json['captured_at']),
    );
  }
}

class RiskQuadrantItemModel {
  final int id;
  final String category;
  final String statement;
  final int importance;
  final int uncertainty;
  final int riskScore;
  final String status;
  final double confidence;

  RiskQuadrantItemModel({
    required this.id,
    required this.category,
    required this.statement,
    required this.importance,
    required this.uncertainty,
    required this.riskScore,
    required this.status,
    required this.confidence,
  });

  factory RiskQuadrantItemModel.fromJson(Map<String, dynamic> json) {
    return RiskQuadrantItemModel(
      id: json['id'] as int,
      category: json['category'] ?? 'CUSTOMER',
      statement: json['statement'] ?? '',
      importance: json['importance'] as int? ?? 3,
      uncertainty: json['uncertainty'] as int? ?? 3,
      riskScore: json['risk_score'] as int? ?? 9,
      status: json['status'] ?? 'UNTESTED',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.5,
    );
  }
}

class RiskMatrixModel {
  final int projectId;
  final List<RiskQuadrantItemModel> criticalRisks;
  final List<RiskQuadrantItemModel> monitorRisks;
  final List<RiskQuadrantItemModel> exploratoryRisks;
  final List<RiskQuadrantItemModel> lowRisks;
  final int totalAssumptions;
  final int highestRiskScore;

  RiskMatrixModel({
    required this.projectId,
    required this.criticalRisks,
    required this.monitorRisks,
    required this.exploratoryRisks,
    required this.lowRisks,
    required this.totalAssumptions,
    required this.highestRiskScore,
  });

  factory RiskMatrixModel.fromJson(Map<String, dynamic> json) {
    return RiskMatrixModel(
      projectId: json['project_id'] as int,
      criticalRisks: (json['critical_risks'] as List<dynamic>?)
              ?.map((e) => RiskQuadrantItemModel.fromJson(e))
              .toList() ??
          [],
      monitorRisks: (json['monitor_risks'] as List<dynamic>?)
              ?.map((e) => RiskQuadrantItemModel.fromJson(e))
              .toList() ??
          [],
      exploratoryRisks: (json['exploratory_risks'] as List<dynamic>?)
              ?.map((e) => RiskQuadrantItemModel.fromJson(e))
              .toList() ??
          [],
      lowRisks: (json['low_risks'] as List<dynamic>?)
              ?.map((e) => RiskQuadrantItemModel.fromJson(e))
              .toList() ??
          [],
      totalAssumptions: json['total_assumptions'] as int? ?? 0,
      highestRiskScore: json['highest_risk_score'] as int? ?? 0,
    );
  }
}

class ValidationReviewModel {
  final int id;
  final int workspaceId;
  final int projectId;
  final int? hypothesisId;
  final String reviewProviderType;
  final String verdict;
  final double confidenceScore;
  final List<String> supportedPoints;
  final List<String> challengedPoints;
  final List<String> missingEvidence;
  final List<String> criticalRisks;
  final String? recommendedNextAction;
  final bool humanReviewRecommended;
  final String? rawReport;
  final DateTime createdAt;

  ValidationReviewModel({
    required this.id,
    required this.workspaceId,
    required this.projectId,
    this.hypothesisId,
    required this.reviewProviderType,
    required this.verdict,
    required this.confidenceScore,
    required this.supportedPoints,
    required this.challengedPoints,
    required this.missingEvidence,
    required this.criticalRisks,
    this.recommendedNextAction,
    required this.humanReviewRecommended,
    this.rawReport,
    required this.createdAt,
  });

  factory ValidationReviewModel.fromJson(Map<String, dynamic> json) {
    return ValidationReviewModel(
      id: json['id'] as int,
      workspaceId: json['workspace_id'] as int,
      projectId: json['project_id'] as int,
      hypothesisId: json['hypothesis_id'] as int?,
      reviewProviderType: json['review_provider_type'] ?? 'AI',
      verdict: json['verdict'] ?? 'TEST_MORE',
      confidenceScore: (json['confidence_score'] as num?)?.toDouble() ?? 0.7,
      supportedPoints: (json['supported_points'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      challengedPoints: (json['challenged_points'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      missingEvidence: (json['missing_evidence'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      criticalRisks: (json['critical_risks'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      recommendedNextAction: json['recommended_next_action'] as String?,
      humanReviewRecommended: json['human_review_recommended'] ?? false,
      rawReport: json['raw_report'] as String?,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class NextBestActionDetailModel {
  final int projectId;
  final String title;
  final String why;
  final String riskCategory;
  final int riskScore;
  final String? recommendedExperiment;
  final String? targetThreshold;
  final int timeframeDays;
  final String priority;

  NextBestActionDetailModel({
    required this.projectId,
    required this.title,
    required this.why,
    required this.riskCategory,
    required this.riskScore,
    this.recommendedExperiment,
    this.targetThreshold,
    required this.timeframeDays,
    required this.priority,
  });

  factory NextBestActionDetailModel.fromJson(Map<String, dynamic> json) {
    return NextBestActionDetailModel(
      projectId: json['project_id'] as int,
      title: json['title'] ?? '',
      why: json['why'] ?? '',
      riskCategory: json['risk_category'] ?? 'CUSTOMER',
      riskScore: json['risk_score'] as int? ?? 0,
      recommendedExperiment: json['recommended_experiment'] as String?,
      targetThreshold: json['target_threshold'] as String?,
      timeframeDays: json['timeframe_days'] as int? ?? 7,
      priority: json['priority'] ?? 'P0_CRITICAL',
    );
  }
}

// -------------------------------------------------------------------------
// F2 & F3: PROBLEM-FIRST & CUSTOMER DISCOVERY MODELS
// -------------------------------------------------------------------------

class ProblemScorecardModel {
  final int? id;
  final int projectId;
  final int frequencyScore;
  final int severityScore;
  final int alternativesScore;
  final int wtpScore;
  final int marketPotentialScore;
  final int totalScore;
  final int frameworkThreshold;
  final String interpretationResult;
  final String evidenceQuality;
  final String? notes;

  ProblemScorecardModel({
    this.id,
    required this.projectId,
    required this.frequencyScore,
    required this.severityScore,
    required this.alternativesScore,
    required this.wtpScore,
    required this.marketPotentialScore,
    required this.totalScore,
    this.frameworkThreshold = 40,
    required this.interpretationResult,
    required this.evidenceQuality,
    this.notes,
  });

  factory ProblemScorecardModel.fromJson(Map<String, dynamic> json) {
    return ProblemScorecardModel(
      id: json['id'] as int?,
      projectId: json['project_id'] as int,
      frequencyScore: json['frequency_score'] as int? ?? 5,
      severityScore: json['severity_score'] as int? ?? 5,
      alternativesScore: json['alternatives_score'] as int? ?? 5,
      wtpScore: json['wtp_score'] as int? ?? 5,
      marketPotentialScore: json['market_potential_score'] as int? ?? 5,
      totalScore: json['total_score'] as int? ?? 25,
      frameworkThreshold: json['framework_threshold'] as int? ?? 40,
      interpretationResult: json['interpretation_result'] ?? 'BELOW_RECOMMENDED_THRESHOLD',
      evidenceQuality: json['evidence_quality'] ?? 'UNVERIFIED',
      notes: json['notes'] as String?,
    );
  }
}

class RoleCoverageModel {
  final int projectId;
  final int userCount;
  final int buyerCount;
  final int decisionMakerCount;
  final int influencerCount;
  final int totalInterviews;
  final bool hasDecisionMakerGap;
  final String? warningMessage;
  final Map<String, bool> coverageStatus;

  RoleCoverageModel({
    required this.projectId,
    required this.userCount,
    required this.buyerCount,
    required this.decisionMakerCount,
    required this.influencerCount,
    required this.totalInterviews,
    required this.hasDecisionMakerGap,
    this.warningMessage,
    required this.coverageStatus,
  });

  factory RoleCoverageModel.fromJson(Map<String, dynamic> json) {
    return RoleCoverageModel(
      projectId: json['project_id'] as int,
      userCount: json['user_count'] as int? ?? 0,
      buyerCount: json['buyer_count'] as int? ?? 0,
      decisionMakerCount: json['decision_maker_count'] as int? ?? 0,
      influencerCount: json['influencer_count'] as int? ?? 0,
      totalInterviews: json['total_interviews'] as int? ?? 0,
      hasDecisionMakerGap: json['has_decision_maker_gap'] ?? false,
      warningMessage: json['warning_message'] as String?,
      coverageStatus: (json['coverage_status'] as Map<String, dynamic>?)?.map(
            (k, v) => MapEntry(k, v == true),
          ) ??
          {},
    );
  }
}

class SolutionBiasRiskModel {
  final int projectId;
  final String solutionBiasRisk;
  final String solutionMaturity;
  final String problemEvidenceMaturity;
  final String? warningTitle;
  final String? warningMessage;
  final String recommendedAction;
  final List<String> counterQuestions;
  final bool allowProceedAnyway;

  SolutionBiasRiskModel({
    required this.projectId,
    required this.solutionBiasRisk,
    required this.solutionMaturity,
    required this.problemEvidenceMaturity,
    this.warningTitle,
    this.warningMessage,
    required this.recommendedAction,
    required this.counterQuestions,
    required this.allowProceedAnyway,
  });

  factory SolutionBiasRiskModel.fromJson(Map<String, dynamic> json) {
    return SolutionBiasRiskModel(
      projectId: json['project_id'] as int,
      solutionBiasRisk: json['solution_bias_risk'] ?? 'NONE',
      solutionMaturity: json['solution_maturity'] ?? 'UNKNOWN',
      problemEvidenceMaturity: json['problem_evidence_maturity'] ?? 'UNKNOWN',
      warningTitle: json['warning_title'] as String?,
      warningMessage: json['warning_message'] as String?,
      recommendedAction: json['recommended_action'] ?? '',
      counterQuestions: (json['counter_questions'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      allowProceedAnyway: json['allow_proceed_anyway'] ?? true,
    );
  }
}

class CustomerContactModel {
  final int id;
  final int projectId;
  final String name;
  final String role;
  final String? segment;
  final String? company;
  final String? contactInfo;
  final String? notes;
  final DateTime createdAt;

  CustomerContactModel({
    required this.id,
    required this.projectId,
    required this.name,
    required this.role,
    this.segment,
    this.company,
    this.contactInfo,
    this.notes,
    required this.createdAt,
  });

  factory CustomerContactModel.fromJson(Map<String, dynamic> json) {
    return CustomerContactModel(
      id: json['id'] as int,
      projectId: json['project_id'] as int,
      name: json['name'] ?? '',
      role: json['role'] ?? 'USER',
      segment: json['segment'] as String?,
      company: json['company'] as String?,
      contactInfo: json['contact_info'] as String?,
      notes: json['notes'] as String?,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class CustomerInterviewSessionModel {
  final int id;
  final int projectId;
  final int? contactId;
  final String role;
  final String? segment;
  final DateTime interviewDate;
  final int durationMinutes;
  final String? rawNotes;
  final String? transcript;
  final String? sessionSummary;
  final String? referralNotes;
  final int quotesCount;
  final DateTime createdAt;

  CustomerInterviewSessionModel({
    required this.id,
    required this.projectId,
    this.contactId,
    required this.role,
    this.segment,
    required this.interviewDate,
    required this.durationMinutes,
    this.rawNotes,
    this.transcript,
    this.sessionSummary,
    this.referralNotes,
    required this.quotesCount,
    required this.createdAt,
  });

  factory CustomerInterviewSessionModel.fromJson(Map<String, dynamic> json) {
    return CustomerInterviewSessionModel(
      id: json['id'] as int,
      projectId: json['project_id'] as int,
      contactId: json['contact_id'] as int?,
      role: json['role'] ?? 'USER',
      segment: json['segment'] as String?,
      interviewDate: DateTime.parse(json['interview_date']),
      durationMinutes: json['duration_minutes'] as int? ?? 30,
      rawNotes: json['raw_notes'] as String?,
      transcript: json['transcript'] as String?,
      sessionSummary: json['session_summary'] as String?,
      referralNotes: json['referral_notes'] as String?,
      quotesCount: json['quotes_count'] as int? ?? 0,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class VerbatimQuoteModel {
  final int id;
  final int projectId;
  final int sessionId;
  final String rawQuote;
  final String? interpretation;
  final String interpretationActor;
  final List<String> tags;
  final String? buyingSignalLevel;
  final int? linkedAssumptionId;
  final DateTime createdAt;

  VerbatimQuoteModel({
    required this.id,
    required this.projectId,
    required this.sessionId,
    required this.rawQuote,
    this.interpretation,
    required this.interpretationActor,
    required this.tags,
    this.buyingSignalLevel,
    this.linkedAssumptionId,
    required this.createdAt,
  });

  factory VerbatimQuoteModel.fromJson(Map<String, dynamic> json) {
    return VerbatimQuoteModel(
      id: json['id'] as int,
      projectId: json['project_id'] as int,
      sessionId: json['session_id'] as int,
      rawQuote: json['raw_quote'] ?? '',
      interpretation: json['interpretation'] as String?,
      interpretationActor: json['interpretation_actor'] ?? 'AI',
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      buyingSignalLevel: json['buying_signal_level'] as String?,
      linkedAssumptionId: json['linked_assumption_id'] as int?,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}



