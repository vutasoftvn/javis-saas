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
  /// Lấy thông tin nhịp tim tổng thể của doanh nghiệp (Company Pulse) từ Backend
  static Future<CompanyPulseModel> getCompanyPulse({dynamic workspaceId, dynamic projectId, String? stage}) async {
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
      final pId = projectId?.toString();

      // 1. Fetch tasks
      final tasksRes = await ApiClient.get('/operations/tasks?workspaceId=$wId');
      int activeGoals = 0;
      int goalsOnTrack = 0;
      if (tasksRes.statusCode == 200) {
        final data = jsonDecode(utf8.decode(tasksRes.bodyBytes));
        final tasksList = (data is Map ? data['tasks'] : data) as List? ?? [];
        activeGoals = tasksList.length;
        goalsOnTrack = tasksList.where((t) => t['status'] == 'completed' || t['status'] == 'in_progress').length;
      }

      // 2. Fetch decisions
      final decisions = await listPendingDecisions(workspaceId: wId);

      // 3. Fetch Next Best Actions
      final top3 = (pId != null && pId.isNotEmpty)
          ? await getTop3Focus(workspaceId: wId, projectId: pId)
          : <NextBestActionModel>[];

      return CompanyPulseModel(
        goalsOnTrack: goalsOnTrack,
        totalActiveGoals: activeGoals,
        activeMissions: top3.length,
        needsDecisionCount: decisions.length,
        pendingApprovalsCount: 0,
        majorRisksCount: 0,
        companyStage: stage,
        suggestedFocus: (pId == null || pId.isEmpty)
            ? 'Chưa có dự án nào trong workspace. Hãy khởi tạo dự án đầu tiên để bắt đầu!'
            : 'Tập trung kiểm chứng bài toán khách hàng và hoàn thiện chiến thuật tuần.',
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
      suggestedFocus: 'Chưa có dự án nào trong workspace. Hãy khởi tạo dự án đầu tiên để bắt đầu!',
      updatedAt: DateTime.now(),
    );
  }

  /// Lấy Top 3 hành động tốt nhất hôm nay (Next Best Action) từ Backend
  static Future<List<NextBestActionModel>> getTop3Focus({dynamic workspaceId, dynamic projectId}) async {
    final pId = projectId?.toString();
    if (pId == null || pId.isEmpty) return [];
    try {
      final response = await ApiClient.get('/operations/strategy/projects/$pId/next-best-actions');
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

  /// Lấy danh sách các quyết định đang chờ Founder duyệt ('Waiting for You') từ Backend
  static Future<List<FounderDecisionModel>> listPendingDecisions({dynamic workspaceId}) async {
    try {
      final wId = workspaceId?.toString() ?? await SecureStorageService.read('workspace_id');
      if (wId == null || wId.isEmpty) return [];
      final response = await ApiClient.get('/operations/strategy/decision-records?workspaceId=$wId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final List<dynamic> list = data is List ? data : (data['decisionRecords'] as List? ?? data['records'] as List? ?? []);
        return list.map((e) => FounderDecisionModel.fromJson(e as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[CoFounderApiService] listPendingDecisions exception: $e');
    }
    return [];
  }

  /// Chốt quyết định chiến lược
  static Future<bool> resolveDecision({
    required dynamic decisionId,
    required String decisionMade,
    String? founderNotes,
  }) async {
    try {
      final response = await ApiClient.patch(
        '/operations/strategy/decision-records/${decisionId.toString()}',
        body: {
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
