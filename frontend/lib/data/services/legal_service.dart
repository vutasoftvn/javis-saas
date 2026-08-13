import 'v13_workspace_service.dart';

class LegalService extends V13WorkspaceService {
  Future<Map<String, dynamic>> getStatus() async {
    final data = await getJson('/legal/status');
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }
}
