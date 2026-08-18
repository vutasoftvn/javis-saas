import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../models/twelve_wy_model.dart';
import '../../core/network/api_client.dart';

class TwelveWyService {
  /// Lấy toàn cảnh Dashboard 12-Week Year của dự án
  Future<TwelveWyDashboardModel?> getDashboard(int projectId) async {
    try {
      final response = await ApiClient.get('/strategy/12wy/dashboard/$projectId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return TwelveWyDashboardModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[TwelveWyService] getDashboard error: $e');
    }
    return null;
  }

  /// Khởi tạo hoặc lấy chu kỳ 12 tuần
  Future<TwelveWeekCycleModel?> createOrGetCycle(int projectId, {String? title}) async {
    try {
      final response = await ApiClient.post(
        '/strategy/12wy/cycle',
        body: {
          'project_id': projectId,
          'title': title ?? 'Chu Kỳ 12 Tuần',
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

  /// Tạo hành động chiến thuật (Tactic) mới
  Future<TacticalItemModel?> createTactic({
    required int projectId,
    int? cycleId,
    required int weekNumber,
    required String title,
    String description = '',
    int? towsOptionId,
    int? hypothesisId,
    required String leadIndicatorName,
    int targetCount = 1,
    int actualCount = 0,
    String status = 'PLANNED',
    String ownerRole = 'Founder',
  }) async {
    try {
      final response = await ApiClient.post(
        '/strategy/12wy/tactics',
        body: {
          'project_id': projectId,
          'cycle_id': cycleId,
          'week_number': weekNumber,
          'title': title,
          'description': description,
          'tows_option_id': towsOptionId,
          'hypothesis_id': hypothesisId,
          'lead_indicator_name': leadIndicatorName,
          'target_count': targetCount,
          'actual_count': actualCount,
          'status': status,
          'owner_role': ownerRole,
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
