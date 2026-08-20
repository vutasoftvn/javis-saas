import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/network/api_client.dart';

class SkillRegistryApiException implements Exception {
  final int statusCode;
  final String message;
  SkillRegistryApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

class SkillRegistryService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<String> _requireWorkspaceId() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) {
      throw SkillRegistryApiException(0, 'Chưa xác định workspace hiện tại');
    }
    return workspaceId;
  }

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
    throw SkillRegistryApiException(response.statusCode, detail);
  }

  Future<List<Map<String, dynamic>>> syncBuiltInSkills() async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post('/skills/sync-built-in?workspace_id=$wsId');
    final data = _decode(res);
    if (data is List) {
      return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return [];
  }

  Future<List<Map<String, dynamic>>> listSkills({String? domain, String? status}) async {
    final wsId = await _requireWorkspaceId();
    var path = '/skills?workspace_id=$wsId';
    if (domain != null && domain.isNotEmpty) path += '&domain=${Uri.encodeComponent(domain)}';
    if (status != null && status.isNotEmpty) path += '&status=${Uri.encodeComponent(status)}';

    final res = await ApiClient.get(path);
    final data = _decode(res);
    if (data is List) {
      return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return [];
  }

  Future<Map<String, dynamic>> getSkill(String skillId) async {
    final res = await ApiClient.get('/skills/$skillId');
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> updateSkill({
    required String skillId,
    String? name,
    String? description,
    String? instructions,
    List<String>? toolPermissions,
    String? domain,
    String? version,
  }) async {
    final res = await ApiClient.put(
      '/skills/$skillId',
      body: {
        'name': ?name,
        'description': ?description,
        'instructions': ?instructions,
        'tool_permissions': ?toolPermissions,
        'domain': ?domain,
        'version': ?version,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }


  Future<Map<String, dynamic>> createCandidate({
    required String name,
    required String domain,
    required String instructions,
    String description = '',
    List<String> scope = const [],
    List<String> toolPermissions = const [],
    List<String> requiredContext = const [],
    String? createdByAgent,
  }) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post(
      '/skills/candidates',
      body: {
        'workspace_id': int.tryParse(wsId) ?? 1,
        'name': name,
        'domain': domain,
        'instructions': instructions,
        'description': description,
        'scope': scope,
        'tool_permissions': toolPermissions,
        'required_context': requiredContext,
        'created_by_agent': ?createdByAgent,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> evaluateSkill({
    required String skillId,
    required double evalScore,
    Map<String, dynamic>? evalDetails,
  }) async {
    final res = await ApiClient.post(
      '/skills/$skillId/evaluate',
      body: {
        'eval_score': evalScore,
        'eval_details': evalDetails ?? {},
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> promoteSkill(String skillId) async {
    final res = await ApiClient.post('/skills/$skillId/promote');
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> deprecateSkill(String skillId, {String? reason}) async {
    final res = await ApiClient.post(
      '/skills/$skillId/deprecate',
      body: {
        'reason': ?reason,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> recordFeedback({
    required String skillId,
    required bool success,
    int? rating,
  }) async {
    final res = await ApiClient.post(
      '/skills/$skillId/feedback',
      body: {
        'success': success,
        'rating': ?rating,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  // --- Phase C: Skill Versions & Restore Default ---

  Future<List<Map<String, dynamic>>> getSkillVersions(String key) async {
    final res = await ApiClient.get('/agent-platform/skills/$key/versions');
    if (res.statusCode == 200) {
      final List<dynamic> data = jsonDecode(res.body);
      return data.map((e) => e as Map<String, dynamic>).toList();
    }
    return [];
  }

  Future<Map<String, dynamic>?> restoreDefaultSkill(String key) async {
    final res = await ApiClient.post('/agent-platform/skills/$key/restore-default');
    if (res.statusCode == 200) {
      return jsonDecode(res.body) as Map<String, dynamic>;
    }
    return null;
  }
}

