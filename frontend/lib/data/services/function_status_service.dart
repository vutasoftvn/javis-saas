import 'v13_workspace_service.dart';

class FunctionStatusService extends V13WorkspaceService {
  Future<List<Map<String, dynamic>>> getStatuses() async {
    final data = await getJson('/functions/status');
    final rows = data is Map ? data['functions'] : null;
    if (rows is! List) return const [];
    return rows.whereType<Map>().map((row) => Map<String, dynamic>.from(row)).toList();
  }
}
