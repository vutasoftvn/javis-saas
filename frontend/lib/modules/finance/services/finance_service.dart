import 'dart:convert';
import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';
import '../../../data/models/finance_legal_models.dart';

class FinanceService extends WorkspaceService {
  Future<FinanceSnapshotModel?> getTypedOverview() async {
    final data = await getOverview();
    return data != null ? FinanceSnapshotModel.fromJson(data) : null;
  }

  Future<List<FinancialTransactionModel>> getTypedTransactions() async {
    final list = await getTransactions();
    return list.map((e) => FinancialTransactionModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }

  Future<AccountingProfileModel?> getTypedProfile() async {
    final profile = await getProfile();
    return profile != null ? AccountingProfileModel.fromJson(profile) : null;
  }

  Future<List<AccountingPeriodModel>> getTypedPeriods() async {
    final list = await getPeriods();
    return list.map((e) => AccountingPeriodModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }

  Future<Map<String, dynamic>?> getOverview() async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.get('/finance-legal/snapshots/latest?workspaceId=$wId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data is Map<String, dynamic>) {
          return data['snapshot'] is Map ? Map<String, dynamic>.from(data['snapshot'] as Map) : data;
        }
      }
    } catch (_) {}
    return null;
  }

  Future<List<dynamic>> getTransactions() async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.get('/finance-legal/transactions?workspaceId=$wId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        return data is Map && data['transactions'] is List ? data['transactions'] as List<dynamic> : const [];
      }
    } catch (_) {}
    return const [];
  }

  Future<Map<String, dynamic>?> recordTransaction(Map<String, dynamic> payload) async {
    final wId = await stringWorkspaceId() ?? '1';
    final body = Map<String, dynamic>.from(payload);
    body['workspaceId'] = body['workspaceId']?.toString() ?? wId;
    body['companyId'] = body['companyId']?.toString() ?? '1';
    final res = await postJson('/finance-legal/transactions', body);
    return res is Map<String, dynamic> ? res : null;
  }

  Future<bool> approveTransaction(dynamic transactionId) async {
    final res = await ApiClient.post('/finance-legal/transactions/${transactionId.toString()}/approve', body: {});
    return res.statusCode == 200;
  }

  Future<List<dynamic>> getDocuments() async =>
      _list('/finance-legal/documents', 'documents');
  Future<List<dynamic>> getBooks() async =>
      _list('/finance-legal/books/templates', 'templates');
  Future<List<dynamic>> getReports() async =>
      _list('/finance-legal/reports', 'reports');

  Future<Map<String, dynamic>?> getProfile() async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.get('/finance-legal/accounting-profiles/by-workspace/$wId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data is Map<String, dynamic>) {
          return data['profile'] is Map ? Map<String, dynamic>.from(data['profile'] as Map) : data;
        }
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> createProfile(String mode) async {
    final wId = await stringWorkspaceId() ?? '1';
    final data = await postJson('/finance-legal/accounting-profiles', {
      'workspaceId': wId,
      'companyId': '1',
      'regime': mode,
    });
    return data is Map ? Map<String, dynamic>.from(data) : null;
  }

  Future<Map<String, dynamic>?> updateProfile(String mode) async {
    return createProfile(mode);
  }

  Future<Map<String, dynamic>?> activateProfile(String profileId) async {
    return {'status': 'active', 'profileId': profileId};
  }

  Future<List<dynamic>> getPeriods() async {
    final data = await getJson('/finance-legal/accounting-periods');
    return data is Map && data['periods'] is List ? data['periods'] as List<dynamic> : const [];
  }

  Future<Map<String, dynamic>?> createPeriod(String startDate, String endDate) async {
    final wId = await stringWorkspaceId() ?? '1';
    final data = await postJson('/finance-legal/accounting-periods', {
      'workspaceId': wId,
      'companyId': '1',
      'periodName': 'Kỳ kế toán ${startDate.substring(0, 7)}',
      'startDate': startDate,
      'endDate': endDate,
    });
    return data is Map ? Map<String, dynamic>.from(data) : null;
  }

  Future<Map<String, dynamic>?> changePeriodStatus(String periodId, String status, {bool authorizeReopen = false}) async {
    final res = await ApiClient.post('/finance-legal/accounting-periods/$periodId/close', body: {});
    return res.statusCode == 200 ? jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>? : null;
  }

  Future<List<dynamic>> getExceptions() async {
    final data = await getJson('/finance-legal/exceptions');
    return data is Map && data['exceptions'] is List ? data['exceptions'] as List<dynamic> : const [];
  }

  // ==========================================
  // Multi-Regime Accounting Methods (TT58 & TT199)
  // ==========================================

  Future<List<Map<String, dynamic>>> getAvailableRegimes() async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.get('/finance-legal/workspaces/$wId/fiscal-profiles');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data is Map && data['fiscalProfiles'] is List) {
          return (data['fiscalProfiles'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
        }
      }
    } catch (_) {}
    return [];
  }

  Future<List<Map<String, dynamic>>> getFiscalYearHistory() async {
    return getAvailableRegimes();
  }

  Future<Map<String, dynamic>?> getCurrentFiscalRegime({int? fiscalYear}) async {
    final list = await getAvailableRegimes();
    if (list.isNotEmpty) return list.first;
    return null;
  }

  Future<Map<String, dynamic>?> previewRegimeTransition({
    required int fromFiscalYear,
    required int toFiscalYear,
    String toRegulation = "TT199_2026",
  }) async {
    return {
      'fromFiscalYear': fromFiscalYear,
      'toFiscalYear': toFiscalYear,
      'toRegulation': toRegulation,
      'status': 'preview_ready',
    };
  }

  Future<Map<String, dynamic>?> executeRegimeTransition({
    required int fromFiscalYear,
    required int toFiscalYear,
    String toRegulation = "TT199_2026",
    String? notes,
  }) async {
    final wId = await stringWorkspaceId() ?? '1';
    final data = await postJson('/finance-legal/fiscal-profiles', {
      'workspaceId': wId,
      'companyId': '1',
      'fiscalYear': toFiscalYear,
      'accountingStandard': toRegulation,
    });
    return data is Map ? Map<String, dynamic>.from(data) : null;
  }

  Future<List<dynamic>> _list(String path, String key) async {
    final data = await getJson(path);
    return data is Map && data[key] is List
        ? data[key] as List<dynamic>
        : const [];
  }
}

