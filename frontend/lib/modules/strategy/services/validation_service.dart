import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../data/models/validation_models.dart';

class ValidationService {
  static Future<ValidationSessionModel?> startSession(int projectId, {String initialTopic = 'CUSTOMER'}) async {
    try {
      final res = await ApiClient.post(
        '/projects/$projectId/validation/session/start',
        body: {'initial_topic': initialTopic, 'interview_mode': true},
      );
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final data = jsonDecode(res.body);
        return ValidationSessionModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('ValidationService.startSession error: $e');
    }
    return null;
  }

  static Future<ValidationSessionModel?> getSession(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/session');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final data = jsonDecode(res.body);
        return ValidationSessionModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('ValidationService.getSession error: $e');
    }
    return null;
  }

  static Future<ValidationChatResponseModel?> sendValidationChat(
    int projectId,
    String message, {
    String? currentTopic,
  }) async {
    try {
      final res = await ApiClient.post(
        '/projects/$projectId/validation/chat',
        body: {
          'message': message,
          ...?currentTopic == null ? null : {'current_topic': currentTopic},
        },
      );
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final data = jsonDecode(res.body);
        return ValidationChatResponseModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('ValidationService.sendValidationChat error: $e');
    }
    return null;
  }

  static Future<List<StructuredClaimModel>> getClaims(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/claims');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final list = jsonDecode(res.body) as List<dynamic>;
        return list.map((e) => StructuredClaimModel.fromJson(e)).toList();
      }
    } catch (e) {
      debugPrint('ValidationService.getClaims error: $e');
    }
    return [];
  }

  static Future<StructuredClaimModel?> confirmClaim(int projectId, int claimId, {double confidence = 1.0}) async {
    try {
      final res = await ApiClient.post(
        '/projects/$projectId/validation/claims/$claimId/confirm',
        body: {'confidence': confidence},
      );
      if (res.statusCode >= 200 && res.statusCode < 300) {
        return StructuredClaimModel.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint('ValidationService.confirmClaim error: $e');
    }
    return null;
  }

  static Future<StructuredClaimModel?> editClaim(
    int projectId,
    int claimId,
    dynamic newValue, {
    String reason = 'Founder direct edit in chat',
  }) async {
    try {
      final res = await ApiClient.post(
        '/projects/$projectId/validation/claims/$claimId/edit',
        body: {
          'new_value': newValue is Map ? newValue : {'raw': newValue},
          'reason': reason,
        },
      );
      if (res.statusCode >= 200 && res.statusCode < 300) {
        return StructuredClaimModel.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint('ValidationService.editClaim error: $e');
    }
    return null;
  }

  static Future<StateVectorModel?> getStateVector(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/state-vector');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        return StateVectorModel.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint('ValidationService.getStateVector error: $e');
    }
    return null;
  }

  static Future<RiskMatrixModel?> getRiskMatrix(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/risk-matrix');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        return RiskMatrixModel.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint('ValidationService.getRiskMatrix error: $e');
    }
    return null;
  }

  static Future<List<ValidationAssumptionModel>> getRiskiestAssumptions(int projectId, {int limit = 5}) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/assumptions/riskiest?limit=$limit');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final list = jsonDecode(res.body) as List<dynamic>;
        return list.map((e) => ValidationAssumptionModel.fromJson(e)).toList();
      }
    } catch (e) {
      debugPrint('ValidationService.getRiskiestAssumptions error: $e');
    }
    return [];
  }

  static Future<ValidationHypothesisModel?> generateHypothesis(int projectId, int assumptionId) async {
    try {
      final res = await ApiClient.post(
        '/projects/$projectId/validation/assumptions/$assumptionId/generate-hypothesis',
      );
      if (res.statusCode >= 200 && res.statusCode < 300) {
        // Return latest hypotheses list or reconstructed hypothesis
        final list = await getHypotheses(projectId);
        return list.isNotEmpty ? list.first : null;
      }
    } catch (e) {
      debugPrint('ValidationService.generateHypothesis error: $e');
    }
    return null;
  }

  static Future<ValidationExperimentModel?> recommendExperiment(int projectId, int hypothesisId) async {
    try {
      final res = await ApiClient.post(
        '/projects/$projectId/validation/hypotheses/$hypothesisId/recommend-experiment',
      );
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final list = await getExperiments(projectId);
        return list.isNotEmpty ? list.first : null;
      }
    } catch (e) {
      debugPrint('ValidationService.recommendExperiment error: $e');
    }
    return null;
  }

  static Future<List<ValidationHypothesisModel>> getHypotheses(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/hypotheses');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final list = jsonDecode(res.body) as List<dynamic>;
        return list.map((e) => ValidationHypothesisModel.fromJson(e)).toList();
      }
    } catch (e) {
      debugPrint('ValidationService.getHypotheses error: $e');
    }
    return [];
  }

  static Future<List<ValidationExperimentModel>> getExperiments(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/experiments');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final list = jsonDecode(res.body) as List<dynamic>;
        return list.map((e) => ValidationExperimentModel.fromJson(e)).toList();
      }
    } catch (e) {
      debugPrint('ValidationService.getExperiments error: $e');
    }
    return [];
  }

  static Future<List<ValidationEvidenceModel>> getEvidence(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/evidence');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final list = jsonDecode(res.body) as List<dynamic>;
        return list.map((e) => ValidationEvidenceModel.fromJson(e)).toList();
      }
    } catch (e) {
      debugPrint('ValidationService.getEvidence error: $e');
    }
    return [];
  }

  static Future<ValidationReviewModel?> performAiReview(int projectId, int hypothesisId) async {
    try {
      final res = await ApiClient.post('/projects/$projectId/validation/hypotheses/$hypothesisId/review/ai');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        return ValidationReviewModel.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint('ValidationService.performAiReview error: $e');
    }
    return null;
  }

  static Future<NextBestActionDetailModel?> getNextBestAction(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/next-best-action');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        return NextBestActionDetailModel.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint('ValidationService.getNextBestAction error: $e');
    }
    return null;
  }

  static Future<ValidationReviewModel?> getLatestReview(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/reviews/latest');
      if (res.statusCode >= 200 && res.statusCode < 300 && res.body.isNotEmpty) {
        final data = jsonDecode(res.body);
        if (data != null) return ValidationReviewModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('ValidationService.getLatestReview error: $e');
    }
    return null;
  }

  // -------------------------------------------------------------------------
  // F2 & F3: PROBLEM-FIRST & CUSTOMER DISCOVERY API METHODS
  // -------------------------------------------------------------------------

  static Future<ProblemScorecardModel?> getProblemScorecard(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/problem-scorecard');
      if (res.statusCode >= 200 && res.statusCode < 300 && res.body.isNotEmpty) {
        return ProblemScorecardModel.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint('ValidationService.getProblemScorecard error: $e');
    }
    return null;
  }

  static Future<ProblemScorecardModel?> updateProblemScorecard(
    int projectId, {
    required int frequencyScore,
    required int severityScore,
    required int alternativesScore,
    required int wtpScore,
    required int marketPotentialScore,
    String? notes,
  }) async {
    try {
      final res = await ApiClient.post(
        '/projects/$projectId/validation/problem-scorecard',
        body: {
          'frequency_score': frequencyScore,
          'severity_score': severityScore,
          'alternatives_score': alternativesScore,
          'wtp_score': wtpScore,
          'market_potential_score': marketPotentialScore,
          'notes': notes,
        },
      );
      if (res.statusCode >= 200 && res.statusCode < 300) {
        return ProblemScorecardModel.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint('ValidationService.updateProblemScorecard error: $e');
    }
    return null;
  }

  static Future<RoleCoverageModel?> getRoleCoverage(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/role-coverage');
      if (res.statusCode >= 200 && res.statusCode < 300 && res.body.isNotEmpty) {
        return RoleCoverageModel.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint('ValidationService.getRoleCoverage error: $e');
    }
    return null;
  }

  static Future<SolutionBiasRiskModel?> getSolutionBiasRisk(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/solution-bias');
      if (res.statusCode >= 200 && res.statusCode < 300 && res.body.isNotEmpty) {
        return SolutionBiasRiskModel.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint('ValidationService.getSolutionBiasRisk error: $e');
    }
    return null;
  }

  static Future<List<CustomerContactModel>> getContacts(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/contacts');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final list = jsonDecode(res.body) as List<dynamic>;
        return list.map((e) => CustomerContactModel.fromJson(e)).toList();
      }
    } catch (e) {
      debugPrint('ValidationService.getContacts error: $e');
    }
    return [];
  }

  static Future<List<CustomerInterviewSessionModel>> getInterviews(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/interviews');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final list = jsonDecode(res.body) as List<dynamic>;
        return list.map((e) => CustomerInterviewSessionModel.fromJson(e)).toList();
      }
    } catch (e) {
      debugPrint('ValidationService.getInterviews error: $e');
    }
    return [];
  }

  static Future<List<VerbatimQuoteModel>> getQuotes(int projectId) async {
    try {
      final res = await ApiClient.get('/projects/$projectId/validation/quotes');
      if (res.statusCode >= 200 && res.statusCode < 300) {
        final list = jsonDecode(res.body) as List<dynamic>;
        return list.map((e) => VerbatimQuoteModel.fromJson(e)).toList();
      }
    } catch (e) {
      debugPrint('ValidationService.getQuotes error: $e');
    }
    return [];
  }
}



