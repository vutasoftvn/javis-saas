import 'dart:convert';
import '../../../core/services/secure_storage_service.dart';
import '../../../core/network/api_client.dart';

class SkillRegistryApiException implements Exception {
  final int statusCode;
  final String message;
  SkillRegistryApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

class SkillAuthException extends SkillRegistryApiException {
  SkillAuthException(super.statusCode, super.message);
}

class SkillNotFoundException extends SkillRegistryApiException {
  SkillNotFoundException(super.statusCode, super.message);
}

class SkillConflictException extends SkillRegistryApiException {
  SkillConflictException(super.statusCode, super.message);
}

class SkillValidationException extends SkillRegistryApiException {
  SkillValidationException(super.statusCode, super.message);
}

class SkillRegistryService {
  Future<String?> _getWorkspaceId() async {
    return SecureStorageService.read('workspace_id');
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

    if (response.statusCode == 401 || response.statusCode == 403) {
      throw SkillAuthException(response.statusCode, detail);
    }
    if (response.statusCode == 404) {
      throw SkillNotFoundException(response.statusCode, detail);
    }
    if (response.statusCode == 409) {
      throw SkillConflictException(response.statusCode, detail);
    }
    if (response.statusCode == 422) {
      throw SkillValidationException(response.statusCode, detail);
    }
    throw SkillRegistryApiException(response.statusCode, detail);
  }

  Future<List<Map<String, dynamic>>> syncBuiltInSkills() async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post('/agent/skills/sync-built-in?workspace_id=$wsId');
    final data = _decode(res);
    if (data is Map && data['skills'] is List) {
      return (data['skills'] as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
    }
    if (data is List) {
      return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return [];
  }

  Future<List<Map<String, dynamic>>> listSkills({String? domain, String? status}) async {
    final wsId = await _requireWorkspaceId();
    var path = '/agent/skills?workspace_id=$wsId';
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
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.get('/agent/skills/$skillId?workspace_id=$wsId');
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
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.put(
      '/agent/skills/$skillId?workspace_id=$wsId',
      body: {
        'name': ?name,
        'description': ?description,
        'instructions': ?instructions,
        'tool_permissions': ?toolPermissions,
        'required_capabilities': ?toolPermissions,
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
      '/agent/skills/candidates',
      body: {
        'workspace_id': wsId,
        'name': name,
        'domain': domain,
        'instructions': instructions,
        'description': description,
        'scope': scope,
        'tool_permissions': toolPermissions,
        'required_capabilities': toolPermissions,
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
      '/agent/skills/$skillId/evaluate',
      body: {
        'eval_score': evalScore,
        'eval_details': evalDetails ?? {},
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> promoteSkill({
    required String skillId,
    required String approvedBy,
    required String approvalReason,
    String? version,
  }) async {
    final res = await ApiClient.post(
      '/agent/skills/$skillId/promote',
      body: {
        'approved_by': approvedBy,
        'approval_reason': approvalReason,
        'version': ?version,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> deprecateSkill(String skillId, {String? reason}) async {
    final res = await ApiClient.post(
      '/agent/skills/$skillId/deprecate',
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
    String? notes,
  }) async {
    final res = await ApiClient.post(
      '/agent/skills/$skillId/feedback',
      body: {
        'success': success,
        'rating': ?rating,
        'notes': ?notes,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }
}
