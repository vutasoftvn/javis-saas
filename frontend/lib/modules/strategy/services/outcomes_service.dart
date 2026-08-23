import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';

class OutcomesService extends WorkspaceService {
  /// Lấy danh sách Objectives / Outcomes từ Encore: GET /operations/objectives
  Future<List<dynamic>> getOutcomes({String? status}) async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.get('/operations/objectives?workspaceId=$wId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data is Map<String, dynamic>) {
          return data['objectives'] ?? data['outcomes'] ?? [];
        } else if (data is List) {
          return data;
        }
      }
    } catch (e) {
      debugPrint('[OutcomesService] getOutcomes error: $e');
    }
    return [];
  }

  /// Tạo Objective mới qua Encore: POST /operations/objectives
  Future<Map<String, dynamic>?> createObjective({
    required dynamic cycleId,
    required String title,
    String? why,
    dynamic ownerId,
  }) async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.post(
        '/operations/objectives',
        body: {
          'workspaceId': wId,
          'cycleId': cycleId?.toString() ?? '1',
          'title': title,
          'why': why,
          'ownerId': ownerId?.toString(),
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[OutcomesService] createObjective error: $e');
    }
    return null;
  }

  /// Thêm Key Result vào Objective: POST /operations/objectives/:id/key-results
  Future<Map<String, dynamic>?> addKeyResult({
    required dynamic objectiveId,
    required String title,
    required double targetValue,
    String unit = 'count',
  }) async {
    try {
      final objId = objectiveId.toString();
      final response = await ApiClient.post(
        '/operations/objectives/$objId/key-results',
        body: {
          'objectiveId': objId,
          'title': title,
          'targetValue': targetValue,
          'unit': unit,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[OutcomesService] addKeyResult error: $e');
    }
    return null;
  }

  /// Lấy tiến độ OKR: GET /operations/objectives/:id/progress
  Future<Map<String, dynamic>?> getObjectiveProgress(dynamic objectiveId) async {
    try {
      final objId = objectiveId.toString();
      final response = await ApiClient.get('/operations/objectives/$objId/progress');
      if (response.statusCode == 200) {
        return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[OutcomesService] getObjectiveProgress error: $e');
    }
    return null;
  }

  /// Alias createOutcome giữ tương thích
  Future<Map<String, dynamic>?> createOutcome(Map<String, dynamic> data) async {
    final cycleId = data['cycleId'] ?? data['cycle_id'] ?? 1;
    final title = data['title'] ?? 'New Objective';
    return createObjective(cycleId: cycleId is int ? cycleId : int.tryParse(cycleId.toString()) ?? 1, title: title.toString(), why: data['why']?.toString());
  }

  Future<Map<String, dynamic>?> triggerRun(String outcomeId) async {
    final res = await postJson('/operations/initiatives', {'outcome_id': outcomeId});
    return res is Map<String, dynamic> ? res : null;
  }

  Future<Map<String, dynamic>?> getRunDetails(String runId) async {
    final res = await getJson('/operations/initiatives/$runId');
    return res is Map<String, dynamic> ? res : null;
  }

  Future<List<dynamic>> getArtifacts({String? type}) async {
    return [];
  }
}
