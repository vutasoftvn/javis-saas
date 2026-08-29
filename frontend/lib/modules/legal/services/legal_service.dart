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
    final wId = await stringWorkspaceId();
    if (wId == null || wId.isEmpty) {
      return {
        'function': 'LEGAL',
        'workspaceId': null,
        'open_checklist_items': 0,
        'open_obligations': 0,
      };
    }
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
    final wId = await stringWorkspaceId();
    if (wId == null || wId.isEmpty) return [];
    final data = await getJson('/finance-legal/workspaces/$wId/legal-checklist-items');
    if (data is Map && data['items'] is List) {
      return data['items'] as List<dynamic>;
    }
    if (data is List) return data;
    return [];
  }

  Future<List<dynamic>> getObligations() async {
    final wId = await stringWorkspaceId();
    if (wId == null || wId.isEmpty) return [];
    final data = await getJson('/finance-legal/workspaces/$wId/legal-obligations');
    if (data is Map && data['obligations'] is List) {
      return data['obligations'] as List<dynamic>;
    }
    if (data is List) return data;
    return [];
  }

  Future<Map<String, dynamic>?> createChecklistItem(String title) async {
    final wId = await stringWorkspaceId();
    if (wId == null || wId.isEmpty) return null;
    final data = await postJson('/finance-legal/legal-checklist-items', {
      'workspaceId': wId,
      'title': title,
    });
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  Future<bool> completeChecklistItem(dynamic id) async {
    final data = await postJson('/finance-legal/legal-checklist-items/${id.toString()}/complete', {});
    return data != null;
  }

  Future<bool> fulfillObligation(dynamic id) async {
    final data = await postJson('/finance-legal/legal-obligations/${id.toString()}/fulfill', {});
    return data != null;
  }

  Future<List<Map<String, dynamic>>> getLegalSources({String packId = 'governance'}) async {
    final data = await getRegulationSources();
    return data.map((s) => {
      'id': s['id'],
      'source': s['sourceName'] ?? s['number'],
      'code': s['number'],
      'issuer': s['issuer'],
      'layer': s['layer'],
      'url': s['url'],
      'status': (s['versions'] as List?)?.any((v) => v['isActive'] == true) == true ? 'active' : 'inactive',
    }).toList();
  }

  Future<List<dynamic>> getRegulationSources({String? layer, bool? activeOnly}) async {
    final queryParams = <String>[];
    if (layer != null) queryParams.add('layer=$layer');
    if (activeOnly != null) queryParams.add('activeOnly=$activeOnly');
    final query = queryParams.isNotEmpty ? '?${queryParams.join('&')}' : '';
    final data = await getJson('/finance-legal/regulation-sources$query');
    if (data is Map && data['sources'] is List) {
      return data['sources'] as List<dynamic>;
    }
    return [];
  }

  Future<List<dynamic>> getApplicableObligations() async {
    final data = await getJson('/legal/applicable-obligations');
    if (data is Map && data['applicableObligations'] is List) {
      return data['applicableObligations'] as List<dynamic>;
    }
    return [];
  }

  Future<List<dynamic>> getObligationInstances({String? status}) async {
    final query = status != null ? '?status=$status' : '';
    final data = await getJson('/legal/obligation-instances$query');
    if (data is Map && data['instances'] is List) {
      return data['instances'] as List<dynamic>;
    }
    return [];
  }

  Future<List<dynamic>> getLegalEntityProfiles() async {
    final data = await getJson('/legal/legal-entity-profiles');
    if (data is Map && data['profiles'] is List) {
      return data['profiles'] as List<dynamic>;
    }
    return [];
  }

  Future<Map<String, dynamic>?> createLegalEntityProfile({
    required String entityType,
    String? registrationNumber,
    String? taxId,
  }) async {
    final data = await postJson('/legal/legal-entity-profiles', {
      'entityType': entityType,
      'registrationNumber': registrationNumber,
      'taxId': taxId,
    });
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  Future<Map<String, dynamic>?> requestVerification(String profileId) async {
    final data = await postJson('/legal/legal-entity-profiles/$profileId/verify', {});
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }

  Future<Map<String, dynamic>?> applyVerification(String profileId, String approvalId) async {
    final data = await postJson('/legal/legal-entity-profiles/$profileId/verify/confirm', {
      'approvalId': approvalId,
    });
    if (data is Map<String, dynamic>) {
      return data;
    }
    return null;
  }
}
