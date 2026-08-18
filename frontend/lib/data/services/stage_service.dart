import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../core/network/api_client.dart';
import '../models/stage_model.dart';

class StageService {
  Future<StageContextModel?> getStageContext({int? projectId}) async {
    try {
      final query = projectId != null ? '?project_id=$projectId' : '';
      final response = await ApiClient.get('/strategy/stage/context$query');
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
      final response = await ApiClient.get('/strategy/stage/policy/${stage.toServerString()}');
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
    try {
      final response = await ApiClient.get('/strategy/stage/list-stages');
      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List;
        return list.map((item) => item as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('StageService.listAllStages error: $e');
    }
    return [];
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
        '/strategy/stage/project/$projectId',
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
