// Founder Trial R1 — legacy surface removed from the MVP contract. Every
// request here now returns MvpRequestClient.unavailable(); the retained
// class shell keeps callers compiling until the module is deleted.
// ignore_for_file: unused_field, unused_import, unused_element
import 'package:http/http.dart' as http;
import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/mvp_strategy_models.dart';

class StrategyMvpClient {
  final MvpRequestClient _client;

  StrategyMvpClient({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  // ─── Canvas Methods ───

  Future<ApiResult<List<MvpCanvas>>> listCanvases() async {
    return MvpRequestClient.unavailable<List<MvpCanvas>>('strategyCanvasList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<MvpCanvas>> createCanvas({
    required String name,
    String? description,
  }) async {
    return MvpRequestClient.unavailable<MvpCanvas>('strategyCanvasCreate was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<MvpCanvas>> getCanvas(String id) async {
    return MvpRequestClient.unavailable<MvpCanvas>('strategyCanvasGet was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<MvpCanvas>> updateCanvas({
    required String id,
    String? name,
    String? description,
  }) async {
    return MvpRequestClient.unavailable<MvpCanvas>('strategyCanvasUpdate was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<void>> deleteCanvas(String id) async {
    return MvpRequestClient.unavailable<void>('strategyCanvasDelete was removed from the Founder Trial R1 contract');
  }

  // ─── Revision Methods ───

  Future<ApiResult<MvpCanvasRevision>> createRevision({
    required String canvasId,
    required Map<String, dynamic> content,
    required String origin,
    List<Map<String, dynamic>>? sourceRefs,
    String? parentRevisionId,
  }) async {
    return MvpRequestClient.unavailable<MvpCanvasRevision>('strategyCanvasRevisionCreate was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<MvpCanvasRevision>> getRevision(String id) async {
    return MvpRequestClient.unavailable<MvpCanvasRevision>('strategyCanvasRevisionGet was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<MvpCanvasRevision>> submitRevisionForReview(String id) async {
    return MvpRequestClient.unavailable<MvpCanvasRevision>('strategyCanvasRevisionSubmitReview was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<MvpCanvasRevision>> approveRevision(String id, {String? reviewNote}) async {
    return MvpRequestClient.unavailable<MvpCanvasRevision>('strategyCanvasRevisionApprove was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<MvpCanvasRevision>> rejectRevision(String id, {String? reviewNote}) async {
    return MvpRequestClient.unavailable<MvpCanvasRevision>('strategyCanvasRevisionReject was removed from the Founder Trial R1 contract');
  }

  // ─── OKR Methods ───

  Future<ApiResult<List<MvpOkrCycle>>> listOkrCycles() async {
    return MvpRequestClient.unavailable<List<MvpOkrCycle>>('strategyOkrCycleList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<MvpObjective>>> listObjectives() async {
    return MvpRequestClient.unavailable<List<MvpObjective>>('strategyObjectiveList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<void>> deleteObjective(String id) async {
    return MvpRequestClient.unavailable<void>('strategyObjectiveDelete was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<MvpObjectiveProgress>> getObjectiveProgress(String id) async {
    return MvpRequestClient.unavailable<MvpObjectiveProgress>('strategyObjectiveProgress was removed from the Founder Trial R1 contract');
  }

  // ─── 12-Week Year Methods ───

  Future<ApiResult<List<MvpTwelveWeekCycle>>> listTwelveWeekCycles() async {
    return MvpRequestClient.unavailable<List<MvpTwelveWeekCycle>>('strategyTwelveWeekCycleList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<MvpWeeklyPlan>>> listTwelveWeekPlans() async {
    return MvpRequestClient.unavailable<List<MvpWeeklyPlan>>('strategyTwelveWeekPlanList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<MvpWeeklyCommitment>>> listTwelveWeekCommitments() async {
    return MvpRequestClient.unavailable<List<MvpWeeklyCommitment>>('strategyTwelveWeekCommitmentList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<MvpWeeklyPlan>> updateWeeklyPlan({
    required String id,
    double? executionScore,
    double? outcomeScore,
    String? reflection,
  }) async {
    return MvpRequestClient.unavailable<MvpWeeklyPlan>('strategyTwelveWeekPlanUpdate was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<MvpExecutionCycleView>> getExecutionCycleView({
    required String projectId,
    String? cycleId,
  }) async {
    final queryMap = <String, String>{'projectId': projectId};
    if (cycleId != null && cycleId.isNotEmpty) {
      queryMap['cycleId'] = cycleId;
    }
    return MvpRequestClient.unavailable<MvpExecutionCycleView>('strategyExecutionCycleView was removed from the Founder Trial R1 contract');
  }
}
