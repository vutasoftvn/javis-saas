import '../../../core/network/api_client.dart';
import '../models/strategy_list_result.dart';
import 'strategy_service_base.dart';

/// Strategic Canvas & Foundation (Phase 1)
class CanvasService extends StrategyServiceBase {
  Future<StrategyListResult<Map<String, dynamic>>> getCanvases() async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    try {
      final response = await ApiClient.get('/strategy/canvases?workspace_id=$workspaceId');
      return decodeList(response, 'canvases');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> getCanvasDetail(String canvasId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.get('/strategy/canvases/$canvasId?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<Map<String, dynamic>> createCanvas(String name, {String? description}) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/canvases?workspace_id=$workspaceId',
      body: {
        'name': name,
        'description': ?description,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> updateCanvas(String canvasId, {String? name, String? description}) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/canvases/$canvasId?workspace_id=$workspaceId',
      body: {
        'name': ?name,
        'description': ?description,
      },
    );
    return decode(response);
  }

  Future<void> deleteCanvas(String canvasId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete('/strategy/canvases/$canvasId?workspace_id=$workspaceId');
    decode(response);
  }

  Future<Map<String, dynamic>> generateAiFoundation(String canvasId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post('/strategy/canvases/$canvasId/generate-ai-foundation?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<Map<String, dynamic>> createRevision(String canvasId, {String? baseRevisionId}) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/canvases/$canvasId/revisions?workspace_id=$workspaceId',
      body: {
        'base_revision_id': ?baseRevisionId,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> getRevisionDetail(String revisionId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.get('/strategy/revisions/$revisionId?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<Map<String, dynamic>> submitReview(String revisionId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post('/strategy/revisions/$revisionId/submit-review?workspace_id=$workspaceId');
    return decode(response);
  }

  Future<Map<String, dynamic>> approveRevision(String revisionId, {String? note}) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/revisions/$revisionId/approve?workspace_id=$workspaceId',
      body: {
        'note': ?note,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> requestChanges(String revisionId, String reason) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/revisions/$revisionId/request-changes?workspace_id=$workspaceId',
      body: {'reason': reason},
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> saveFoundation(
    String revisionId, {
    required String vision,
    required String mission,
    required List<Map<String, dynamic>> values,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/revisions/$revisionId/foundation?workspace_id=$workspaceId',
      body: {'vision': vision, 'mission': mission, 'values': values},
    );
    return decode(response);
  }
}
