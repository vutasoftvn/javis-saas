import 'package:http/http.dart' as http;

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/workforce_mvp_models.dart';

/// Task 3 — service canonical duy nhất cho Mission Control / Workforce UI,
/// xây trên `MvpRequestClient` (không tự ghép URL / bypass transport chung).
/// Mọi lỗi (404, 5xx, timeout, offline...) được `MvpRequestClient` ánh xạ
/// thành `ApiFailure` và trả nguyên vẹn cho caller — không bao giờ được
/// nuốt lỗi rồi trả về `[]`/`null`/`false` giả tạo ở lớp này.
class WorkforceMvpService {
  final MvpRequestClient _client;

  WorkforceMvpService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  // Fix-review (2026-09-01) — `mvp_list` (apps/cosa/api/mvp_response.py) luôn
  // đặt list trực tiếp dưới `data`, không bao giờ bọc thêm một object
  // `{items: [...]}`; bỏ nhánh Map-fallback không thể chạy tới được.
  List<Map<String, dynamic>> _asList(Object? json) {
    if (json is List) {
      return json.whereType<Map<String, dynamic>>().toList();
    }
    return const [];
  }

  Future<ApiResult<List<WorkforceRun>>> listRuns({int limit = 50}) async {
    return _client.request<List<WorkforceRun>>(
      MvpEndpoint.workforceRunList,
      query: {'limit': limit.toString()},
      decode: (json) => _asList(json).map(WorkforceRun.fromJson).toList(),
    );
  }

  Future<ApiResult<List<WorkforceRunEvent>>> listRunEvents(String runId) async {
    return _client.request<List<WorkforceRunEvent>>(
      MvpEndpoint.workforceRunEvents,
      pathParams: {'runId': runId},
      decode: (json) => _asList(json).map(WorkforceRunEvent.fromJson).toList(),
    );
  }

  Future<ApiResult<List<WorkforceApproval>>> listApprovals({String? status}) async {
    return _client.request<List<WorkforceApproval>>(
      MvpEndpoint.workforceApprovalList,
      query: status != null ? {'status': status} : null,
      decode: (json) => _asList(json).map(WorkforceApproval.fromJson).toList(),
    );
  }

  Future<ApiResult<WorkforceApprovalDecision>> decideApproval(
    String approvalId, {
    required bool approved,
    String? reason,
  }) async {
    return _client.request<WorkforceApprovalDecision>(
      MvpEndpoint.workforceApprovalDecision,
      pathParams: {'approvalId': approvalId},
      body: {
        'approved': approved,
        'reason': ?reason,
      },
      decode: (json) => WorkforceApprovalDecision.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<List<WorkforceCompositionEntry>>> getComposition() async {
    return _client.request<List<WorkforceCompositionEntry>>(
      MvpEndpoint.workforceCompositionGet,
      decode: (json) => _asList(json).map(WorkforceCompositionEntry.fromJson).toList(),
    );
  }

  // Task 7 — org-chart chưa có typed model riêng (backend trả cây phân cấp
  // tự do, không phải danh sách record cố định như run/approval/composition);
  // giữ nguyên `Map<String, dynamic>` thay vì suy diễn schema chưa được xác
  // nhận, nhưng vẫn đi qua `MvpRequestClient` để có envelope-unwrap +
  // ApiFailure thật giống mọi endpoint workforce khác — không tự ghép URL
  // `/workforce/org-chart` (thiếu prefix `/agent`, luôn 404 lên sai host).
  Future<ApiResult<Map<String, dynamic>>> getOrgChart() async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.workforceOrgChartGet,
      decode: (json) => (json as Map?)?.cast<String, dynamic>() ?? const {},
    );
  }

  Future<ApiResult<List<WorkforceRosterEntry>>> listRoster() async {
    return _client.request<List<WorkforceRosterEntry>>(
      MvpEndpoint.workforceRosterList,
      decode: (json) => _asList(json).map(WorkforceRosterEntry.fromJson).toList(),
    );
  }

  Future<ApiResult<List<WorkforceWorkProduct>>> listWorkProducts() async {
    return _client.request<List<WorkforceWorkProduct>>(
      MvpEndpoint.workforceWorkProductList,
      decode: (json) => _asList(json).map(WorkforceWorkProduct.fromJson).toList(),
    );
  }

  Future<ApiResult<WorkforceExceptionSummary>> listExceptions() async {
    return _client.request<WorkforceExceptionSummary>(
      MvpEndpoint.workforceExceptionList,
      decode: (json) => WorkforceExceptionSummary.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<WorkforceStageRoster>> getStageRoster(String stageCode) async {
    return _client.request<WorkforceStageRoster>(
      MvpEndpoint.workforceStageRosterGet,
      pathParams: {'stageCode': stageCode},
      decode: (json) => WorkforceStageRoster.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<WorkforceDashboardSummary>> getDashboardSummary() async {
    return _client.request<WorkforceDashboardSummary>(
      MvpEndpoint.workforceDashboardSummaryGet,
      decode: (json) => WorkforceDashboardSummary.fromJson(json as Map<String, dynamic>),
    );
  }
}
