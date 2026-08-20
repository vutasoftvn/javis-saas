import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../../core/network/api_client.dart';
import '../models/company_pulse_model.dart';
import '../models/founder_decision_model.dart';
import '../models/workforce_pack_model.dart';

/// G2 P0.8 / G3 §10.4: `chatWithCoFounder` used to collapse every failure
/// (non-200 status, network exception, JSON decode error) into a `null`
/// return, which the caller then displayed as a fabricated "I've noted this
/// and I'm coordinating..." success message. Thrown on failure now, so the
/// caller can render a real error instead of pretending the message landed.
class CoFounderChatException implements Exception {
  final String message;
  CoFounderChatException(this.message);

  @override
  String toString() => message;
}

class CoFounderApiService {
  /// Lấy thông tin nhịp tim tổng thể của doanh nghiệp (Company Pulse) từ Backend
  static Future<CompanyPulseModel?> getCompanyPulse({int? workspaceId, int? projectId}) async {
    try {
      final queryParams = <String>[];
      if (workspaceId != null) queryParams.add('workspace_id=$workspaceId');
      if (projectId != null) queryParams.add('project_id=$projectId');
      final q = queryParams.isNotEmpty ? '?${queryParams.join('&')}' : '';

      final response = await ApiClient.get('/cofounder/pulse$q');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return CompanyPulseModel.fromJson(data);
      }
      debugPrint('[CoFounderApiService] getCompanyPulse error status: ${response.statusCode}');
    } catch (e) {
      debugPrint('[CoFounderApiService] getCompanyPulse exception: $e');
    }
    return null;
  }

  /// Lấy Top 3 hành động tốt nhất hôm nay (Next Best Action) từ Backend
  static Future<List<NextBestActionModel>> getTop3Focus({int? workspaceId, int? projectId}) async {
    try {
      final queryParams = <String>[];
      if (workspaceId != null) queryParams.add('workspace_id=$workspaceId');
      if (projectId != null) queryParams.add('project_id=$projectId');
      final q = queryParams.isNotEmpty ? '?${queryParams.join('&')}' : '';

      final response = await ApiClient.get('/cofounder/top3$q');
      if (response.statusCode == 200) {
        final List<dynamic> list = jsonDecode(response.body);
        return list.map((e) => NextBestActionModel.fromJson(e as Map<String, dynamic>)).toList();
      }
      debugPrint('[CoFounderApiService] getTop3Focus error status: ${response.statusCode}');
    } catch (e) {
      debugPrint('[CoFounderApiService] getTop3Focus exception: $e');
    }
    return [];
  }

  /// Lấy danh sách các quyết định đang chờ Founder duyệt ('Waiting for You') từ Backend
  static Future<List<FounderDecisionModel>> listPendingDecisions({int? workspaceId}) async {
    try {
      final q = workspaceId != null ? '?workspace_id=$workspaceId' : '';
      final response = await ApiClient.get('/cofounder/decisions$q');
      if (response.statusCode == 200) {
        final List<dynamic> list = jsonDecode(response.body);
        return list.map((e) => FounderDecisionModel.fromJson(e as Map<String, dynamic>)).toList();
      }
      debugPrint('[CoFounderApiService] listPendingDecisions error status: ${response.statusCode}');
    } catch (e) {
      debugPrint('[CoFounderApiService] listPendingDecisions exception: $e');
    }
    return [];
  }

  /// Chốt quyết định chiến lược
  static Future<bool> resolveDecision({
    required int decisionId,
    required String decisionMade,
    String? founderNotes,
  }) async {
    try {
      final response = await ApiClient.post(
        '/cofounder/decisions/$decisionId/resolve',
        body: {
          'decision_made': decisionMade,
          'founder_notes': founderNotes,
          'status': 'DECIDED',
        },
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[CoFounderApiService] resolveDecision error: $e');
      return false;
    }
  }

  /// Trò chuyện và nhận chỉ đạo từ Co-Founder.
  ///
  /// Throws [CoFounderChatException] on any failure (network error, non-200
  /// status, malformed response) instead of returning null — the caller must
  /// be able to tell "request failed" apart from "request succeeded", since
  /// collapsing both to null previously led to a fabricated success message
  /// being shown to the founder (G2 P0.8).
  static Future<Map<String, dynamic>> chatWithCoFounder({
    required String message,
    int? workspaceId,
    int? projectId,
  }) async {
    final http.Response response;
    try {
      response = await ApiClient.post(
        '/cofounder/chat',
        body: {
          'message': message,
          'workspace_id': workspaceId,
          'project_id': projectId,
        },
      );
    } catch (e) {
      debugPrint('[CoFounderApiService] chatWithCoFounder network exception: $e');
      throw CoFounderChatException('Không thể kết nối tới COSA runtime: $e');
    }

    if (response.statusCode != 200) {
      debugPrint('[CoFounderApiService] chatWithCoFounder error status: ${response.statusCode}');
      throw CoFounderChatException(
        'COSA runtime phản hồi lỗi (HTTP ${response.statusCode}).',
      );
    }

    try {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      debugPrint('[CoFounderApiService] chatWithCoFounder decode exception: $e');
      throw CoFounderChatException('Không thể đọc phản hồi từ COSA runtime.');
    }
  }

  /// Lấy danh sách toàn bộ các 5 Core Domains và Optional Packs từ Backend
  static Future<List<WorkforcePackModel>> listWorkforcePacks({int? workspaceId}) async {
    try {
      final q = workspaceId != null ? '?workspace_id=$workspaceId' : '';
      final response = await ApiClient.get('/workforce/packs$q');
      if (response.statusCode == 200) {
        final List<dynamic> list = jsonDecode(response.body);
        return list.map((e) => WorkforcePackModel.fromJson(e as Map<String, dynamic>)).toList();
      }
      debugPrint('[CoFounderApiService] listWorkforcePacks error status: ${response.statusCode}');
    } catch (e) {
      debugPrint('[CoFounderApiService] listWorkforcePacks exception: $e');
    }
    return [];
  }

  /// Bật/Tắt một Optional Pack
  static Future<bool> toggleOptionalPack({
    required String packKey,
    required bool isActive,
    int? workspaceId,
  }) async {
    try {
      final response = await ApiClient.post(
        '/workforce/packs/$packKey/toggle',
        body: {
          'is_active': isActive,
          'workspace_id': workspaceId,
        },
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[CoFounderApiService] toggleOptionalPack error: $e');
      return false;
    }
  }
}
