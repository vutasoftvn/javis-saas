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
    final data = await getJson('/legal/status');
    if (data is Map<String, dynamic>) {
      return data;
    }
    return {'function': 'LEGAL', 'open_checklist_items': 0, 'open_obligations': 0};
  }

  Future<Map<String, dynamic>?> analyzeContract({
    required String contractText,
    String contractType = 'COMMERCIAL_SERVICE',
  }) async {
    final data = await postJson('/legal/reviews/analyze', {
      'contract_text': contractText,
      'contract_type': contractType,
    });
    if (data is Map && data['data'] is Map) {
      return Map<String, dynamic>.from(data['data']);
    }
    return null;
  }

  Future<List<dynamic>> getChecklist() async {
    final data = await getJson('/legal/checklist');
    if (data is Map && data['data'] is List) {
      return data['data'] as List<dynamic>;
    }
    return [];
  }

  Future<List<dynamic>> getObligations() async {
    final data = await getJson('/legal/obligations');
    if (data is Map && data['data'] is List) {
      return data['data'] as List<dynamic>;
    }
    return [];
  }

  Future<Map<String, dynamic>?> createChecklistItem(String title) async {
    final data = await postJson('/legal/checklist', {'title': title});
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> getLegalSources({String packId = 'governance'}) async {
    final data = await getJson('/business/packs/$packId/legal/resolve');
    if (data is Map && data['data'] is List) {
      return (data['data'] as List).map((e) => e as Map<String, dynamic>).toList();
    }
    return [];
  }
}

