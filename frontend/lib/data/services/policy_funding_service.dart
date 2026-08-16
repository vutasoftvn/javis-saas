import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

class PolicyFundingApiException implements Exception {
  final int statusCode;
  final String message;
  PolicyFundingApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

class PolicyFundingService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<String> _requireWorkspaceId() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) {
      throw PolicyFundingApiException(0, 'Chưa xác định workspace hiện tại');
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
    throw PolicyFundingApiException(response.statusCode, detail);
  }

  Future<Map<String, dynamic>> getFundingOverview(String projectId) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.get('/projects/$projectId/funding-overview?workspace_id=$wsId');
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> triggerMatching(String projectId) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post(
      '/projects/$projectId/policy-match?workspace_id=$wsId',
      body: {},
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> assessStage({
    required String projectId,
    required String companyType,
    required String stage,
    String? notes,
  }) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post(
      '/projects/$projectId/assess-stage?workspace_id=$wsId',
      body: {
        'company_type': companyType,
        'stage': stage,
        'is_founder_confirmed': true,
        'notes': ?notes,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> assessTrl({
    required String projectId,
    required int trlCurrent,
    int? trlTarget,
    String? explanation,
  }) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post(
      '/projects/$projectId/assess-trl?workspace_id=$wsId',
      body: {
        'trl_current': trlCurrent,
        'trl_target': ?trlTarget,
        'explanation': ?explanation,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> create12wyTask({
    required String projectId,
    required int missingRequirementId,
    String? customTitle,
  }) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post(
      '/projects/$projectId/create-12wy-task?workspace_id=$wsId',
      body: {
        'missing_requirement_id': missingRequirementId,
        'custom_title': ?customTitle,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> checkDoubleFunding({
    required String projectId,
    required String workPackage,
    required String costCategory,
    required String purpose,
    required double amount,
  }) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post(
      '/projects/$projectId/check-double-funding?workspace_id=$wsId',
      body: {
        'project_id': int.tryParse(projectId) ?? 0,
        'work_package': workPackage,
        'cost_category': costCategory,
        'purpose': purpose,
        'amount': amount,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<List<dynamic>> listPrograms({String? status, String? programType}) async {
    final wsId = await _requireWorkspaceId();
    var path = '/policy-programs?workspace_id=$wsId';
    if (status != null) path += '&status=$status';
    if (programType != null) path += '&program_type=$programType';
    final res = await ApiClient.get(path);
    final data = _decode(res);
    return data is List ? data : [];
  }

  Future<List<dynamic>> getCurrentBenefits({
    String? programType,
    String? geography,
    String? verificationStatus,
  }) async {
    final wsId = await _requireWorkspaceId();
    var path = '/policy-programs/current-benefits?workspace_id=$wsId';
    if (programType != null) path += '&program_type=$programType';
    if (geography != null) path += '&geography=$geography';
    if (verificationStatus != null) path += '&verification_status=$verificationStatus';
    final res = await ApiClient.get(path);
    final data = _decode(res);
    return data is List ? data : [];
  }

  Future<List<dynamic>> getDraftWatchlist() async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.get('/policy-programs/draft-watchlist?workspace_id=$wsId');
    final data = _decode(res);
    return data is List ? data : [];
  }

  Future<Map<String, dynamic>> getProgramDetail(String programId) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.get('/policy-programs/$programId?workspace_id=$wsId');
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> verifyProgram({
    required String programId,
    required String resultStatus,
    String? officialSourceUrl,
    String? officialAuthority,
    String? notes,
    Map<String, String>? updatedClaims,
  }) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post(
      '/policy-programs/$programId/verify?workspace_id=$wsId',
      body: {
        'result_status': resultStatus,
        'official_source_url': ?officialSourceUrl,
        'official_authority': ?officialAuthority,
        'notes': ?notes,
        'updated_claims': updatedClaims ?? {},
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<List<dynamic>> getProgramClaims(String programId) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.get('/policy-programs/$programId/claims?workspace_id=$wsId');
    final data = _decode(res);
    return data is List ? data : [];
  }

  Future<Map<String, dynamic>> updateClaim({
    required String programId,
    required String claimId,
    String? claimValue,
    bool? isVerified,
    String? verifiedValue,
  }) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.put(
      '/policy-programs/$programId/claims/$claimId?workspace_id=$wsId',
      body: {
        'claim_value': ?claimValue,
        'is_verified': ?isVerified,
        'verified_value': ?verifiedValue,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }
}

