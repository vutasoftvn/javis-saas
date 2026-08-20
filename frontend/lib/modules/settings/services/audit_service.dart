import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/network/api_client.dart';

class AuditService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<Map<String, dynamic>> getAuditEvents({
    String? action,
    String? actorType,
    int limit = 50,
    int offset = 0,
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return {'total': 0, 'events': []};

    var url = '/admin/$workspaceId/audit-events?limit=$limit&offset=$offset';
    if (action != null && action.isNotEmpty) {
      url += '&action=$action';
    }
    if (actorType != null && actorType.isNotEmpty) {
      url += '&actor_type=$actorType';
    }

    final response = await ApiClient.get(url);
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return {'total': 0, 'events': []};
  }
}
