import 'workspace_service.dart';

class LegalService extends WorkspaceService {
  Future<Map<String, dynamic>> getStatus() async {
    final data = await getJson('/legal/status');
    return data is Map ? Map<String, dynamic>.from(data) : <String, dynamic>{};
  }
}
