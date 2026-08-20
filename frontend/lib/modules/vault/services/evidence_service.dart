import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../data/models/evidence_model.dart';

class EvidenceService {
  Future<List<HypothesisModel>> getHypotheses({
    int? projectId,
    String? category,
    String? status,
  }) async {
    try {
      final params = <String>[];
      if (projectId != null) params.add('project_id=$projectId');
      if (category != null) params.add('category=$category');
      if (status != null) params.add('status=$status');

      final query = params.isNotEmpty ? '?${params.join('&')}' : '';
      final response = await ApiClient.get('/strategy/evidence/hypotheses$query');

      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List;
        return list.map((item) => HypothesisModel.fromJson(item)).toList();
      }
    } catch (e) {
      debugPrint('EvidenceService.getHypotheses error: $e');
    }
    return [];
  }

  Future<HypothesisModel?> createHypothesis(Map<String, dynamic> data) async {
    try {
      final response = await ApiClient.post('/strategy/evidence/hypotheses', body: data);
      if (response.statusCode == 200 || response.statusCode == 201) {
        return HypothesisModel.fromJson(jsonDecode(response.body));
      }
    } catch (e) {
      debugPrint('EvidenceService.createHypothesis error: $e');
    }
    return null;
  }

  Future<List<EvidenceModel>> getEvidences({
    int? projectId,
    String? ladderLevel,
    String? type,
  }) async {
    try {
      final params = <String>[];
      if (projectId != null) params.add('project_id=$projectId');
      if (ladderLevel != null) params.add('ladder_level=$ladderLevel');
      if (type != null) params.add('type=$type');

      final query = params.isNotEmpty ? '?${params.join('&')}' : '';
      final response = await ApiClient.get('/strategy/evidence/evidences$query');

      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List;
        return list.map((item) => EvidenceModel.fromJson(item)).toList();
      }
    } catch (e) {
      debugPrint('EvidenceService.getEvidences error: $e');
    }
    return [];
  }

  Future<EvidenceModel?> createEvidence(Map<String, dynamic> data) async {
    try {
      final response = await ApiClient.post('/strategy/evidence/evidences', body: data);
      if (response.statusCode == 200 || response.statusCode == 201) {
        return EvidenceModel.fromJson(jsonDecode(response.body));
      }
    } catch (e) {
      debugPrint('EvidenceService.createEvidence error: $e');
    }
    return null;
  }

  Future<AssumptionMatrixModel?> getAssumptionMatrix(int projectId) async {
    try {
      final response = await ApiClient.get('/strategy/evidence/matrix/$projectId');
      if (response.statusCode == 200) {
        return AssumptionMatrixModel.fromJson(jsonDecode(response.body));
      }
    } catch (e) {
      debugPrint('EvidenceService.getAssumptionMatrix error: $e');
    }
    return null;
  }

  Future<List<StrategicDecisionModel>> getDecisions({int? projectId}) async {
    try {
      final query = projectId != null ? '?project_id=$projectId' : '';
      final response = await ApiClient.get('/strategy/evidence/decisions$query');
      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List;
        return list.map((item) => StrategicDecisionModel.fromJson(item)).toList();
      }
    } catch (e) {
      debugPrint('EvidenceService.getDecisions error: $e');
    }
    return [];
  }

  Future<StrategicDecisionModel?> recordDecision(Map<String, dynamic> data) async {
    try {
      final response = await ApiClient.post('/strategy/evidence/decisions', body: data);
      if (response.statusCode == 200 || response.statusCode == 201) {
        return StrategicDecisionModel.fromJson(jsonDecode(response.body));
      }
    } catch (e) {
      debugPrint('EvidenceService.recordDecision error: $e');
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> queryCompanyMemory({
    String? queryText,
    int? projectId,
  }) async {
    try {
      final params = <String>[];
      if (queryText != null && queryText.isNotEmpty) params.add('query_text=$queryText');
      if (projectId != null) params.add('project_id=$projectId');

      final query = params.isNotEmpty ? '?${params.join('&')}' : '';
      final response = await ApiClient.get('/strategy/evidence/decisions/memory$query');

      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List;
        return list.map((item) => item as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('EvidenceService.queryCompanyMemory error: $e');
    }
    return [];
  }
}
