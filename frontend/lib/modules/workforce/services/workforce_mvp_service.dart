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

  Map<String, dynamic> _asMap(Object? json) {
    if (json is Map<String, dynamic>) return json;
    throw const FormatException('Expected JSON object in workforce response');
  }

  Future<ApiResult<List<WorkforceRun>>> listRuns({int limit = 50}) async {
    return _client.request<List<WorkforceRun>>(
      MvpEndpoint.workforceRunsList,
      query: {'limit': '$limit'},
      decode: (raw) => _asList(raw).map(WorkforceRun.fromJson).toList(),
    );
  }

  Future<ApiResult<List<WorkforceRunEvent>>> listRunEvents(String runId) async {
    return _client.request<List<WorkforceRunEvent>>(
      MvpEndpoint.workforceRunEvents,
      pathParams: {'runId': runId},
      decode: (raw) => _asList(raw).map(WorkforceRunEvent.fromJson).toList(),
    );
  }

  Future<ApiResult<List<WorkforceApproval>>> listApprovals({String? status}) async {
    return _client.request<List<WorkforceApproval>>(
      MvpEndpoint.workforceApprovalsList,
      query: {'status': ?status},
      decode: (raw) => _asList(raw).map(WorkforceApproval.fromJson).toList(),
    );
  }

  Future<ApiResult<WorkforceApprovalDecision>> decideApproval(
    String approvalId, {
    required bool approved,
    String? reason,
  }) async {
    return _client.request<WorkforceApprovalDecision>(
      MvpEndpoint.workforceApprovalDecide,
      pathParams: {'approvalId': approvalId},
      body: {'approved': approved, 'reason': ?reason},
      decode: (raw) => WorkforceApprovalDecision.fromJson(_asMap(raw)),
    );
  }

  Future<ApiResult<List<WorkforceCompositionEntry>>> getComposition() async {
    return _client.request<List<WorkforceCompositionEntry>>(
      MvpEndpoint.workforceCompositionRead,
      decode: (raw) => _asList(raw).map(WorkforceCompositionEntry.fromJson).toList(),
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
      MvpEndpoint.workforceOrgChartRead,
      decode: _asMap,
    );
  }

  Future<ApiResult<List<WorkforceRosterEntry>>> listRoster() async {
    return _client.request<List<WorkforceRosterEntry>>(
      MvpEndpoint.workforceRosterList,
      decode: (raw) => _asList(raw).map(WorkforceRosterEntry.fromJson).toList(),
    );
  }

  Future<ApiResult<List<WorkforceWorkProduct>>> listWorkProducts() async {
    return _client.request<List<WorkforceWorkProduct>>(
      MvpEndpoint.workforceWorkProductsList,
      decode: (raw) => _asList(raw).map(WorkforceWorkProduct.fromJson).toList(),
    );
  }

  Future<ApiResult<WorkforceExceptionSummary>> listExceptions() async {
    return _client.request<WorkforceExceptionSummary>(
      MvpEndpoint.workforceExceptionsList,
      decode: (raw) => WorkforceExceptionSummary.fromJson(_asMap(raw)),
    );
  }

  Future<ApiResult<WorkforceStageRoster>> getStageRoster(String stageCode) async {
    return _client.request<WorkforceStageRoster>(
      MvpEndpoint.workforceStageRosterRead,
      pathParams: {'stageCode': stageCode},
      decode: (raw) => WorkforceStageRoster.fromJson(_asMap(raw)),
    );
  }

  Future<ApiResult<WorkforceDashboardSummary>> getDashboardSummary() async {
    return _client.request<WorkforceDashboardSummary>(
      MvpEndpoint.workforceDashboardSummaryRead,
      decode: (raw) => WorkforceDashboardSummary.fromJson(_asMap(raw)),
    );
  }
}
