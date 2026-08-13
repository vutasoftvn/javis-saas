import 'workspace_service.dart';

class FinanceService extends WorkspaceService {
  Future<Map<String, dynamic>?> getOverview() async {
    final data = await getJson('/finance/overview');
    final snapshot = data is Map ? data['snapshot'] : null;
    return snapshot is Map ? Map<String, dynamic>.from(snapshot) : null;
  }

  Future<List<dynamic>> getTransactions() async =>
      _list('/finance/transactions', 'transactions');
  Future<List<dynamic>> getDocuments() async =>
      _list('/finance/documents', 'documents');
  Future<List<dynamic>> getBooks() async =>
      _list('/finance/books/templates', 'templates');
  Future<List<dynamic>> getReports() async =>
      _list('/finance/reports', 'reports');
  Future<Map<String, dynamic>?> getProfile() async {
    final data = await getJson('/finance/profile');
    final profile = data is Map ? data['profile'] : null;
    return profile is Map ? Map<String, dynamic>.from(profile) : null;
  }

  Future<Map<String, dynamic>?> createProfile(String mode) async {
    final data = await postJson('/finance/profile', {'mode': mode});
    return data is Map ? Map<String, dynamic>.from(data) : null;
  }

  Future<Map<String, dynamic>?> activateProfile(String profileId) async {
    final data = await postJson(
      '/finance/profile/$profileId/activate',
      const {},
    );
    return data is Map ? Map<String, dynamic>.from(data) : null;
  }

  Future<List<dynamic>> getPeriods() async =>
      _list('/finance/periods', 'periods');
  Future<List<dynamic>> getExceptions() async =>
      _list('/finance/exceptions', 'exceptions');

  Future<List<dynamic>> _list(String path, String key) async {
    final data = await getJson(path);
    return data is Map && data[key] is List
        ? data[key] as List<dynamic>
        : const [];
  }
}
