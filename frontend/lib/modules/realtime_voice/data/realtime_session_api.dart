import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/network/api_client.dart';

class RealtimeSessionApi {
  Future<Map<String, dynamic>?> createSession({required String deviceType}) async {
    final prefs = await SharedPreferences.getInstance();
    final wsId = prefs.getString('workspace_id');
    if (wsId == null || wsId.isEmpty) return null;

    final res = await ApiClient.post(
      '/realtime/sessions?workspace_id=$wsId',
      body: {'device_type': deviceType},
    );
    if (res.statusCode == 200) {
      return jsonDecode(res.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<void> endSession(String sessionId) async {
    final prefs = await SharedPreferences.getInstance();
    final wsId = prefs.getString('workspace_id');
    if (wsId == null || wsId.isEmpty) return;

    await ApiClient.post('/realtime/sessions/$sessionId/end?workspace_id=$wsId');
  }
}
