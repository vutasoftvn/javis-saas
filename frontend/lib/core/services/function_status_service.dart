import '../network/workspace_scoped_service.dart';

class FunctionStatusService extends WorkspaceService {
  Future<List<Map<String, dynamic>>> getStatuses() async {
    final data = await getJson('/functions/status');
    final rows = data is Map ? data['functions'] : null;
    if (rows is! List) return const [];
    return rows.whereType<Map>().map((row) => Map<String, dynamic>.from(row)).toList();
  }
}
