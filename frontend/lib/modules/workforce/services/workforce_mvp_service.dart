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

  List<Map<String, dynamic>> _asList(Object? json) {
    if (json is List) {
      return json.whereType<Map<String, dynamic>>().toList();
    }
    if (json is Map<String, dynamic>) {
      return (json['items'] as List?)?.whereType<Map<String, dynamic>>().toList() ?? [];
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
}
