import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

class DeveloperService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<List<dynamic>> getDevices() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final response = await ApiClient.get('/devices?workspace_id=$workspaceId');
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['devices'] ?? [];
    }
    return [];
  }

  Future<Map<String, dynamic>?> enrollDevice(Map<String, dynamic> data) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.post(
      '/devices/enroll?workspace_id=$workspaceId',
      body: data,
    );
    if (response.statusCode == 201) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<List<dynamic>> getJobs({String? status}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return [];

    final statusParam = status != null ? '&status=$status' : '';
    final response = await ApiClient.get('/devices/jobs?workspace_id=$workspaceId$statusParam');
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['jobs'] ?? [];
    }
    return [];
  }

  Future<Map<String, dynamic>?> createJob(Map<String, dynamic> data) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null) return null;

    final response = await ApiClient.post(
      '/devices/jobs?workspace_id=$workspaceId',
      body: data,
    );
    if (response.statusCode == 201) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  // NOTE: claim-job and submit-results are intentionally not wrapped here.
  // Those two endpoints authenticate with a Device's own enrollment token
  // (see backend `get_current_device`), not a logged-in user's Bearer JWT -
  // a human session calling them would just get a 401. They belong to the
  // future Local Worker Plane (`desktop_worker/`, Phase 5 continuation), not
  // to this app.
}
