import 'v13_workspace_service.dart';

class SalesService extends V13WorkspaceService {
  Future<List<dynamic>> getLeads() async {
    final data = await getJson('/sales/leads');
    return data is Map && data['leads'] is List ? data['leads'] as List<dynamic> : const [];
  }
}
