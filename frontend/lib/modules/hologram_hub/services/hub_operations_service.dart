import "dart:convert";
import "package:frontend/core/network/api_client.dart";
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';

import '../models/hub_operations_models.dart';

/// B6 (Task 7) — kết quả duyệt thẻ kế hoạch tự động hoá (`POST /cosa/workspaces/:workspaceId/
/// automation-plans/:proposalId/approve`, xem task-6-report.md mục ROUTE APPROVE). Route trả
/// thẳng `ScheduleDefinitionResponse` (TS Encore, camelCase, KHÔNG bọc `{data, meta}` như các
/// route MVP khác) — chỉ giữ lại các field UI cần, không parse toàn bộ shape.
class AutomationPlanApprovalResult {
  const AutomationPlanApprovalResult({required this.scheduleId});

  final String scheduleId;

  factory AutomationPlanApprovalResult.fromJson(Map<String, dynamic> json) =>
      AutomationPlanApprovalResult(scheduleId: json['id']?.toString() ?? '');
}

List<Map<String, dynamic>> _items(Object? raw) {
  if (raw is Map<String, dynamic>) {
    final items = raw['items'];
    if (items is List) return items.whereType<Map<String, dynamic>>().toList();
  }
  throw const FormatException('Expected an object with an items array');
}

/// Gọi API cho card vận hành ở hub (Lịch, quyền agent). Task dùng
/// `ProjectOperatingLoopService`, agent dùng `ProjectStartupTeamService`, connector dùng
/// `SettingsMvpService` — không nhân bản các service đó ở đây.
class HubOperationsService {
  HubOperationsService({MvpRequestClient? client}) : _client = client ?? MvpRequestClient();

  final MvpRequestClient _client;

  /// Lịch của organization; lọc theo Project ở phía gọi (server chưa lọc theo Project).
  Future<ApiResult<List<HubSchedule>>> listSchedules() {
    return _client.request<List<HubSchedule>>(
      MvpEndpoint.hubSchedulesList,
      decode: (raw) => _items(raw).map(HubSchedule.fromJson).toList(),
    );
  }

  Future<ApiResult<void>> runScheduleNow(String scheduleId) {
    return _client.request<void>(
      MvpEndpoint.hubScheduleRunNow,
      pathParams: {'scheduleId': scheduleId},
      decode: (_) {},
    );
  }

  /// `state`: `enabled` | `paused` | `archived` (lưu trữ là trạng thái cuối).
  Future<ApiResult<HubSchedule>> setScheduleState(String scheduleId, String state) {
    return _client.request<HubSchedule>(
      MvpEndpoint.hubScheduleSetState,
      pathParams: {'scheduleId': scheduleId},
      body: {'state': state},
      decode: (raw) => HubSchedule.fromJson(raw as Map<String, dynamic>),
    );
  }

  Future<ApiResult<List<HubScheduleExecution>>> listScheduleExecutions(
    String scheduleId, {
    int limit = 5,
  }) {
    return _client.request<List<HubScheduleExecution>>(
      MvpEndpoint.hubScheduleExecutions,
      pathParams: {'scheduleId': scheduleId},
      query: {'limit': '$limit'},
      decode: (raw) => _items(raw).map(HubScheduleExecution.fromJson).toList(),
    );
  }

  Future<ApiResult<HubSchedule>> createSchedule({
    required String projectId,
    required String promptTemplate,
    String scheduleKind = "daily",
    int? hour,
    int? minute,
    List<int> weekdays = const [],
    String agentProfile = "operations",
  }) async {
    try {
      final res = await ApiClient.post(
        "/agent/schedules",
        body: {
          "schedule_kind": scheduleKind,
          "timezone": "Asia/Ho_Chi_Minh",
          "hour": hour,
          "minute": minute,
          "weekdays": weekdays,
          "prompt_template": promptTemplate,
          "agent_profile": agentProfile,
          "project_id": projectId,
        },
      );
      if (res.statusCode == 200 || res.statusCode == 201) {
        final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
        return ApiSuccess(
          data: HubSchedule.fromJson(data),
          meta: ApiResponseMeta(
            dataState: ApiDataState.populated,
            observedAt: DateTime.now().toUtc(),
          ),
        );
      }
      return ApiFailure(ApiFailureDetail(
        code: ApiFailureCode.unknown,
        statusCode: res.statusCode,
        message: "Failed to create schedule (${res.statusCode})",
      ));
    } catch (e) {
      return ApiFailure(ApiFailureDetail(
        code: ApiFailureCode.unknown,
        message: e.toString(),
      ));
    }
  }

  /// Task 6 (B5) / Task 7 (B6) — founder bấm Duyệt thẻ kế hoạch tự động hoá trong chat.
  /// `ApiClient.post` tự gắn `Authorization`/`X-Workspace-Id` từ phiên đăng nhập founder đang
  /// lưu (KHÔNG phải delegation agent — đúng yêu cầu route, xem task-6-report.md mục ROUTE
  /// APPROVE). `workspaceId` phải nằm TRONG path (route Encore), khác các route MVP khác chỉ
  /// cần header.
  Future<ApiResult<AutomationPlanApprovalResult>> approveAutomationPlan({
    required String proposalId,
    required String projectId,
  }) async {
    final workspaceId = await SecureStorageService.read('workspace_id');
    if (workspaceId == null || workspaceId.isEmpty) {
      return ApiFailure(ApiFailureDetail(
        code: ApiFailureCode.invalidRequest,
        message: 'Chưa xác định được workspace hiện tại.',
      ));
    }
    try {
      final res = await ApiClient.post(
        '/cosa/workspaces/$workspaceId/automation-plans/$proposalId/approve',
        body: {'projectId': projectId},
      );
      final decoded = res.bodyBytes.isEmpty ? null : jsonDecode(utf8.decode(res.bodyBytes));
      if (res.statusCode == 200 || res.statusCode == 201) {
        return ApiSuccess(
          data: AutomationPlanApprovalResult.fromJson(
            decoded is Map<String, dynamic> ? decoded : const {},
          ),
          meta: ApiResponseMeta(
            dataState: ApiDataState.populated,
            observedAt: DateTime.now().toUtc(),
          ),
        );
      }
      final backendCode = decoded is Map<String, dynamic> ? decoded['code']?.toString() : null;
      final backendMessage =
          decoded is Map<String, dynamic> ? decoded['message']?.toString() : null;
      return ApiFailure(ApiFailureDetail(
        code: _mapApprovalFailureCode(backendCode),
        statusCode: res.statusCode,
        message: backendMessage ?? 'Failed to approve automation plan (${res.statusCode})',
        raw: decoded,
      ));
    } catch (e) {
      return ApiFailure(ApiFailureDetail(
        code: ApiFailureCode.unknown,
        message: e.toString(),
      ));
    }
  }

  ApiFailureCode _mapApprovalFailureCode(String? backendCode) {
    switch (backendCode) {
      case 'unauthenticated':
        return ApiFailureCode.unauthenticated;
      case 'permission_denied':
        return ApiFailureCode.forbidden;
      case 'not_found':
        return ApiFailureCode.notFound;
      case 'already_exists':
      case 'failed_precondition':
        return ApiFailureCode.conflict;
      case 'invalid_argument':
        return ApiFailureCode.invalidRequest;
      case 'unavailable':
        return ApiFailureCode.unavailable;
      default:
        return ApiFailureCode.unknown;
    }
  }

  Future<ApiResult<List<HubAgentGrant>>> listAgentGrants(String projectId) {
    return _client.request<List<HubAgentGrant>>(
      MvpEndpoint.projectAgentCapabilityGrantsRead,
      pathParams: {'projectId': projectId},
      decode: (raw) => _items(raw).map(HubAgentGrant.fromJson).toList(),
    );
  }
}
