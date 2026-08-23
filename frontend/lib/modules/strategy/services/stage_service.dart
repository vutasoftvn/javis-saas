import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../data/models/stage_model.dart';

class StageService {
  Future<List<Map<String, dynamic>>> listStagePolicies({int? workspaceId, int? companyId, String? stageKey}) async {
    try {
      final params = <String>[];
      if (workspaceId != null) params.add('workspaceId=$workspaceId');
      if (companyId != null) params.add('companyId=$companyId');
      if (stageKey != null) params.add('stageKey=$stageKey');
      final query = params.isNotEmpty ? '?${params.join('&')}' : '';

      final response = await ApiClient.get('/operations/strategy/stage-policies$query');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data is List) return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
        if (data is Map && data['policies'] is List) {
          return (data['policies'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
        }
      }
    } catch (e) {
      debugPrint('StageService.listStagePolicies error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> createStageTransition({
    required int workspaceId,
    required int companyId,
    required int projectId,
    required String fromStage,
    required String toStage,
    String transitionType = 'PROMOTE',
    String? rationale,
    int? gateEvaluationId,
    int? approvedBy,
  }) async {
    try {
      final response = await ApiClient.post(
        '/operations/strategy/stage-transitions',
        body: {
          'workspaceId': workspaceId,
          'companyId': companyId,
          'projectId': projectId,
          'fromStage': fromStage,
          'toStage': toStage,
          'transitionType': transitionType,
          'rationale': rationale ?? 'Stage promotion initiated by founder',
          'gateEvaluationId': ?gateEvaluationId,
          'approvedBy': ?approvedBy,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('StageService.createStageTransition error: $e');
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> listStageTransitions({int? workspaceId, int? projectId}) async {
    try {
      final params = <String>[];
      if (workspaceId != null) params.add('workspaceId=$workspaceId');
      if (projectId != null) params.add('projectId=$projectId');
      final query = params.isNotEmpty ? '?${params.join('&')}' : '';

      final response = await ApiClient.get('/operations/strategy/stage-transitions$query');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data is List) return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
        if (data is Map && data['transitions'] is List) {
          return (data['transitions'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
        }
      }
    } catch (e) {
      debugPrint('StageService.listStageTransitions error: $e');
    }
    return [];
  }

  Future<StageContextModel?> getStageContext({int? projectId}) async {
    try {
      final query = projectId != null ? '?project_id=$projectId' : '';
      final response = await ApiClient.get('/operations/strategy/stage-context$query');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return StageContextModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('StageService.getStageContext error: $e');
    }
    return null;
  }

  Future<StagePolicyModel?> getStagePolicy(ProjectStage stage) async {
    try {
      final response = await ApiClient.get('/operations/strategy/stage-policies?stageKey=${stage.toServerString()}');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return StagePolicyModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('StageService.getStagePolicy error: $e');
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> listAllStages() async {
    return listStagePolicies();
  }

  Future<StageContextModel?> updateProjectStage(
    int projectId, {
    ProjectStage? projectStage,
    String? stageGoal,
    List<String>? criticalConstraints,
    Map<String, dynamic>? exitCriteria,
    Map<String, dynamic>? stageMetadata,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (projectStage != null) body['project_stage'] = projectStage.toServerString();
      if (stageGoal != null) body['stage_goal'] = stageGoal;
      if (criticalConstraints != null) body['critical_constraints'] = criticalConstraints;
      if (exitCriteria != null) body['exit_criteria'] = exitCriteria;
      if (stageMetadata != null) body['stage_metadata'] = stageMetadata;

      final response = await ApiClient.patch(
        '/operations/strategy/projects/$projectId/stage',
        body: body,
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return StageContextModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('StageService.updateProjectStage error: $e');
    }
    return null;
  }
}
