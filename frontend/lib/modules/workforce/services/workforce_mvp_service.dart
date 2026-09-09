// Founder Trial R1 — legacy surface removed from the MVP contract. Every
// request here now returns MvpRequestClient.unavailable(); the retained
// class shell keeps callers compiling until the module is deleted.
// ignore_for_file: unused_field, unused_import, unused_element
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
    return MvpRequestClient.unavailable<List<WorkforceRun>>('workforceRunList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<WorkforceRunEvent>>> listRunEvents(String runId) async {
    return MvpRequestClient.unavailable<List<WorkforceRunEvent>>('workforceRunEvents was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<WorkforceApproval>>> listApprovals({String? status}) async {
    return MvpRequestClient.unavailable<List<WorkforceApproval>>('workforceApprovalList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<WorkforceApprovalDecision>> decideApproval(
    String approvalId, {
    required bool approved,
    String? reason,
  }) async {
    return MvpRequestClient.unavailable<WorkforceApprovalDecision>('workforceApprovalDecision was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<WorkforceCompositionEntry>>> getComposition() async {
    return MvpRequestClient.unavailable<List<WorkforceCompositionEntry>>('workforceCompositionGet was removed from the Founder Trial R1 contract');
  }

  // Task 7 — org-chart chưa có typed model riêng (backend trả cây phân cấp
  // tự do, không phải danh sách record cố định như run/approval/composition);
  // giữ nguyên `Map<String, dynamic>` thay vì suy diễn schema chưa được xác
  // nhận, nhưng vẫn đi qua `MvpRequestClient` để có envelope-unwrap +
  // ApiFailure thật giống mọi endpoint workforce khác — không tự ghép URL
  // `/workforce/org-chart` (thiếu prefix `/agent`, luôn 404 lên sai host).
  Future<ApiResult<Map<String, dynamic>>> getOrgChart() async {
    return MvpRequestClient.unavailable<Map<String, dynamic>>('workforceOrgChartGet was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<WorkforceRosterEntry>>> listRoster() async {
    return MvpRequestClient.unavailable<List<WorkforceRosterEntry>>('workforceRosterList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<WorkforceWorkProduct>>> listWorkProducts() async {
    return MvpRequestClient.unavailable<List<WorkforceWorkProduct>>('workforceWorkProductList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<WorkforceExceptionSummary>> listExceptions() async {
    return MvpRequestClient.unavailable<WorkforceExceptionSummary>('workforceExceptionList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<WorkforceStageRoster>> getStageRoster(String stageCode) async {
    return MvpRequestClient.unavailable<WorkforceStageRoster>('workforceStageRosterGet was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<WorkforceDashboardSummary>> getDashboardSummary() async {
    return MvpRequestClient.unavailable<WorkforceDashboardSummary>('workforceDashboardSummaryGet was removed from the Founder Trial R1 contract');
  }
}
