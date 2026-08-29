import 'dart:convert';
import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';

class CanvasApiException implements Exception {
  final int statusCode;
  final String message;
  CanvasApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

class CanvasService extends WorkspaceService {
  dynamic _decode(dynamic response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(response.body);
    }
    String detail = 'Yêu cầu thất bại (${response.statusCode})';
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['detail'] != null) {
        final d = body['detail'];
        detail = d is String ? d : jsonEncode(d);
      }
    } catch (_) {}
    throw CanvasApiException(response.statusCode, detail);
  }

  List<dynamic> _decodeList(dynamic response, String key) {
    if (response.statusCode == 404) return [];
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return [];
      try {
        final data = jsonDecode(response.body);
        return data is Map && data[key] is List ? (data[key] as List<dynamic>) : [];
      } catch (_) {
        return [];
      }
    }
    return [];
  }

  Future<String> _requireWorkspaceId() async {
    final wId = await stringWorkspaceId();
    if (wId == null || wId.isEmpty) {
      throw CanvasApiException(0, 'Chưa xác định workspace hiện tại');
    }
    return wId;
  }

  Future<List<dynamic>> getCanvases() async {
    final wId = await stringWorkspaceId();
    if (wId == null) return [];
    try {
      final response = await ApiClient.get('/strategy/canvases?workspace_id=$wId');
      return _decodeList(response, 'canvases');
    } catch (_) {
      return [];
    }
  }

  Future<Map<String, dynamic>> getCanvasDetail(String canvasId) async {
    final wId = await _requireWorkspaceId();
    final response = await ApiClient.get('/strategy/canvases/$canvasId?workspace_id=$wId');
    return _decode(response);
  }

  Future<Map<String, dynamic>> createCanvas(String name, {String? description}) async {
    final wId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/canvases?workspace_id=$wId',
      body: {
        'name': name,
        'description': ?description,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateCanvas(String canvasId, {String? name, String? description}) async {
    final wId = await _requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/canvases/$canvasId?workspace_id=$wId',
      body: {
        'name': ?name,
        'description': ?description,
      },
    );
    return _decode(response);
  }

  Future<void> deleteCanvas(String canvasId) async {
    final wId = await _requireWorkspaceId();
    final response = await ApiClient.delete('/strategy/canvases/$canvasId?workspace_id=$wId');
    _decode(response);
  }

  Future<Map<String, dynamic>> generateAiFoundation(String canvasId) async {
    final wId = await _requireWorkspaceId();
    final response = await ApiClient.post('/strategy/canvases/$canvasId/generate-ai-foundation?workspace_id=$wId');
    return _decode(response);
  }

  Future<Map<String, dynamic>> createRevision(String canvasId, {String? baseRevisionId}) async {
    final wId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/canvases/$canvasId/revisions?workspace_id=$wId',
      body: {
        'base_revision_id': ?baseRevisionId,
      },
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> getRevisionDetail(String revisionId) async {
    final wId = await _requireWorkspaceId();
    final response = await ApiClient.get('/strategy/revisions/$revisionId?workspace_id=$wId');
    return _decode(response);
  }

  Future<Map<String, dynamic>> submitReview(String revisionId) async {
    final wId = await _requireWorkspaceId();
    final response = await ApiClient.post('/strategy/revisions/$revisionId/submit-review?workspace_id=$wId');
    return _decode(response);
  }

  Future<Map<String, dynamic>> approveRevision(String revisionId, {String? note}) async {
    final wId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/revisions/$revisionId/approve?workspace_id=$wId',
      body: {'note': ?note},
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> rejectRevision(String revisionId, {String? reason}) async {
    final wId = await _requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/revisions/$revisionId/reject?workspace_id=$wId',
      body: {'reason': ?reason},
    );
    return _decode(response);
  }
}
