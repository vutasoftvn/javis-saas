import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_result.dart';
import '../../../core/services/secure_storage_service.dart';
import '../../../data/models/company_pulse_model.dart';
import '../../../data/models/founder_decision_model.dart';
import '../../../data/models/workforce_pack_model.dart';
import '../../workforce/services/workforce_mvp_service.dart';

class CoFounderApiService {
  /// Lấy thông tin nhịp tim tổng thể của dự án (Company Pulse) từ Backend.
  /// Task 6 — projectId là bắt buộc. Endpoint `/operations/strategy/projects/{projectId}/next-best-actions`
  /// là project-scoped. Tuy nhiên `/operations/tasks` là workspace-only mà không có
  /// project-scoped variant, nên tạm thời hiển thị metrics dựa trên Project activity.
  /// TODO (Gap-TBD): Thay thế task count bằng Activity Feed projection khi
  /// `/agent/projects/{project_id}/activity` được integrate hoàn chỉnh.
  static Future<CompanyPulseModel> getCompanyPulse({
    dynamic workspaceId,
    required String projectId,
    String? stage,
  }) async {
    try {
      final wId = workspaceId?.toString() ?? await SecureStorageService.read('workspace_id');
      if (wId == null || wId.isEmpty) {
        return CompanyPulseModel(
          goalsOnTrack: 0,
          totalActiveGoals: 0,
          activeMissions: 0,
          needsDecisionCount: 0,
          pendingApprovalsCount: 0,
          majorRisksCount: 0,
          companyStage: stage,
          suggestedFocus: 'Chưa có dự án nào trong workspace. Hãy khởi tạo dự án đầu tiên để bắt đầu!',
          updatedAt: DateTime.now(),
        );
      }

      // 1. Fetch tasks — workspace-wide. Backend /operations/tasks không filter
      // theo project, chỉ trả tất cả task của workspace. Task6 spec yêu cầu
      // không dùng workspace-wide fallback, nên tạm gán 0 tới khi có
      // Activity Feed project-scoped.
      int activeGoals = 0;
      int goalsOnTrack = 0;
      // TODO (Gap-TBD): Replace with Activity Feed
      // final tasksRes = await ApiClient.get('/operations/tasks?workspaceId=$wId');
      // if (tasksRes.statusCode == 200) {...}

      // 2. Fetch decisions — backend accepts projectId parameter
      final decisions = await listPendingDecisions(
        workspaceId: wId,
        projectId: projectId,
      );

      // 3. Fetch Next Best Actions — project-scoped endpoint
      final top3 = await getTop3Focus(
        workspaceId: wId,
        projectId: projectId,
      );

      return CompanyPulseModel(
        goalsOnTrack: goalsOnTrack,
        totalActiveGoals: activeGoals,
        activeMissions: top3.length,
        needsDecisionCount: decisions.length,
        pendingApprovalsCount: 0,
        majorRisksCount: 0,
        companyStage: stage,
        suggestedFocus: null,
        updatedAt: DateTime.now(),
      );
    } catch (e) {
      debugPrint('[CoFounderApiService] getCompanyPulse exception: $e');
    }
    return CompanyPulseModel(
      goalsOnTrack: 0,
      totalActiveGoals: 0,
      activeMissions: 0,
      needsDecisionCount: 0,
      pendingApprovalsCount: 0,
      majorRisksCount: 0,
      companyStage: stage,
      suggestedFocus: null,
      updatedAt: DateTime.now(),
    );
  }

  /// Lấy Top 3 hành động tốt nhất hôm nay (Next Best Action) từ Backend.
  /// Task 6 — projectId là bắt buộc, project-scoped endpoint đã có sẵn.
  static Future<List<NextBestActionModel>> getTop3Focus({
    dynamic workspaceId,
    required String projectId,
  }) async {
    try {
      final response = await ApiClient.get(
        '/operations/strategy/projects/$projectId/next-best-actions',
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final items = (data['items'] as List<dynamic>?) ?? [];
        return items
            .map((e) => NextBestActionModel.fromJson(e as Map<String, dynamic>))
            .where((a) => a.title.trim().isNotEmpty)
            .toList();
      }
    } catch (e) {
      debugPrint('[CoFounderApiService] getTop3Focus exception: $e');
    }
    return [];
  }

  /// Lấy danh sách các quyết định đang chờ Founder duyệt ('Waiting for You') từ Backend.
  /// Task 6 — projectId là bắt buộc. Backend endpoint
  /// `/operations/strategy/decision-records` chấp nhận `projectId` query parameter
  /// để filter theo project.
  static Future<List<FounderDecisionModel>> listPendingDecisions({
    dynamic workspaceId,
    required String projectId,
  }) async {
    try {
      final wId = workspaceId?.toString() ?? await SecureStorageService.read('workspace_id');
      if (wId == null || wId.isEmpty) return [];
      final response = await ApiClient.get(
        '/operations/strategy/decision-records?projectId=$projectId',
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final List<dynamic> list = data is List
            ? data
            : (data['decisionRecords'] as List? ??
                data['items'] as List? ??
                data['records'] as List? ??
                []);
        return list
            .map((e) => FounderDecisionModel.fromJson(e as Map<String, dynamic>))
            .toList();
      }
    } catch (e) {
      debugPrint('[CoFounderApiService] listPendingDecisions exception: $e');
    }
    return [];
  }

  /// Chốt quyết định chiến lược.
  /// Task 6 — projectId là bắt buộc để ensure project context khi resolve decision.
  static Future<bool> resolveDecision({
    required dynamic decisionId,
    required String projectId,
    required String decisionMade,
    String? founderNotes,
  }) async {
    try {
      final response = await ApiClient.patch(
        '/operations/strategy/decision-records/${decisionId.toString()}',
        body: {
          'project_id': projectId,
          'decision': decisionMade,
          'rationale': founderNotes ?? 'Decided by founder',
        },
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[CoFounderApiService] resolveDecision error: $e');
      return false;
    }
  }

  /// Task 3 (Truthful MVP Hardening) — `/workforce/packs` không có canonical
  /// backend nào cả, nên trước đây mọi lỗi/404 bị nuốt và thay bằng danh sách
  /// giả 5 domain mặc định — một "success" ảo. Giờ gọi thẳng canonical
  /// `/agent/workforce/composition` qua `WorkforceMvpService`: chỉ hiển thị
  /// đúng những functional agent mà backend thực sự biết tới.
  ///
  /// Fix-review (2026-09-01): trả `ApiResult<List<WorkforcePackModel>>` thay
  /// vì `List` trần — nếu không, "gọi thất bại" và "gọi thành công nhưng
  /// workspace chưa gán agent nào" đều thành `[]` giống hệt nhau, khiến
  /// caller (founder_command_center_controller.dart) không thể phân biệt
  /// để hiển thị trạng thái "unavailable" đúng như brief Step 4 yêu cầu.
  static Future<ApiResult<List<WorkforcePackModel>>> listWorkforcePacks({
    int? workspaceId,
    WorkforceMvpService? workforceMvpService,
  }) async {
    final service = workforceMvpService ?? WorkforceMvpService();
    final result = await service.getComposition();
    return result.when(
      success: (entries, meta) => ApiSuccess(
        data: entries
            .map(
              (e) => WorkforcePackModel(
                key: e.functionalKey,
                name: e.title,
                roleTitle: e.title,
                department: null,
                category: 'DOMAIN',
                isCore: false,
                isActive: e.assigned,
                description: e.description,
              ),
            )
            .toList(),
        meta: meta,
      ),
      failure: (failure) {
        debugPrint('[CoFounderApiService] listWorkforcePacks failure: ${failure.message}');
        return ApiFailure<List<WorkforcePackModel>>(failure);
      },
    );
  }

  /// Task 3 — `/workforce/packs/:key/toggle` không có canonical backend.
  /// Không còn route nào để bật/tắt pack ở mức này; trả `false` (không thực
  /// hiện thay đổi nào) thay vì giả vờ gọi API rồi coi lỗi là thành công.
  /// UI phía founder command center cần hiển thị trạng thái "unavailable"
  /// cho hành động này.
  static Future<bool> toggleOptionalPack({
    required String packKey,
    required bool isActive,
    int? workspaceId,
  }) async {
    debugPrint(
      '[CoFounderApiService] toggleOptionalPack unavailable: no canonical route for pack toggle ($packKey)',
    );
    return false;
  }
}
