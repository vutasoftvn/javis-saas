// Founder Trial R1 — legacy surface removed from the MVP contract. Every
// request here now returns MvpRequestClient.unavailable(); the retained
// class shell keeps callers compiling until the module is deleted.
// ignore_for_file: unused_field, unused_import, unused_element
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
    return MvpRequestClient.unavailable<List<WorkforceAssignment>>('workforceAssignmentList was removed from the Founder Trial R1 contract');
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

    return MvpRequestClient.unavailable<WorkforceAssignment>('workforceAssignmentCreate was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<WorkforceAssignment>> retireAssignment(String id) async {
    return MvpRequestClient.unavailable<WorkforceAssignment>('workforceAssignmentRetire was removed from the Founder Trial R1 contract');
  }

  // ─── Composition & Org Chart ───

  Future<ApiResult<List<WorkforceCompositionEntry>>> getComposition() async {
    return MvpRequestClient.unavailable<List<WorkforceCompositionEntry>>('workforceCompositionGet was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<WorkforceOrgChart>> getOrgChart() async {
    return MvpRequestClient.unavailable<WorkforceOrgChart>('workforceOrgChartGet was removed from the Founder Trial R1 contract');
  }

  // ─── Capabilities & Health & Cost ───

  Future<ApiResult<List<WorkforceCapability>>> listCapabilities() async {
    return MvpRequestClient.unavailable<List<WorkforceCapability>>('workforceCapabilityList was removed from the Founder Trial R1 contract');
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

    return MvpRequestClient.unavailable<List<WorkforceCostObservation>>('workforceCostObservationList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<WorkforceHealth>>> getHealth() async {
    return MvpRequestClient.unavailable<List<WorkforceHealth>>('workforceHealthGet was removed from the Founder Trial R1 contract');
  }

  // ─── Runs ───

  Future<ApiResult<List<WorkforceRunSummary>>> listRuns({int limit = 50}) async {
    return MvpRequestClient.unavailable<List<WorkforceRunSummary>>('workforceRunList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<WorkforceRunDetail>> getRun(String runId) async {
    return MvpRequestClient.unavailable<WorkforceRunDetail>('workforceRunGet was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<WorkforceRunEvent>>> getRunEvents(String runId) async {
    return MvpRequestClient.unavailable<List<WorkforceRunEvent>>('workforceRunEvents was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<WorkforceRunArtifact>>> getRunArtifacts(String runId) async {
    return MvpRequestClient.unavailable<List<WorkforceRunArtifact>>('workforceRunArtifacts was removed from the Founder Trial R1 contract');
  }

  // ─── Schedules ───

  Future<ApiResult<List<WorkforceSchedule>>> listSchedules() async {
    return MvpRequestClient.unavailable<List<WorkforceSchedule>>('workforceScheduleList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<WorkforceSchedule>> createSchedule({
    required String name,
    required String functionalKey,
    required String cronExpression,
    Map<String, dynamic>? inputPayload,
  }) async {
    return MvpRequestClient.unavailable<WorkforceSchedule>('workforceScheduleCreate was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<Map<String, dynamic>>> runScheduleNow(String scheduleId) async {
    return MvpRequestClient.unavailable<Map<String, dynamic>>('workforceScheduleRunNow was removed from the Founder Trial R1 contract');
  }

  // ─── Approvals ───

  Future<ApiResult<List<WorkforceApproval>>> listApprovals({String? status}) async {
    return MvpRequestClient.unavailable<List<WorkforceApproval>>('workforceApprovalList was removed from the Founder Trial R1 contract');
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

    return MvpRequestClient.unavailable<WorkforceApprovalDecision>('workforceApprovalDecision was removed from the Founder Trial R1 contract');
  }
}
