import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../data/models/evidence_model.dart';

class EvidenceService {
  Future<List<HypothesisModel>> getHypotheses({
    dynamic projectId,
    dynamic workspaceId,
    String? category,
    String? status,
  }) async {
    try {
      final params = <String>[];
      if (projectId != null) params.add('projectId=${projectId.toString()}');
      if (workspaceId != null) params.add('workspaceId=${workspaceId.toString()}');
      if (category != null) params.add('category=$category');
      if (status != null) params.add('status=$status');

      final query = params.isNotEmpty ? '?${params.join('&')}' : '';
      final response = await ApiClient.get('/operations/strategy/assumptions$query');

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is List ? data : (data['assumptions'] as List? ?? []);
        return list.map((item) => HypothesisModel.fromJson(item as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('EvidenceService.getHypotheses error: $e');
    }
    return [];
  }

  Future<HypothesisModel?> createHypothesis(Map<String, dynamic> data) async {
    try {
      final response = await ApiClient.post('/operations/strategy/assumptions', body: data);
      if (response.statusCode == 200 || response.statusCode == 201) {
        return HypothesisModel.fromJson(jsonDecode(utf8.decode(response.bodyBytes)));
      }
    } catch (e) {
      debugPrint('EvidenceService.createHypothesis error: $e');
    }
    return null;
  }

  Future<List<EvidenceModel>> getEvidences({
    dynamic projectId,
    dynamic workspaceId,
    String? ladderLevel,
    String? type,
  }) async {
    try {
      final params = <String>[];
      if (projectId != null) params.add('projectId=${projectId.toString()}');
      if (workspaceId != null) params.add('workspaceId=${workspaceId.toString()}');
      if (ladderLevel != null) params.add('ladderLevel=$ladderLevel');
      if (type != null) params.add('type=$type');

      final query = params.isNotEmpty ? '?${params.join('&')}' : '';
      final response = await ApiClient.get('/operations/strategy/evidence$query');

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is List ? data : (data['evidence'] as List? ?? []);
        return list.map((item) => EvidenceModel.fromJson(item as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('EvidenceService.getEvidences error: $e');
    }
    return [];
  }

  Future<EvidenceModel?> createEvidence(Map<String, dynamic> data) async {
    try {
      final response = await ApiClient.post('/operations/strategy/evidence', body: data);
      if (response.statusCode == 200 || response.statusCode == 201) {
        return EvidenceModel.fromJson(jsonDecode(utf8.decode(response.bodyBytes)));
      }
    } catch (e) {
      debugPrint('EvidenceService.createEvidence error: $e');
    }
    return null;
  }

  Future<AssumptionMatrixModel?> getAssumptionMatrix(dynamic projectId) async {
    try {
      final pId = projectId?.toString() ?? '1';
      final response = await ApiClient.get('/operations/strategy/assumptions?projectId=$pId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data is Map<String, dynamic> && data.containsKey('quadrants')) {
          return AssumptionMatrixModel.fromJson(data);
        }
        final list = data is List ? data : (data is Map && data['assumptions'] is List ? data['assumptions'] as List : []);
        final hypotheses = list.map((e) => HypothesisModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();
        return AssumptionMatrixModel(
          projectId: int.tryParse(pId) ?? 1,
          totalHypotheses: hypotheses.length,
          criticalCount: hypotheses.where((h) => h.isCritical).length,
          criticalTestFirst: hypotheses.where((h) => h.isCritical).toList(),
          monitor: hypotheses.where((h) => !h.isCritical && h.uncertainty > 0.5).toList(),
          importantLowRisk: hypotheses.where((h) => h.importance > 0.5 && h.uncertainty <= 0.5).toList(),
          lowPriority: hypotheses.where((h) => h.importance <= 0.5 && h.uncertainty <= 0.5).toList(),
        );
      }
    } catch (e) {
      debugPrint('EvidenceService.getAssumptionMatrix error: $e');
    }
    return null;
  }

  Future<List<StrategicDecisionModel>> getDecisions({dynamic projectId, dynamic workspaceId}) async {
    try {
      final params = <String>[];
      if (projectId != null) params.add('projectId=${projectId.toString()}');
      if (workspaceId != null) params.add('workspaceId=${workspaceId.toString()}');
      final query = params.isNotEmpty ? '?${params.join('&')}' : '';
      final response = await ApiClient.get('/operations/strategy/decision-records$query');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is List ? data : (data['decisionRecords'] as List? ?? data['records'] as List? ?? []);
        return list.map((item) => StrategicDecisionModel.fromJson(item as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('EvidenceService.getDecisions error: $e');
    }
    return [];
  }

  Future<StrategicDecisionModel?> recordDecision(Map<String, dynamic> data) async {
    try {
      final response = await ApiClient.post('/operations/strategy/decision-records', body: data);
      if (response.statusCode == 200 || response.statusCode == 201) {
        return StrategicDecisionModel.fromJson(jsonDecode(utf8.decode(response.bodyBytes)));
      }
    } catch (e) {
      debugPrint('EvidenceService.recordDecision error: $e');
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> queryCompanyMemory({
    String? queryText,
    dynamic projectId,
  }) async {
    try {
      final params = <String>[];
      if (queryText != null && queryText.isNotEmpty) params.add('queryText=$queryText');
      if (projectId != null) params.add('projectId=${projectId.toString()}');

      final query = params.isNotEmpty ? '?${params.join('&')}' : '';
      final response = await ApiClient.get('/operations/strategy/decision-records$query');

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is List ? data : (data['decisionRecords'] as List? ?? []);
        return list.map((item) => item as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('EvidenceService.queryCompanyMemory error: $e');
    }
    return [];
  }
}
