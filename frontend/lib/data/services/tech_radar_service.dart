import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

class TechRadarApiException implements Exception {
  final int statusCode;
  final String message;
  TechRadarApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

class TechRadarService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<String> _requireWorkspaceId() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) {
      throw TechRadarApiException(0, 'Chưa xác định workspace hiện tại');
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
    throw TechRadarApiException(response.statusCode, detail);
  }

  Future<List<Map<String, dynamic>>> listItems({String? category, String? status}) async {
    final wsId = await _requireWorkspaceId();
    var path = '/tech-radar?workspace_id=$wsId';
    if (category != null && category.isNotEmpty) path += '&category=${Uri.encodeComponent(category)}';
    if (status != null && status.isNotEmpty) path += '&status=${Uri.encodeComponent(status)}';
    
    final res = await ApiClient.get(path);
    final data = _decode(res);
    if (data is List) {
      return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return [];
  }

  Future<Map<String, dynamic>> createItem({
    required String name,
    required String category,
    String status = 'WATCH',
    String maturity = 'experimental',
    String potential = 'high',
    String cosaUse = 'pattern',
    String integration = 'no',
    String? description,
    String? lastReviewed,
  }) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post(
      '/tech-radar',
      body: {
        'workspace_id': int.tryParse(wsId) ?? 1,
        'name': name,
        'category': category,
        'status': status,
        'maturity': maturity,
        'potential': potential,
        'cosa_use': cosaUse,
        'integration': integration,
        'description': ?description,
        'last_reviewed': ?lastReviewed,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> updateItem({
    required String itemId,
    String? status,
    String? maturity,
    String? potential,
    String? cosaUse,
    String? integration,
    String? description,
    String? lastReviewed,
  }) async {
    final res = await ApiClient.patch(
      '/tech-radar/$itemId',
      body: {
        'status': ?status,
        'maturity': ?maturity,
        'potential': ?potential,
        'cosa_use': ?cosaUse,
        'integration': ?integration,
        'description': ?description,
        'last_reviewed': ?lastReviewed,
      },
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<List<Map<String, dynamic>>> seedDefaults() async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post('/tech-radar/seed?workspace_id=$wsId');
    final data = _decode(res);
    if (data is List) {
      return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return [];
  }
}
