import 'dart:convert';

import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';
import '../../../data/models/execution_plan_model.dart';

/// WGA — client cho weekly-goal + execution-plans (kế hoạch triển khai agent
/// đề xuất). Xác thực workspace do `ApiClient` gắn header X-Workspace-Id.
class ExecutionPlanService extends WorkspaceScopedService {
  Future<String> _requireWorkspaceId() async {
    final w = await stringWorkspaceId();
    if (w == null || w.isEmpty) throw StateError('No active workspace selected');
    return w;
  }

  /// Đặt / cập nhật mục tiêu tuần. `triggerDecomposition=true` -> agent lập kế hoạch.
  Future<void> setWeeklyGoal(
    String projectId,
    String focus, {
    String? mission,
    bool triggerDecomposition = true,
    String origin = 'command_center',
    String? originRef,
  }) async {
    if (projectId.isEmpty) throw ArgumentError('projectId cannot be empty');
    await _requireWorkspaceId();
    final res = await ApiClient.post(
      '/operations/strategy/projects/$projectId/weekly-goal',
      body: {
        'focus': focus,
        'mission': ?mission,
        'triggerDecomposition': triggerDecomposition,
        'origin': origin,
        'originRef': ?originRef,
      },
    );
    if (res.statusCode == 200) return;
    throw StateError('Failed to set weekly goal: ${res.statusCode} ${res.body}');
  }

  Future<List<ExecutionPlan>> listDraftPlans(String projectId) async {
    await _requireWorkspaceId();
    final res = await ApiClient.get(
      '/operations/execution-plans?projectId=$projectId&status=draft',
    );
    if (res.statusCode != 200) {
      if (res.statusCode == 404) return const [];
      throw StateError('Failed to list execution plans: ${res.statusCode}');
    }
    final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    final list = (data['plans'] as List<dynamic>?) ?? const [];
    return list
        .map((e) => ExecutionPlan.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> acceptPlan(String planId) async {
    await _requireWorkspaceId();
    final res = await ApiClient.post('/operations/execution-plans/$planId/accept');
    if (res.statusCode == 200) return;
    throw StateError('Failed to accept plan: ${res.statusCode} ${res.body}');
  }

  Future<void> rejectPlan(String planId) async {
    await _requireWorkspaceId();
    final res = await ApiClient.post('/operations/execution-plans/$planId/reject');
    if (res.statusCode == 200) return;
    throw StateError('Failed to reject plan: ${res.statusCode} ${res.body}');
  }

  /// Sửa 1 item trước khi duyệt. Trả về item đã cập nhật, hoặc ném lỗi
  /// (vd. nâng AUTO trái phép -> 403).
  Future<ExecutionPlanItem> updateItem(
    String planId,
    String itemId, {
    String? title,
    List<String>? evidenceRefs,
    String? priority,
    AutonomyClass? autonomyClass,
    bool? drop,
  }) async {
    await _requireWorkspaceId();
    final res = await ApiClient.patch(
      '/operations/execution-plans/$planId/items/$itemId',
      body: {
        'title': ?title,
        'evidenceRefs': ?evidenceRefs,
        'priority': ?priority,
        if (autonomyClass != null)
          'autonomyClass': autonomyClassToString(autonomyClass),
        'drop': ?drop,
      },
    );
    if (res.statusCode == 200) {
      return ExecutionPlanItem.fromJson(
        jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>,
      );
    }
    if (res.statusCode == 403) {
      throw StateError('Không cho phép: ${res.body}');
    }
    throw StateError('Failed to update plan item: ${res.statusCode} ${res.body}');
  }
}
