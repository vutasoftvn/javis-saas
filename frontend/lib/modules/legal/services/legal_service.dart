import '../../../core/network/workspace_scoped_service.dart';
import '../../../data/models/finance_legal_models.dart';

class LegalService extends WorkspaceService {
  Future<List<LegalChecklistItemModel>> getTypedChecklist() async {
    final list = await getChecklist();
    return list.map((e) => LegalChecklistItemModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }

  Future<List<LegalObligationModel>> getTypedObligations() async {
    final list = await getObligations();
    return list.map((e) => LegalObligationModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }

  Future<Map<String, dynamic>> getStatus() async {
    final wId = await intWorkspaceId() ?? 1;
    final list = await getChecklist();
    final obligations = await getObligations();
    return {
      'function': 'LEGAL',
      'workspaceId': wId,
      'open_checklist_items': list.where((e) => e['status'] != 'COMPLETED').length,
      'open_obligations': obligations.where((e) => e['status'] != 'FULFILLED').length,
    };
  }

  Future<Map<String, dynamic>?> analyzeContract({
    required String contractText,
    String contractType = 'COMMERCIAL_SERVICE',
  }) async {
    final data = await postJson('/finance-legal/legal-reviews/analyze', {
      'contract_text': contractText,
      'contract_type': contractType,
    });
    if (data is Map && data['data'] is Map) {
      return Map<String, dynamic>.from(data['data']);
    }
    return null;
  }

  Future<List<dynamic>> getChecklist() async {
    final wId = await intWorkspaceId() ?? 1;
    final data = await getJson('/finance-legal/workspaces/$wId/legal-checklist-items');
    if (data is Map && data['items'] is List) {
      return data['items'] as List<dynamic>;
    }
    if (data is List) return data;
    return [];
  }

  Future<List<dynamic>> getObligations() async {
    final wId = await intWorkspaceId() ?? 1;
    final data = await getJson('/finance-legal/workspaces/$wId/legal-obligations');
    if (data is Map && data['obligations'] is List) {
      return data['obligations'] as List<dynamic>;
    }
    if (data is List) return data;
    return [];
  }

  Future<Map<String, dynamic>?> createChecklistItem(String title) async {
    final wId = await intWorkspaceId() ?? 1;
    final data = await postJson('/finance-legal/legal-checklist-items', {
      'workspaceId': wId,
      'companyId': 1,
      'title': title,
    });
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  Future<bool> completeChecklistItem(int id) async {
    final data = await postJson('/finance-legal/legal-checklist-items/$id/complete', {});
    return data != null;
  }

  Future<bool> fulfillObligation(int id) async {
    final data = await postJson('/finance-legal/legal-obligations/$id/fulfill', {});
    return data != null;
  }

  Future<List<Map<String, dynamic>>> getLegalSources({String packId = 'governance'}) async {
    return [
      {'source': 'Luật Doanh nghiệp 2020', 'code': 'LDN2020', 'status': 'active'},
      {'source': 'Thông tư 199/2026/TT-BTC', 'code': 'TT199', 'status': 'active'},
      {'source': 'Thông tư 58/2024/TT-BTC', 'code': 'TT58', 'status': 'active'},
    ];
  }
}

