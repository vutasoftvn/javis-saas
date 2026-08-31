import '../../../core/network/api_result.dart';
import 'strategy_mvp_client.dart';
import '../models/mvp_strategy_models.dart';

class CanvasService {
  final StrategyMvpClient _client;

  CanvasService({StrategyMvpClient? client}) : _client = client ?? StrategyMvpClient();

  Future<ApiResult<List<MvpCanvas>>> getCanvases() async {
    return _client.listCanvases();
  }

  Future<ApiResult<MvpCanvas>> getCanvasDetail(String canvasId) async {
    return _client.getCanvas(canvasId);
  }

  Future<ApiResult<MvpCanvas>> createCanvas(String name, {String? description}) async {
    return _client.createCanvas(name: name, description: description);
  }

  Future<ApiResult<MvpCanvas>> updateCanvas(String canvasId, {String? name, String? description}) async {
    return _client.updateCanvas(id: canvasId, name: name, description: description);
  }

  Future<ApiResult<void>> deleteCanvas(String canvasId) async {
    return _client.deleteCanvas(canvasId);
  }

  Future<ApiResult<MvpCanvasRevision>> createRevision({
    required String canvasId,
    required Map<String, dynamic> content,
    required String origin,
    List<Map<String, dynamic>>? sourceRefs,
    String? parentRevisionId,
  }) async {
    return _client.createRevision(
      canvasId: canvasId,
      content: content,
      origin: origin,
      sourceRefs: sourceRefs,
      parentRevisionId: parentRevisionId,
    );
  }

  Future<ApiResult<MvpCanvasRevision>> getRevision(String revisionId) async {
    return _client.getRevision(revisionId);
  }

  Future<ApiResult<MvpCanvasRevision>> submitRevisionForReview(String revisionId) async {
    return _client.submitRevisionForReview(revisionId);
  }

  Future<ApiResult<MvpCanvasRevision>> approveRevision(String revisionId, {String? reviewNote}) async {
    return _client.approveRevision(revisionId, reviewNote: reviewNote);
  }

  Future<ApiResult<MvpCanvasRevision>> rejectRevision(String revisionId, {String? reviewNote}) async {
    return _client.rejectRevision(revisionId, reviewNote: reviewNote);
  }
}
