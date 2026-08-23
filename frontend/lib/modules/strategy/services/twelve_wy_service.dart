import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';
import '../../../data/models/twelve_wy_model.dart';

class TwelveWyService extends WorkspaceService {
  /// Lấy danh sách chu kỳ 12 tuần từ Encore: GET /operations/workspaces/:workspaceId/cycles
  Future<List<TwelveWeekCycleModel>> getCycles() async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.get('/operations/workspaces/$wId/cycles');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        final list = (data['cycles'] as List<dynamic>?) ?? [];
        return list.map((e) => TwelveWeekCycleModel.fromJson(e as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[TwelveWyService] getCycles error: $e');
    }
    return [];
  }

  /// Lấy toàn cảnh Dashboard 12-Week Year của dự án
  Future<TwelveWyDashboardModel?> getDashboard(dynamic projectId) async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.get('/operations/workspaces/$wId/cycles');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        final cycles = (data['cycles'] as List<dynamic>?) ?? [];
        if (cycles.isNotEmpty) {
          final activeCycle = TwelveWeekCycleModel.fromJson(cycles.first as Map<String, dynamic>);
          return TwelveWyDashboardModel(
            cycle: activeCycle,
            currentWeek: activeCycle.currentWeek,
            currentWeekExecutionScore: activeCycle.overallExecutionScore,
            tacticsByWeek: {},
            weeklyScores: {},
          );
        }
      }
    } catch (e) {
      debugPrint('[TwelveWyService] getDashboard error: $e');
    }
    return null;
  }

  /// Khởi tạo hoặc lấy chu kỳ 12 tuần mới qua Encore: POST /operations/cycles
  Future<TwelveWeekCycleModel?> createOrGetCycle(dynamic projectId, {String? title, String? visionStatement}) async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.post(
        '/operations/cycles',
        body: {
          'workspaceId': wId,
          'projectId': projectId?.toString() ?? '1',
          'theme': title ?? 'Chu Kỳ 12 Tuần',
          'visionStatement': visionStatement ?? 'Xây dựng và tăng trưởng',
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return TwelveWeekCycleModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[TwelveWyService] createOrGetCycle error: $e');
    }
    return null;
  }

  /// Tạo Kế hoạch tuần qua Encore: POST /operations/weekly-plans
  Future<Map<String, dynamic>?> createWeeklyPlan({
    required dynamic cycleId,
    required int weekNo,
    String? focus,
    String? mission,
  }) async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.post(
        '/operations/weekly-plans',
        body: {
          'workspaceId': wId,
          'cycleId': cycleId?.toString() ?? '1',
          'weekNo': weekNo,
          'focus': ?focus,
          'mission': ?mission,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[TwelveWyService] createWeeklyPlan error: $e');
    }
    return null;
  }

  /// Tạo Cam kết hành động chiến thuật (Commitment / Tactic) qua Encore: POST /operations/weekly-commitments
  Future<TacticalItemModel?> createTactic({
    required dynamic projectId,
    dynamic cycleId,
    required int weekNumber,
    required String title,
    String description = '',
    dynamic towsOptionId,
    dynamic hypothesisId,
    required String leadIndicatorName,
    int targetCount = 1,
    int actualCount = 0,
    String status = 'PLANNED',
    String ownerRole = 'Founder',
  }) async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.post(
        '/operations/weekly-commitments',
        body: {
          'workspaceId': wId,
          'weeklyPlanId': weekNumber.toString(),
          'title': title,
          'plannedEffort': targetCount.toString(),
          'commitmentOwnerType': ownerRole,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return TacticalItemModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[TwelveWyService] createTactic error: $e');
    }
    return null;
  }

  /// Cập nhật tiến độ chỉ số dẫn dắt hoặc trạng thái
  Future<TacticalItemModel?> updateTactic({
    required int tacticId,
    int? actualCount,
    String? status,
    String? title,
    String? description,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (actualCount != null) body['actual_count'] = actualCount;
      if (status != null) body['status'] = status;
      if (title != null) body['title'] = title;
      if (description != null) body['description'] = description;

      final response = await ApiClient.put(
        '/strategy/12wy/tactics/$tacticId',
        body: body,
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return TacticalItemModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[TwelveWyService] updateTactic error: $e');
    }
    return null;
  }

  /// Tạo bản tổng kết phiên họp kiểm điểm WAM
  Future<WeeklyReviewModel?> generateWeeklyReview({
    required int cycleId,
    required int weekNumber,
  }) async {
    try {
      final response = await ApiClient.post(
        '/strategy/12wy/weekly-review/$cycleId/$weekNumber',
        body: {},
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return WeeklyReviewModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[TwelveWyService] generateWeeklyReview error: $e');
    }
    return null;
  }
}
