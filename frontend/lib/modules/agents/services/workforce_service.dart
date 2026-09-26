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
      MvpEndpoint.workforceAssignmentsList,
      query: {'status': ?status},
      decode: (raw) => _asList(raw).map(WorkforceAssignment.fromJson).toList(),
    );
  }

  Future<ApiResult<WorkforceAssignment>> createAssignment({
    required String functionalKey,
    String? reportsToAssignmentId,
    String? companyWorkforceMemberId,
  }) async {
    return _client.request<WorkforceAssignment>(
      MvpEndpoint.workforceAssignmentCreate,
      body: {
        'functional_key': functionalKey,
        'reports_to_assignment_id': ?reportsToAssignmentId,
        'company_workforce_member_id': ?companyWorkforceMemberId,
      },
      decode: (raw) => WorkforceAssignment.fromJson(_asMap(raw)),
    );
  }

  Future<ApiResult<WorkforceAssignment>> retireAssignment(String id) async {
    return _client.request<WorkforceAssignment>(
      MvpEndpoint.workforceAssignmentRetire,
      pathParams: {'assignmentId': id},
      decode: (raw) => WorkforceAssignment.fromJson(_asMap(raw)),
    );
  }

  // ─── Composition & Org Chart ───

  Future<ApiResult<List<WorkforceCompositionEntry>>> getComposition() async {
    return _client.request<List<WorkforceCompositionEntry>>(
      MvpEndpoint.workforceCompositionRead,
      decode: (raw) => _asList(raw).map(WorkforceCompositionEntry.fromJson).toList(),
    );
  }

  Future<ApiResult<WorkforceOrgChart>> getOrgChart() async {
    return _client.request<WorkforceOrgChart>(
      MvpEndpoint.workforceOrgChartRead,
      decode: (raw) => WorkforceOrgChart.fromJson(_asMap(raw)),
    );
  }

  // ─── Capabilities & Health & Cost ───

  Future<ApiResult<List<WorkforceCapability>>> listCapabilities() async {
    return _client.request<List<WorkforceCapability>>(
      MvpEndpoint.workforceCapabilitiesList,
      decode: (raw) => _asList(raw).map(WorkforceCapability.fromJson).toList(),
    );
  }

  Future<ApiResult<List<WorkforceCostObservation>>> listCostObservations({
    String? runId,
    int limit = 100,
  }) async {
    return _client.request<List<WorkforceCostObservation>>(
      MvpEndpoint.workforceCostObservationsList,
      query: {'limit': '$limit', 'run_id': ?runId},
      decode: (raw) => _asList(raw).map(WorkforceCostObservation.fromJson).toList(),
    );
  }

  Future<ApiResult<List<WorkforceHealth>>> getHealth() async {
    return _client.request<List<WorkforceHealth>>(
      MvpEndpoint.workforceHealthRead,
      decode: (raw) => _asList(raw).map(WorkforceHealth.fromJson).toList(),
    );
  }

  // ─── Runs ───

  Future<ApiResult<List<WorkforceRunSummary>>> listRuns({int limit = 50}) async {
    return _client.request<List<WorkforceRunSummary>>(
      MvpEndpoint.workforceRunsList,
      query: {'limit': '$limit'},
      decode: (raw) => _asList(raw).map(WorkforceRunSummary.fromJson).toList(),
    );
  }

  Future<ApiResult<WorkforceRunDetail>> getRun(String runId) async {
    return _client.request<WorkforceRunDetail>(
      MvpEndpoint.workforceRunRead,
      pathParams: {'runId': runId},
      decode: (raw) => WorkforceRunDetail.fromJson(_asMap(raw)),
    );
  }

  Future<ApiResult<List<WorkforceRunEvent>>> getRunEvents(String runId) async {
    return _client.request<List<WorkforceRunEvent>>(
      MvpEndpoint.workforceRunEvents,
      pathParams: {'runId': runId},
      decode: (raw) => _asList(raw).map(WorkforceRunEvent.fromJson).toList(),
    );
  }

  Future<ApiResult<List<WorkforceRunArtifact>>> getRunArtifacts(String runId) async {
    return _client.request<List<WorkforceRunArtifact>>(
      MvpEndpoint.workforceRunArtifacts,
      pathParams: {'runId': runId},
      decode: (raw) => _asList(raw).map(WorkforceRunArtifact.fromJson).toList(),
    );
  }

  // ─── Schedules ───

  Future<ApiResult<List<WorkforceSchedule>>> listSchedules() async {
    return _client.request<List<WorkforceSchedule>>(
      MvpEndpoint.workforceSchedulesList,
      decode: (raw) => _asList(raw).map(WorkforceSchedule.fromJson).toList(),
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
        'input_payload': inputPayload ?? const <String, dynamic>{},
      },
      decode: (raw) => WorkforceSchedule.fromJson(_asMap(raw)),
    );
  }

  Future<ApiResult<Map<String, dynamic>>> runScheduleNow(String scheduleId) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.workforceScheduleRunNow,
      pathParams: {'scheduleId': scheduleId},
      decode: _asMap,
    );
  }

  // ─── Approvals ───

  Future<ApiResult<List<WorkforceApproval>>> listApprovals({String? status}) async {
    return _client.request<List<WorkforceApproval>>(
      MvpEndpoint.workforceApprovalsList,
      query: {'status': ?status},
      decode: (raw) => _asList(raw).map(WorkforceApproval.fromJson).toList(),
    );
  }

  Future<ApiResult<WorkforceApprovalDecision>> decideApproval(
    String approvalId,
    String decision, {
    String? reason,
  }) async {
    return _client.request<WorkforceApprovalDecision>(
      MvpEndpoint.workforceApprovalDecide,
      pathParams: {'approvalId': approvalId},
      body: {'decision': decision, 'reason': ?reason},
      decode: (raw) => WorkforceApprovalDecision.fromJson(_asMap(raw)),
    );
  }

  static List<Map<String, dynamic>> _asList(Object? json) =>
      json is List ? json.whereType<Map<String, dynamic>>().toList() : const [];

  static Map<String, dynamic> _asMap(Object? json) {
    if (json is Map<String, dynamic>) return json;
    throw const FormatException('Expected JSON object in workforce response');
  }
}
