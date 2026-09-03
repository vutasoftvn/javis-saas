import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/validation_models.dart';

/// Test serialization cho toàn bộ model trong `lib/data/models/validation_models.dart`.
///
/// Mỗi model có 2 nhánh cần phủ:
/// - "full": mọi field xuất hiện trong JSON → nhánh đọc giá trị thật.
/// - "minimal": chỉ field bắt buộc (id/workspace_id/...) → nhánh `?? default`.
void main() {
  const ts = '2026-09-01T10:00:00Z';
  const ts2 = '2026-09-02T11:30:00Z';

  group('ValidationSessionModel', () {
    test('fromJson đọc đủ field khi JSON đầy đủ', () {
      final m = ValidationSessionModel.fromJson({
        'id': 1,
        'workspace_id': 10,
        'project_id': 100,
        'current_topic': 'PROBLEM',
        'workflow_state': 'REVIEW',
        'interview_mode_active': true,
        'fields_status_jsonb': {'customer': 'DONE'},
        'created_at': ts,
        'updated_at': ts2,
      });
      expect(m.id, 1);
      expect(m.workspaceId, 10);
      expect(m.projectId, 100);
      expect(m.currentTopic, 'PROBLEM');
      expect(m.workflowState, 'REVIEW');
      expect(m.interviewModeActive, isTrue);
      expect(m.fieldsStatus, {'customer': 'DONE'});
      expect(m.createdAt, DateTime.parse(ts));
      expect(m.updatedAt, DateTime.parse(ts2));
    });

    test('fromJson dùng default khi thiếu field tùy chọn', () {
      final m = ValidationSessionModel.fromJson({
        'id': 2,
        'workspace_id': 11,
        'project_id': 101,
        'fields_status_jsonb': 'not-a-map',
        'created_at': ts,
        'updated_at': ts,
      });
      expect(m.currentTopic, 'CUSTOMER');
      expect(m.workflowState, 'DATA_COLLECTION');
      expect(m.interviewModeActive, isFalse);
      expect(m.fieldsStatus, isEmpty);
    });
  });

  group('StructuredClaimModel', () {
    test('fromJson full', () {
      final m = StructuredClaimModel.fromJson({
        'id': 1,
        'workspace_id': 10,
        'project_id': 100,
        'session_id': 5,
        'dimension': 'CUSTOMER',
        'subject': 'SMB owners',
        'predicate': 'struggle with payroll',
        'value_jsonb': {'x': 1},
        'epistemic_type': 'VALIDATED',
        'confirmation_status': 'FOUNDER_CONFIRMED',
        'source_type': 'INTERVIEW',
        'source_actor': 'CUSTOMER',
        'source_ref': 'sess-5',
        'confidence': 0.9,
        'supersedes_id': 3,
        'created_at': ts,
        'updated_at': ts2,
      });
      expect(m.sessionId, 5);
      expect(m.subject, 'SMB owners');
      expect(m.value, {'x': 1});
      expect(m.epistemicType, 'VALIDATED');
      expect(m.sourceRef, 'sess-5');
      expect(m.confidence, 0.9);
      expect(m.supersedesId, 3);
    });

    test('fromJson minimal → default + value fallback', () {
      final m = StructuredClaimModel.fromJson({
        'id': 2,
        'workspace_id': 11,
        'project_id': 101,
        'created_at': ts,
        'updated_at': ts,
      });
      expect(m.sessionId, isNull);
      expect(m.dimension, '');
      expect(m.value, {});
      expect(m.epistemicType, 'ASSUMPTION');
      expect(m.confirmationStatus, 'AI_INFERRED');
      expect(m.sourceType, 'FOUNDER_CHAT');
      expect(m.sourceActor, 'FOUNDER');
      expect(m.confidence, 1.0);
      expect(m.supersedesId, isNull);
    });

    test('fromJson đọc `value` khi không có `value_jsonb`', () {
      final m = StructuredClaimModel.fromJson({
        'id': 3,
        'workspace_id': 11,
        'project_id': 101,
        'value': [1, 2, 3],
        'created_at': ts,
        'updated_at': ts,
      });
      expect(m.value, [1, 2, 3]);
    });
  });

  group('ClusterSummaryModel', () {
    test('fromJson full', () {
      final m = ClusterSummaryModel.fromJson({
        'title': 'CUSTOMER SNAPSHOT',
        'summary_items': ['a', 'b', 2],
        'status': 'VALIDATED',
      });
      expect(m.title, 'CUSTOMER SNAPSHOT');
      expect(m.summaryItems, ['a', 'b', '2']);
      expect(m.status, 'VALIDATED');
    });

    test('fromJson minimal → default', () {
      final m = ClusterSummaryModel.fromJson({});
      expect(m.title, 'SNAPSHOT');
      expect(m.summaryItems, isEmpty);
      expect(m.status, 'ASSUMPTION');
    });
  });

  group('ValidationChatResponseModel', () {
    test('fromJson full (kèm cluster_summary lồng)', () {
      final m = ValidationChatResponseModel.fromJson({
        'session_id': 7,
        'current_topic': 'SOLUTION',
        'ai_reply': 'Understood.',
        'extracted_claims': [
          {'subject': 's', 'predicate': 'p'},
        ],
        'is_topic_cluster_complete': true,
        'cluster_summary': {
          'title': 'T',
          'summary_items': ['x'],
          'status': 'ASSUMPTION',
        },
        'next_questions': ['q1', 'q2'],
        'suggested_next_topic': 'MARKET',
      });
      expect(m.sessionId, 7);
      expect(m.currentTopic, 'SOLUTION');
      expect(m.aiReply, 'Understood.');
      expect(m.extractedClaims.single['subject'], 's');
      expect(m.isTopicClusterComplete, isTrue);
      expect(m.clusterSummary, isNotNull);
      expect(m.clusterSummary!.title, 'T');
      expect(m.nextQuestions, ['q1', 'q2']);
      expect(m.suggestedNextTopic, 'MARKET');
    });

    test('fromJson minimal → default, cluster_summary null', () {
      final m = ValidationChatResponseModel.fromJson({'session_id': 8});
      expect(m.currentTopic, 'CUSTOMER');
      expect(m.aiReply, '');
      expect(m.extractedClaims, isEmpty);
      expect(m.isTopicClusterComplete, isFalse);
      expect(m.clusterSummary, isNull);
      expect(m.nextQuestions, isEmpty);
      expect(m.suggestedNextTopic, isNull);
    });
  });

  group('DimensionStateModel', () {
    test('fromJson full', () {
      final m = DimensionStateModel.fromJson({
        'dimension': 'DESIRABILITY_CUSTOMER',
        'pillar': 'VIABILITY',
        'state': 'STRONG',
        'confidence': 0.8,
        'summary': 'ok',
        'updated_at': ts,
      });
      expect(m.dimension, 'DESIRABILITY_CUSTOMER');
      expect(m.pillar, 'VIABILITY');
      expect(m.state, 'STRONG');
      expect(m.confidence, 0.8);
      expect(m.summary, 'ok');
      expect(m.updatedAt, DateTime.parse(ts));
    });

    test('fromJson minimal → default', () {
      final m = DimensionStateModel.fromJson({'updated_at': ts});
      expect(m.dimension, '');
      expect(m.pillar, 'DESIRABILITY');
      expect(m.state, 'UNKNOWN');
      expect(m.confidence, 0.0);
      expect(m.summary, isNull);
    });
  });

  group('StateVectorModel', () {
    test('fromJson full (kèm dimensions lồng)', () {
      final m = StateVectorModel.fromJson({
        'project_id': 100,
        'project_stage': 'VALIDATION',
        'workflow_state': 'REVIEW',
        'overall_confidence': 0.65,
        'dimensions': {
          'CUSTOMER': {
            'dimension': 'CUSTOMER',
            'pillar': 'DESIRABILITY',
            'state': 'STRONG',
            'confidence': 0.9,
            'updated_at': ts,
          },
          'bad': 'ignored',
        },
        'critical_assumptions_count': 4,
        'active_experiments_count': 2,
        'primary_next_best_action': 'Run interview',
      });
      expect(m.projectId, 100);
      expect(m.projectStage, 'VALIDATION');
      expect(m.overallConfidence, 0.65);
      expect(m.dimensions.keys, ['CUSTOMER']);
      expect(m.dimensions['CUSTOMER']!.state, 'STRONG');
      expect(m.criticalAssumptionsCount, 4);
      expect(m.activeExperimentsCount, 2);
      expect(m.primaryNextBestAction, 'Run interview');
    });

    test('fromJson minimal → default, dimensions rỗng', () {
      final m = StateVectorModel.fromJson({'project_id': 101});
      expect(m.projectStage, 'IDEA');
      expect(m.workflowState, 'DATA_COLLECTION');
      expect(m.overallConfidence, 0.0);
      expect(m.dimensions, isEmpty);
      expect(m.criticalAssumptionsCount, 0);
      expect(m.activeExperimentsCount, 0);
      expect(m.primaryNextBestAction, isNull);
    });
  });

  group('ValidationAssumptionModel', () {
    test('fromJson full', () {
      final m = ValidationAssumptionModel.fromJson({
        'id': 1,
        'workspace_id': 10,
        'project_id': 100,
        'claim_id': 9,
        'category': 'MARKET',
        'statement': 'TAM is large',
        'importance': 5,
        'uncertainty': 4,
        'impact': 5,
        'risk_score': 20,
        'source': 'DESK_RESEARCH',
        'status': 'TESTING',
        'confidence': 0.4,
        'owner': 'founder',
        'created_at': ts,
      });
      expect(m.claimId, 9);
      expect(m.category, 'MARKET');
      expect(m.importance, 5);
      expect(m.riskScore, 20);
      expect(m.status, 'TESTING');
      expect(m.owner, 'founder');
    });

    test('fromJson minimal → default', () {
      final m = ValidationAssumptionModel.fromJson({
        'id': 2,
        'workspace_id': 11,
        'project_id': 101,
        'created_at': ts,
      });
      expect(m.claimId, isNull);
      expect(m.category, 'CUSTOMER');
      expect(m.statement, '');
      expect(m.importance, 3);
      expect(m.uncertainty, 3);
      expect(m.impact, 3);
      expect(m.riskScore, 9);
      expect(m.source, 'FOUNDER_CHAT');
      expect(m.status, 'UNTESTED');
      expect(m.confidence, 0.5);
      expect(m.owner, isNull);
    });
  });

  group('ValidationHypothesisModel', () {
    test('fromJson full', () {
      final m = ValidationHypothesisModel.fromJson({
        'id': 1,
        'workspace_id': 10,
        'project_id': 100,
        'assumption_id': 50,
        'action': 'Landing page test',
        'target_segment': 'SMB',
        'metric': 'signup rate',
        'threshold': '5%',
        'timeframe_days': 14,
        'statement': 'If X then Y',
        'quality_gate_passed': true,
        'status': 'RUNNING',
        'created_at': ts,
      });
      expect(m.assumptionId, 50);
      expect(m.action, 'Landing page test');
      expect(m.timeframeDays, 14);
      expect(m.qualityGatePassed, isTrue);
      expect(m.status, 'RUNNING');
    });

    test('fromJson minimal → default', () {
      final m = ValidationHypothesisModel.fromJson({
        'id': 2,
        'workspace_id': 11,
        'project_id': 101,
        'assumption_id': 51,
        'created_at': ts,
      });
      expect(m.action, '');
      expect(m.targetSegment, '');
      expect(m.metric, '');
      expect(m.threshold, '');
      expect(m.timeframeDays, 7);
      expect(m.statement, '');
      expect(m.qualityGatePassed, isFalse);
      expect(m.status, 'DRAFT');
    });
  });

  group('ValidationExperimentModel', () {
    test('fromJson full', () {
      final m = ValidationExperimentModel.fromJson({
        'id': 1,
        'workspace_id': 10,
        'project_id': 100,
        'hypothesis_id': 70,
        'experiment_type': 'FAKE_DOOR',
        'name': 'Pricing page',
        'description': 'desc',
        'smallest_useful_scope': 'one segment',
        'success_threshold': '10 signups',
        'budget_amount': 250.5,
        'duration_days': 21,
        'status': 'DONE',
        'results_summary': 'passed',
        'created_at': ts,
      });
      expect(m.hypothesisId, 70);
      expect(m.experimentType, 'FAKE_DOOR');
      expect(m.description, 'desc');
      expect(m.smallestUsefulScope, 'one segment');
      expect(m.budgetAmount, 250.5);
      expect(m.durationDays, 21);
      expect(m.resultsSummary, 'passed');
    });

    test('fromJson minimal → default', () {
      final m = ValidationExperimentModel.fromJson({
        'id': 2,
        'workspace_id': 11,
        'project_id': 101,
        'hypothesis_id': 71,
        'created_at': ts,
      });
      expect(m.experimentType, 'CUSTOMER_INTERVIEW');
      expect(m.name, '');
      expect(m.description, isNull);
      expect(m.smallestUsefulScope, isNull);
      expect(m.successThreshold, '');
      expect(m.budgetAmount, 0.0);
      expect(m.durationDays, 7);
      expect(m.status, 'DRAFT');
      expect(m.resultsSummary, isNull);
    });
  });

  group('ValidationEvidenceModel', () {
    test('fromJson full', () {
      final m = ValidationEvidenceModel.fromJson({
        'id': 1,
        'workspace_id': 10,
        'project_id': 100,
        'assumption_id': 5,
        'hypothesis_id': 6,
        'experiment_id': 7,
        'evidence_type': 'INTERVIEW_QUOTE',
        'source_type': 'INTERVIEW',
        'source_ref': 'q-1',
        'observation': 'Customer said yes',
        'metric_name': 'signups',
        'metric_value': '12',
        'relationship': 'REFUTES',
        'confidence': 0.95,
        'captured_at': ts,
      });
      expect(m.assumptionId, 5);
      expect(m.hypothesisId, 6);
      expect(m.experimentId, 7);
      expect(m.evidenceType, 'INTERVIEW_QUOTE');
      expect(m.sourceRef, 'q-1');
      expect(m.metricName, 'signups');
      expect(m.metricValue, '12');
      expect(m.relationship, 'REFUTES');
      expect(m.confidence, 0.95);
      expect(m.capturedAt, DateTime.parse(ts));
    });

    test('fromJson minimal → default', () {
      final m = ValidationEvidenceModel.fromJson({
        'id': 2,
        'workspace_id': 11,
        'project_id': 101,
        'captured_at': ts,
      });
      expect(m.assumptionId, isNull);
      expect(m.hypothesisId, isNull);
      expect(m.experimentId, isNull);
      expect(m.evidenceType, 'FOUNDER_BELIEF');
      expect(m.sourceType, '');
      expect(m.observation, '');
      expect(m.relationship, 'SUPPORTS');
      expect(m.confidence, 0.5);
    });
  });

  group('RiskQuadrantItemModel', () {
    test('fromJson full', () {
      final m = RiskQuadrantItemModel.fromJson({
        'id': 1,
        'category': 'FEASIBILITY',
        'statement': 'Tech risk',
        'importance': 4,
        'uncertainty': 5,
        'risk_score': 20,
        'status': 'TESTING',
        'confidence': 0.3,
      });
      expect(m.category, 'FEASIBILITY');
      expect(m.riskScore, 20);
      expect(m.status, 'TESTING');
    });

    test('fromJson minimal → default', () {
      final m = RiskQuadrantItemModel.fromJson({'id': 2});
      expect(m.category, 'CUSTOMER');
      expect(m.statement, '');
      expect(m.importance, 3);
      expect(m.uncertainty, 3);
      expect(m.riskScore, 9);
      expect(m.status, 'UNTESTED');
      expect(m.confidence, 0.5);
    });
  });

  group('RiskMatrixModel', () {
    test('fromJson full (4 quadrant có phần tử)', () {
      Map<String, dynamic> item(int id) => {
            'id': id,
            'category': 'CUSTOMER',
            'statement': 's$id',
            'importance': 3,
            'uncertainty': 3,
            'risk_score': 9,
            'status': 'UNTESTED',
            'confidence': 0.5,
          };
      final m = RiskMatrixModel.fromJson({
        'project_id': 100,
        'critical_risks': [item(1)],
        'monitor_risks': [item(2)],
        'exploratory_risks': [item(3)],
        'low_risks': [item(4)],
        'total_assumptions': 4,
        'highest_risk_score': 25,
      });
      expect(m.criticalRisks.single.id, 1);
      expect(m.monitorRisks.single.id, 2);
      expect(m.exploratoryRisks.single.id, 3);
      expect(m.lowRisks.single.id, 4);
      expect(m.totalAssumptions, 4);
      expect(m.highestRiskScore, 25);
    });

    test('fromJson minimal → list rỗng', () {
      final m = RiskMatrixModel.fromJson({'project_id': 101});
      expect(m.criticalRisks, isEmpty);
      expect(m.monitorRisks, isEmpty);
      expect(m.exploratoryRisks, isEmpty);
      expect(m.lowRisks, isEmpty);
      expect(m.totalAssumptions, 0);
      expect(m.highestRiskScore, 0);
    });
  });

  group('ValidationReviewModel', () {
    test('fromJson full', () {
      final m = ValidationReviewModel.fromJson({
        'id': 1,
        'workspace_id': 10,
        'project_id': 100,
        'hypothesis_id': 9,
        'review_provider_type': 'HUMAN',
        'verdict': 'PROCEED',
        'confidence_score': 0.85,
        'supported_points': ['a'],
        'challenged_points': ['b'],
        'missing_evidence': ['c'],
        'critical_risks': ['d'],
        'recommended_next_action': 'ship',
        'human_review_recommended': true,
        'raw_report': '{...}',
        'created_at': ts,
      });
      expect(m.hypothesisId, 9);
      expect(m.reviewProviderType, 'HUMAN');
      expect(m.verdict, 'PROCEED');
      expect(m.confidenceScore, 0.85);
      expect(m.supportedPoints, ['a']);
      expect(m.challengedPoints, ['b']);
      expect(m.missingEvidence, ['c']);
      expect(m.criticalRisks, ['d']);
      expect(m.recommendedNextAction, 'ship');
      expect(m.humanReviewRecommended, isTrue);
      expect(m.rawReport, '{...}');
    });

    test('fromJson minimal → default', () {
      final m = ValidationReviewModel.fromJson({
        'id': 2,
        'workspace_id': 11,
        'project_id': 101,
        'created_at': ts,
      });
      expect(m.hypothesisId, isNull);
      expect(m.reviewProviderType, 'AI');
      expect(m.verdict, 'TEST_MORE');
      expect(m.confidenceScore, 0.7);
      expect(m.supportedPoints, isEmpty);
      expect(m.challengedPoints, isEmpty);
      expect(m.missingEvidence, isEmpty);
      expect(m.criticalRisks, isEmpty);
      expect(m.recommendedNextAction, isNull);
      expect(m.humanReviewRecommended, isFalse);
      expect(m.rawReport, isNull);
    });
  });

  group('NextBestActionDetailModel', () {
    test('fromJson full', () {
      final m = NextBestActionDetailModel.fromJson({
        'project_id': 100,
        'title': 'Interview 5 buyers',
        'why': 'decision-maker gap',
        'risk_category': 'VIABILITY',
        'risk_score': 18,
        'recommended_experiment': 'CUSTOMER_INTERVIEW',
        'target_threshold': '5 interviews',
        'timeframe_days': 10,
        'priority': 'P1_HIGH',
      });
      expect(m.title, 'Interview 5 buyers');
      expect(m.riskCategory, 'VIABILITY');
      expect(m.riskScore, 18);
      expect(m.recommendedExperiment, 'CUSTOMER_INTERVIEW');
      expect(m.targetThreshold, '5 interviews');
      expect(m.timeframeDays, 10);
      expect(m.priority, 'P1_HIGH');
    });

    test('fromJson minimal → default', () {
      final m = NextBestActionDetailModel.fromJson({'project_id': 101});
      expect(m.title, '');
      expect(m.why, '');
      expect(m.riskCategory, 'CUSTOMER');
      expect(m.riskScore, 0);
      expect(m.recommendedExperiment, isNull);
      expect(m.targetThreshold, isNull);
      expect(m.timeframeDays, 7);
      expect(m.priority, 'P0_CRITICAL');
    });
  });

  group('ProblemScorecardModel', () {
    test('fromJson full', () {
      final m = ProblemScorecardModel.fromJson({
        'id': 5,
        'project_id': 100,
        'frequency_score': 8,
        'severity_score': 9,
        'alternatives_score': 7,
        'wtp_score': 6,
        'market_potential_score': 8,
        'total_score': 38,
        'framework_threshold': 40,
        'interpretation_result': 'BELOW_RECOMMENDED_THRESHOLD',
        'evidence_quality': 'STRONG',
        'notes': 'n',
      });
      expect(m.id, 5);
      expect(m.frequencyScore, 8);
      expect(m.totalScore, 38);
      expect(m.frameworkThreshold, 40);
      expect(m.evidenceQuality, 'STRONG');
      expect(m.notes, 'n');
    });

    test('fromJson minimal → default', () {
      final m = ProblemScorecardModel.fromJson({'project_id': 101});
      expect(m.id, isNull);
      expect(m.frequencyScore, 5);
      expect(m.severityScore, 5);
      expect(m.alternativesScore, 5);
      expect(m.wtpScore, 5);
      expect(m.marketPotentialScore, 5);
      expect(m.totalScore, 25);
      expect(m.frameworkThreshold, 40);
      expect(m.interpretationResult, 'BELOW_RECOMMENDED_THRESHOLD');
      expect(m.evidenceQuality, 'UNVERIFIED');
      expect(m.notes, isNull);
    });
  });

  group('RoleCoverageModel', () {
    test('fromJson full', () {
      final m = RoleCoverageModel.fromJson({
        'project_id': 100,
        'user_count': 5,
        'buyer_count': 3,
        'decision_maker_count': 1,
        'influencer_count': 2,
        'total_interviews': 11,
        'has_decision_maker_gap': true,
        'warning_message': 'Need more DMs',
        'coverage_status': {'USER': true, 'BUYER': false},
      });
      expect(m.userCount, 5);
      expect(m.decisionMakerCount, 1);
      expect(m.totalInterviews, 11);
      expect(m.hasDecisionMakerGap, isTrue);
      expect(m.warningMessage, 'Need more DMs');
      expect(m.coverageStatus, {'USER': true, 'BUYER': false});
    });

    test('fromJson minimal → default', () {
      final m = RoleCoverageModel.fromJson({'project_id': 101});
      expect(m.userCount, 0);
      expect(m.buyerCount, 0);
      expect(m.decisionMakerCount, 0);
      expect(m.influencerCount, 0);
      expect(m.totalInterviews, 0);
      expect(m.hasDecisionMakerGap, isFalse);
      expect(m.warningMessage, isNull);
      expect(m.coverageStatus, isEmpty);
    });
  });

  group('SolutionBiasRiskModel', () {
    test('fromJson full', () {
      final m = SolutionBiasRiskModel.fromJson({
        'project_id': 100,
        'solution_bias_risk': 'HIGH',
        'solution_maturity': 'PROTOTYPE',
        'problem_evidence_maturity': 'WEAK',
        'warning_title': 'Solution-first',
        'warning_message': 'You jumped ahead',
        'recommended_action': 'Go back to problem',
        'counter_questions': ['why now?', 'who hurts?'],
        'allow_proceed_anyway': false,
      });
      expect(m.solutionBiasRisk, 'HIGH');
      expect(m.solutionMaturity, 'PROTOTYPE');
      expect(m.problemEvidenceMaturity, 'WEAK');
      expect(m.warningTitle, 'Solution-first');
      expect(m.recommendedAction, 'Go back to problem');
      expect(m.counterQuestions, ['why now?', 'who hurts?']);
      expect(m.allowProceedAnyway, isFalse);
    });

    test('fromJson minimal → default', () {
      final m = SolutionBiasRiskModel.fromJson({'project_id': 101});
      expect(m.solutionBiasRisk, 'NONE');
      expect(m.solutionMaturity, 'UNKNOWN');
      expect(m.problemEvidenceMaturity, 'UNKNOWN');
      expect(m.warningTitle, isNull);
      expect(m.warningMessage, isNull);
      expect(m.recommendedAction, '');
      expect(m.counterQuestions, isEmpty);
      expect(m.allowProceedAnyway, isTrue);
    });
  });

  group('CustomerContactModel', () {
    test('fromJson full', () {
      final m = CustomerContactModel.fromJson({
        'id': 1,
        'project_id': 100,
        'name': 'Jane',
        'role': 'BUYER',
        'segment': 'SMB',
        'company': 'Acme',
        'contact_info': 'jane@acme.test',
        'notes': 'warm',
        'created_at': ts,
      });
      expect(m.name, 'Jane');
      expect(m.role, 'BUYER');
      expect(m.segment, 'SMB');
      expect(m.company, 'Acme');
      expect(m.contactInfo, 'jane@acme.test');
      expect(m.notes, 'warm');
    });

    test('fromJson minimal → default', () {
      final m = CustomerContactModel.fromJson({
        'id': 2,
        'project_id': 101,
        'created_at': ts,
      });
      expect(m.name, '');
      expect(m.role, 'USER');
      expect(m.segment, isNull);
      expect(m.company, isNull);
      expect(m.contactInfo, isNull);
      expect(m.notes, isNull);
    });
  });

  group('CustomerInterviewSessionModel', () {
    test('fromJson full', () {
      final m = CustomerInterviewSessionModel.fromJson({
        'id': 1,
        'project_id': 100,
        'contact_id': 9,
        'role': 'DECISION_MAKER',
        'segment': 'Enterprise',
        'interview_date': ts,
        'duration_minutes': 45,
        'raw_notes': 'notes',
        'transcript': 'full transcript',
        'session_summary': 'summary',
        'referral_notes': 'ask for intro',
        'quotes_count': 6,
        'created_at': ts2,
      });
      expect(m.contactId, 9);
      expect(m.role, 'DECISION_MAKER');
      expect(m.segment, 'Enterprise');
      expect(m.interviewDate, DateTime.parse(ts));
      expect(m.durationMinutes, 45);
      expect(m.transcript, 'full transcript');
      expect(m.referralNotes, 'ask for intro');
      expect(m.quotesCount, 6);
    });

    test('fromJson minimal → default', () {
      final m = CustomerInterviewSessionModel.fromJson({
        'id': 2,
        'project_id': 101,
        'interview_date': ts,
        'created_at': ts,
      });
      expect(m.contactId, isNull);
      expect(m.role, 'USER');
      expect(m.segment, isNull);
      expect(m.durationMinutes, 30);
      expect(m.rawNotes, isNull);
      expect(m.transcript, isNull);
      expect(m.sessionSummary, isNull);
      expect(m.referralNotes, isNull);
      expect(m.quotesCount, 0);
    });
  });

  group('VerbatimQuoteModel', () {
    test('fromJson full', () {
      final m = VerbatimQuoteModel.fromJson({
        'id': 1,
        'project_id': 100,
        'session_id': 9,
        'raw_quote': 'I would pay for this',
        'interpretation': 'strong buying signal',
        'interpretation_actor': 'FOUNDER',
        'tags': ['pricing', 'pain'],
        'buying_signal_level': 'HIGH',
        'linked_assumption_id': 50,
        'created_at': ts,
      });
      expect(m.sessionId, 9);
      expect(m.rawQuote, 'I would pay for this');
      expect(m.interpretation, 'strong buying signal');
      expect(m.interpretationActor, 'FOUNDER');
      expect(m.tags, ['pricing', 'pain']);
      expect(m.buyingSignalLevel, 'HIGH');
      expect(m.linkedAssumptionId, 50);
    });

    test('fromJson minimal → default', () {
      final m = VerbatimQuoteModel.fromJson({
        'id': 2,
        'project_id': 101,
        'session_id': 10,
        'created_at': ts,
      });
      expect(m.rawQuote, '');
      expect(m.interpretation, isNull);
      expect(m.interpretationActor, 'AI');
      expect(m.tags, isEmpty);
      expect(m.buyingSignalLevel, isNull);
      expect(m.linkedAssumptionId, isNull);
    });
  });
}
