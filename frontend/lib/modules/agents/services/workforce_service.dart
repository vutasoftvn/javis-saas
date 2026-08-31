import 'package:http/http.dart' as http;

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/workforce_models.dart';

class WorkforceService {
  final MvpRequestClient _client;

  WorkforceService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  // ─── Assignments ───

  Future<ApiResult<List<WorkforceAssignment>>> listAssignments({String? status}) async {
    return _client.request<List<WorkforceAssignment>>(
      MvpEndpoint.workforceAssignmentList,
      query: status != null ? {'status': status} : null,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => WorkforceAssignment.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<WorkforceAssignment>> createAssignment({
    required String functionalKey,
    String? reportsToAssignmentId,
  }) async {
    final body = <String, dynamic>{
      'functional_key': functionalKey,
    };
    if (reportsToAssignmentId != null) {
      body['reports_to_assignment_id'] = reportsToAssignmentId;
    }

    return _client.request<WorkforceAssignment>(
      MvpEndpoint.workforceAssignmentCreate,
      body: body,
      decode: (json) => WorkforceAssignment.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<WorkforceAssignment>> retireAssignment(String id) async {
    return _client.request<WorkforceAssignment>(
      MvpEndpoint.workforceAssignmentRetire,
      pathParams: {'id': id},
      decode: (json) => WorkforceAssignment.fromJson(json as Map<String, dynamic>),
    );
  }

  // ─── Composition & Org Chart ───

  Future<ApiResult<List<WorkforceCompositionEntry>>> getComposition() async {
    return _client.request<List<WorkforceCompositionEntry>>(
      MvpEndpoint.workforceCompositionGet,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => WorkforceCompositionEntry.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<WorkforceOrgChart>> getOrgChart() async {
    return _client.request<WorkforceOrgChart>(
      MvpEndpoint.workforceOrgChartGet,
      decode: (json) => WorkforceOrgChart.fromJson(json as Map<String, dynamic>),
    );
  }

  // ─── Capabilities & Health & Cost ───

  Future<ApiResult<List<WorkforceCapability>>> listCapabilities() async {
    return _client.request<List<WorkforceCapability>>(
      MvpEndpoint.workforceCapabilityList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => WorkforceCapability.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<List<WorkforceCostObservation>>> listCostObservations({
    String? runId,
    int limit = 100,
  }) async {
    final queryParams = <String, String>{
      'limit': limit.toString(),
    };
    if (runId != null) {
      queryParams['run_id'] = runId;
    }

    return _client.request<List<WorkforceCostObservation>>(
      MvpEndpoint.workforceCostObservationList,
      query: queryParams,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => WorkforceCostObservation.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<List<WorkforceHealth>>> getHealth() async {
    return _client.request<List<WorkforceHealth>>(
      MvpEndpoint.workforceHealthGet,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => WorkforceHealth.fromJson(e))
            .toList();
      },
    );
  }

  // ─── Runs ───

  Future<ApiResult<List<WorkforceRunSummary>>> listRuns({int limit = 50}) async {
    return _client.request<List<WorkforceRunSummary>>(
      MvpEndpoint.workforceRunList,
      query: {'limit': limit.toString()},
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => WorkforceRunSummary.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<WorkforceRunDetail>> getRun(String runId) async {
    return _client.request<WorkforceRunDetail>(
      MvpEndpoint.workforceRunGet,
      pathParams: {'runId': runId},
      decode: (json) => WorkforceRunDetail.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<List<WorkforceRunEvent>>> getRunEvents(String runId) async {
    return _client.request<List<WorkforceRunEvent>>(
      MvpEndpoint.workforceRunEvents,
      pathParams: {'runId': runId},
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => WorkforceRunEvent.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<List<WorkforceRunArtifact>>> getRunArtifacts(String runId) async {
    return _client.request<List<WorkforceRunArtifact>>(
      MvpEndpoint.workforceRunArtifacts,
      pathParams: {'runId': runId},
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => WorkforceRunArtifact.fromJson(e))
            .toList();
      },
    );
  }

  // ─── Schedules ───

  Future<ApiResult<List<WorkforceSchedule>>> listSchedules() async {
    return _client.request<List<WorkforceSchedule>>(
      MvpEndpoint.workforceScheduleList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => WorkforceSchedule.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<WorkforceSchedule>> createSchedule({
    required String name,
    required String functionalKey,
    required String cronExpression,
    Map<String, dynamic>? inputPayload,
  }) async {
    return _client.request<WorkforceSchedule>(
      MvpEndpoint.workforceScheduleCreate,
      body: {
        'name': name,
        'functional_key': functionalKey,
        'cron_expression': cronExpression,
        'input_payload': inputPayload ?? <String, dynamic>{},
      },
      decode: (json) => WorkforceSchedule.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<Map<String, dynamic>>> runScheduleNow(String scheduleId) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.workforceScheduleRunNow,
      pathParams: {'scheduleId': scheduleId},
      decode: (json) => json as Map<String, dynamic>,
    );
  }

  // ─── Approvals ───

  Future<ApiResult<List<WorkforceApproval>>> listApprovals({String? status}) async {
    return _client.request<List<WorkforceApproval>>(
      MvpEndpoint.workforceApprovalList,
      query: status != null ? {'status': status} : null,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => WorkforceApproval.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<WorkforceApprovalDecision>> decideApproval(
    String approvalId,
    String decision, {
    String? reason,
  }) async {
    final body = <String, dynamic>{
      'decision': decision,
    };
    if (reason != null) {
      body['reason'] = reason;
    }

    return _client.request<WorkforceApprovalDecision>(
      MvpEndpoint.workforceApprovalDecision,
      pathParams: {'approvalId': approvalId},
      body: body,
      decode: (json) => WorkforceApprovalDecision.fromJson(json as Map<String, dynamic>),
    );
  }
}
