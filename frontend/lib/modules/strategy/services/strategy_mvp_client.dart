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
    return _client.request<List<MvpCanvas>>(
      MvpEndpoint.strategyCanvasList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MvpCanvas.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<MvpCanvas>> createCanvas({
    required String name,
    String? description,
  }) async {
    return _client.request<MvpCanvas>(
      MvpEndpoint.strategyCanvasCreate,
      body: {
        'name': name,
        'description': ?description,
      },
      decode: (json) => MvpCanvas.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<MvpCanvas>> getCanvas(String id) async {
    return _client.request<MvpCanvas>(
      MvpEndpoint.strategyCanvasGet,
      pathParams: {'id': id},
      decode: (json) => MvpCanvas.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<MvpCanvas>> updateCanvas({
    required String id,
    String? name,
    String? description,
  }) async {
    return _client.request<MvpCanvas>(
      MvpEndpoint.strategyCanvasUpdate,
      pathParams: {'id': id},
      body: {
        'name': ?name,
        'description': ?description,
      },
      decode: (json) => MvpCanvas.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<void>> deleteCanvas(String id) async {
    return _client.request<void>(
      MvpEndpoint.strategyCanvasDelete,
      pathParams: {'id': id},
      decode: (_) {},
    );
  }

  // ─── Revision Methods ───

  Future<ApiResult<MvpCanvasRevision>> createRevision({
    required String canvasId,
    required Map<String, dynamic> content,
    required String origin,
    List<Map<String, dynamic>>? sourceRefs,
    String? parentRevisionId,
  }) async {
    return _client.request<MvpCanvasRevision>(
      MvpEndpoint.strategyCanvasRevisionCreate,
      pathParams: {'id': canvasId},
      body: {
        'content': content,
        'origin': origin,
        'sourceRefs': ?sourceRefs,
        'parentRevisionId': ?parentRevisionId,
      },
      decode: (json) => MvpCanvasRevision.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<MvpCanvasRevision>> getRevision(String id) async {
    return _client.request<MvpCanvasRevision>(
      MvpEndpoint.strategyCanvasRevisionGet,
      pathParams: {'id': id},
      decode: (json) => MvpCanvasRevision.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<MvpCanvasRevision>> submitRevisionForReview(String id) async {
    return _client.request<MvpCanvasRevision>(
      MvpEndpoint.strategyCanvasRevisionSubmitReview,
      pathParams: {'id': id},
      decode: (json) => MvpCanvasRevision.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<MvpCanvasRevision>> approveRevision(String id, {String? reviewNote}) async {
    return _client.request<MvpCanvasRevision>(
      MvpEndpoint.strategyCanvasRevisionApprove,
      pathParams: {'id': id},
      body: {
        'reviewNote': ?reviewNote,
      },
      decode: (json) => MvpCanvasRevision.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<MvpCanvasRevision>> rejectRevision(String id, {String? reviewNote}) async {
    return _client.request<MvpCanvasRevision>(
      MvpEndpoint.strategyCanvasRevisionReject,
      pathParams: {'id': id},
      body: {
        'reviewNote': ?reviewNote,
      },
      decode: (json) => MvpCanvasRevision.fromJson(json as Map<String, dynamic>),
    );
  }

  // ─── OKR Methods ───

  Future<ApiResult<List<MvpOkrCycle>>> listOkrCycles() async {
    return _client.request<List<MvpOkrCycle>>(
      MvpEndpoint.strategyOkrCycleList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MvpOkrCycle.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<List<MvpObjective>>> listObjectives() async {
    return _client.request<List<MvpObjective>>(
      MvpEndpoint.strategyObjectiveList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MvpObjective.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<void>> deleteObjective(String id) async {
    return _client.request<void>(
      MvpEndpoint.strategyObjectiveDelete,
      pathParams: {'id': id},
      decode: (_) {},
    );
  }

  Future<ApiResult<MvpObjectiveProgress>> getObjectiveProgress(String id) async {
    return _client.request<MvpObjectiveProgress>(
      MvpEndpoint.strategyObjectiveProgress,
      pathParams: {'id': id},
      decode: (json) => MvpObjectiveProgress.fromJson(json as Map<String, dynamic>),
    );
  }

  // ─── 12-Week Year Methods ───

  Future<ApiResult<List<MvpTwelveWeekCycle>>> listTwelveWeekCycles() async {
    return _client.request<List<MvpTwelveWeekCycle>>(
      MvpEndpoint.strategyTwelveWeekCycleList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MvpTwelveWeekCycle.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<List<MvpWeeklyPlan>>> listTwelveWeekPlans() async {
    return _client.request<List<MvpWeeklyPlan>>(
      MvpEndpoint.strategyTwelveWeekPlanList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MvpWeeklyPlan.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<List<MvpWeeklyCommitment>>> listTwelveWeekCommitments() async {
    return _client.request<List<MvpWeeklyCommitment>>(
      MvpEndpoint.strategyTwelveWeekCommitmentList,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MvpWeeklyCommitment.fromJson(e))
            .toList();
      },
    );
  }
}
