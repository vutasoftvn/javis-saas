import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';

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

  Future<Map<String, dynamic>?> updateProfile(String mode) async {
    final data = await putJson('/finance/profile', {'mode': mode});
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

  Future<Map<String, dynamic>?> createPeriod(String startDate, String endDate) async {
    final data = await postJson('/finance/periods', {
      'start_date': startDate,
      'end_date': endDate,
    });
    return data is Map ? Map<String, dynamic>.from(data) : null;
  }

  Future<Map<String, dynamic>?> changePeriodStatus(String periodId, String status, {bool authorizeReopen = false}) async {
    final data = await postJson('/finance/periods/$periodId/status', {
      'status': status,
      'authorize_locked_reopen': authorizeReopen,
    });
    return data is Map ? Map<String, dynamic>.from(data) : null;
  }

  Future<List<dynamic>> getExceptions() async =>
      _list('/finance/exceptions', 'exceptions');

  // ==========================================
  // Multi-Regime Accounting Methods (TT58 & TT199)
  // ==========================================

  Future<List<Map<String, dynamic>>> getAvailableRegimes() async {
    final data = await getJson('/finance/regimes/available');
    if (data is Map && data['data'] is List) {
      return (data['data'] as List).map((e) => e as Map<String, dynamic>).toList();
    }
    return [];
  }

  Future<List<Map<String, dynamic>>> getFiscalYearHistory() async {
    final data = await getJson('/finance/regimes/history');
    if (data is Map && data['data'] is List) {
      return (data['data'] as List).map((e) => e as Map<String, dynamic>).toList();
    }
    return [];
  }

  Future<Map<String, dynamic>?> getCurrentFiscalRegime({int? fiscalYear}) async {
    final query = fiscalYear != null ? '?fiscal_year=$fiscalYear' : '';
    final data = await getJson('/finance/regimes/current$query');
    if (data is Map && data['data'] is Map) {
      return Map<String, dynamic>.from(data['data']);
    }
    return null;
  }

  Future<Map<String, dynamic>?> previewRegimeTransition({
    required int fromFiscalYear,
    required int toFiscalYear,
    String toRegulation = "TT199_2026",
  }) async {
    final data = await postJson('/finance/regimes/transition/preview', {
      'from_fiscal_year': fromFiscalYear,
      'to_fiscal_year': toFiscalYear,
      'to_regulation': toRegulation,
    });
    if (data is Map && data['data'] is Map) {
      return Map<String, dynamic>.from(data['data']);
    }
    return null;
  }

  Future<Map<String, dynamic>?> executeRegimeTransition({
    required int fromFiscalYear,
    required int toFiscalYear,
    String toRegulation = "TT199_2026",
    String? notes,
  }) async {
    final data = await postJson('/finance/regimes/transition/execute', {
      'from_fiscal_year': fromFiscalYear,
      'to_fiscal_year': toFiscalYear,
      'to_regulation': toRegulation,
      'notes': notes,
    });
    if (data is Map && data['data'] is Map) {
      return Map<String, dynamic>.from(data['data']);
    }
    return null;
  }

  Future<List<dynamic>> _list(String path, String key) async {
    final data = await getJson(path);
    return data is Map && data[key] is List
        ? data[key] as List<dynamic>
        : const [];
  }
}

