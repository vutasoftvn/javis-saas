import 'dart:convert';
import '../../core/network/api_client.dart';
import 'workspace_service.dart';

class CompanyRuntimeService extends WorkspaceService {
  Future<List<dynamic>> getNeedsYou({bool includeSnoozed = false}) async {
    final res = await getJson('/company-runtime/needs-you?include_snoozed=$includeSnoozed');
    if (res is Map && res['items'] is List) {
      return res['items'] as List<dynamic>;
    }
    return [];
  }

  Future<bool> resolveNeedsYou(String itemId) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return false;
    final response = await ApiClient.post(
      '/company-runtime/needs-you/$itemId/resolve?workspace_id=${Uri.encodeQueryComponent(id)}',
    );
    return response.statusCode >= 200 && response.statusCode < 300;
  }

  Future<bool> snoozeNeedsYou(String itemId, DateTime until) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return false;
    final response = await ApiClient.post(
      '/company-runtime/needs-you/$itemId/snooze?workspace_id=${Uri.encodeQueryComponent(id)}',
      body: {'until': until.toUtc().toIso8601String()},
    );
    return response.statusCode >= 200 && response.statusCode < 300;
  }

  Future<List<dynamic>> getBlockers({String? status}) async {
    final statusQuery = status != null ? '&status=${Uri.encodeQueryComponent(status)}' : '';
    final res = await getJson('/company-runtime/blockers$statusQuery');
    if (res is Map && res['blockers'] is List) {
      return res['blockers'] as List<dynamic>;
    }
    return [];
  }

  Future<bool> resolveBlocker(String blockerId, {String? resolutionArtifactId}) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return false;
    final body = resolutionArtifactId != null ? {'resolution_artifact_id': int.tryParse(resolutionArtifactId)} : null;
    final response = await ApiClient.post(
      '/company-runtime/blockers/$blockerId/resolve?workspace_id=${Uri.encodeQueryComponent(id)}',
      body: body,
    );
    return response.statusCode >= 200 && response.statusCode < 300;
  }

  Future<Map<String, dynamic>?> getWorkInspector(String taskId) async {
    final res = await getJson('/company-runtime/tasks/$taskId/inspector');
    if (res is Map<String, dynamic>) {
      return res;
    }
    return null;
  }

  Future<Map<String, dynamic>?> getRuntimeStatus() async {
    final res = await getJson('/company-runtime/runtime/status');
    if (res is Map<String, dynamic>) {
      return res;
    }
    return null;
  }

  Future<Map<String, dynamic>?> getRuntimeDag() async {
    final res = await getJson('/company-runtime/runtime/dag');
    if (res is Map<String, dynamic>) {
      return res;
    }
    return null;
  }

  Future<Map<String, dynamic>?> decomposeMission(String weeklyCommitmentId) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return null;
    final response = await ApiClient.post(
      '/company-runtime/runtime/decompose?workspace_id=${Uri.encodeQueryComponent(id)}',
      body: {'weekly_commitment_id': int.tryParse(weeklyCommitmentId) ?? 0},
    );
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<Map<String, dynamic>?> createReview(
    String outcomeId, {
    required String reviewerType,
    required String result,
    String? feedback,
  }) async {
    final id = await workspaceId();
    if (id == null || id.isEmpty) return null;
    final response = await ApiClient.post(
      '/company-runtime/outcomes/$outcomeId/review?workspace_id=${Uri.encodeQueryComponent(id)}',
      body: {
        'reviewer_type': reviewerType,
        'result': result,
        'feedback': feedback,
      },
    );
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }
}
