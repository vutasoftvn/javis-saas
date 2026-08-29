import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';
import '../../../data/models/okr_models.dart';

class OkrService extends WorkspaceService {
  /// Lấy danh sách OKR Cycles từ Encore backend
  Future<List<OkrCycleDto>> getCycles() async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.get('/operations/okr-cycles?workspace_id=$wId');
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is Map && data['cycles'] is List
            ? data['cycles'] as List<dynamic>
            : (data is List ? data : []);
        return list.map((e) => OkrCycleDto.fromJson(e as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[OkrService] getCycles error: $e');
    }
    return [];
  }

  /// Tạo OKR Cycle mới
  Future<OkrCycleDto?> createCycle(String name) async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.post(
        '/operations/okr-cycles',
        body: {
          'workspaceId': wId,
          'name': name,
        },
      );
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return OkrCycleDto.fromJson(data);
      }
    } catch (e) {
      debugPrint('[OkrService] createCycle error: $e');
    }
    return null;
  }

  /// Lấy danh sách Objectives
  Future<List<ObjectiveDto>> getObjectives({String? cycleId}) async {
    final wId = await stringWorkspaceId() ?? '1';
    final query = cycleId != null
        ? 'workspace_id=$wId&cycle_id=$cycleId'
        : 'workspace_id=$wId';
    try {
      final response = await ApiClient.get('/operations/objectives?$query');
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final list = data is Map && data['objectives'] is List
            ? data['objectives'] as List<dynamic>
            : (data is List ? data : []);
        return list.map((e) => ObjectiveDto.fromJson(e as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[OkrService] getObjectives error: $e');
    }
    return [];
  }

  /// Tạo Objective mới
  Future<ObjectiveDto?> createObjective(
    String title, {
    String? cycleId,
    String? why,
  }) async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.post(
        '/operations/objectives',
        body: {
          'workspaceId': wId,
          'cycleId': cycleId ?? '1',
          'title': title,
          'why': ?why,
        },
      );
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return ObjectiveDto.fromJson(data);
      }
    } catch (e) {
      debugPrint('[OkrService] createObjective error: $e');
    }
    return null;
  }

  /// Xóa Objective
  Future<bool> deleteObjective(String objectiveId) async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.delete('/operations/objectives/$objectiveId?workspace_id=$wId');
      return response.statusCode >= 200 && response.statusCode < 300;
    } catch (e) {
      debugPrint('[OkrService] deleteObjective error: $e');
      return false;
    }
  }

  /// Thêm Key Result vào Objective
  Future<KeyResultDto?> addKeyResult({
    required String objectiveId,
    required String title,
    double targetValue = 100.0,
    String unit = '%',
  }) async {
    try {
      final response = await ApiClient.post(
        '/operations/objectives/$objectiveId/key-results',
        body: {
          'objectiveId': objectiveId,
          'title': title,
          'targetValue': targetValue,
          'unit': unit,
        },
      );
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return KeyResultDto.fromJson(data);
      }
    } catch (e) {
      debugPrint('[OkrService] addKeyResult error: $e');
    }
    return null;
  }

  /// Check-in tiến độ Key Result
  Future<KeyResultDto?> checkinKeyResult(String keyResultId, double value) async {
    try {
      final response = await ApiClient.post(
        '/operations/key-results/$keyResultId/checkin',
        body: {
          'id': keyResultId,
          'value': value,
        },
      );
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return KeyResultDto.fromJson(data);
      }
    } catch (e) {
      debugPrint('[OkrService] checkinKeyResult error: $e');
    }
    return null;
  }
}
