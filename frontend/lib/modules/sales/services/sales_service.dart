import 'dart:convert';
import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';
import '../../../data/models/commercial_models.dart';

class SalesService extends WorkspaceService {
  Future<List<AccountModel>> getTypedAccounts() async {
    final list = await getAccounts();
    return list.map((e) => AccountModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }

  Future<List<LeadModel>> getTypedLeads() async {
    final list = await getLeads();
    return list.map((e) => LeadModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }

  Future<List<OpportunityModel>> getTypedOpportunities({String? stage, String? accountId}) async {
    final list = await getOpportunities(stage: stage, accountId: accountId);
    return list.map((e) => OpportunityModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }

  Future<List<CustomerModel>> getTypedCustomers() async {
    final list = await getCustomers();
    return list.map((e) => CustomerModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }

  // Accounts
  Future<List<dynamic>> getAccounts() async {
    final wId = await stringWorkspaceId() ?? '1';
    final data = await getJson('/commercial/workspaces/$wId/accounts');
    return data is Map && data['accounts'] is List ? data['accounts'] as List<dynamic> : const [];
  }

  Future<Map<String, dynamic>?> createAccount(Map<String, dynamic> payload) async {
    final wId = await stringWorkspaceId() ?? '1';
    final body = Map<String, dynamic>.from(payload);
    body['workspaceId'] = body['workspaceId']?.toString() ?? wId;
    body['companyId'] = body['companyId']?.toString() ?? '1';
    final res = await postJson('/commercial/accounts', body);
    return res is Map<String, dynamic> ? res : null;
  }

  // Contacts
  Future<List<dynamic>> getContacts({String? accountId}) async {
    final wId = await stringWorkspaceId() ?? '1';
    final path = accountId != null ? '/commercial/workspaces/$wId/contacts?accountId=$accountId' : '/commercial/workspaces/$wId/contacts';
    final data = await getJson(path);
    return data is Map && data['contacts'] is List ? data['contacts'] as List<dynamic> : const [];
  }

  Future<Map<String, dynamic>?> createContact(Map<String, dynamic> payload) async {
    final wId = await stringWorkspaceId() ?? '1';
    final body = Map<String, dynamic>.from(payload);
    body['workspaceId'] = body['workspaceId']?.toString() ?? wId;
    body['companyId'] = body['companyId']?.toString() ?? '1';
    final res = await postJson('/commercial/contacts', body);
    return res is Map<String, dynamic> ? res : null;
  }

  // Leads
  Future<List<dynamic>> getLeads() async {
    final wId = await stringWorkspaceId() ?? '1';
    try {
      final response = await ApiClient.get('/commercial/leads?workspace_id=$wId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        return data is Map && data['leads'] is List ? data['leads'] as List<dynamic> : const [];
      }
    } catch (_) {}
    return const [];
  }

  Future<Map<String, dynamic>?> createLead(Map<String, dynamic> payload) async {
    final wId = await stringWorkspaceId() ?? '1';
    final body = Map<String, dynamic>.from(payload);
    body['workspaceId'] = body['workspaceId']?.toString() ?? wId;
    body['companyId'] = body['companyId']?.toString() ?? '1';
    final res = await postJson('/commercial/leads', body);
    return res is Map<String, dynamic> ? res : null;
  }

  Future<Map<String, dynamic>?> qualifyLead(String leadId, Map<String, dynamic> payload) async {
    final res = await postJson('/commercial/leads/$leadId/stage', {'stage': 'QUALIFIED', ...payload});
    return res is Map<String, dynamic> ? res : null;
  }

  Future<Map<String, dynamic>?> convertLead(String leadId, Map<String, dynamic> payload) async {
    final res = await postJson('/commercial/leads/$leadId/stage', {'stage': 'CONVERTED', ...payload});
    return res is Map<String, dynamic> ? res : null;
  }

  Future<Map<String, dynamic>?> intakeFromHandoff(String handoffId) async {
    final res = await postJson('/commercial/leads/from-handoff/$handoffId', {});
    return res is Map<String, dynamic> ? res : null;
  }

  // Opportunities
  Future<List<dynamic>> getOpportunities({String? stage, String? accountId}) async {
    final wId = await stringWorkspaceId() ?? '1';
    final params = <String>[];
    if (stage != null) params.add('stage=$stage');
    if (accountId != null) params.add('accountId=$accountId');
    final queryStr = params.isNotEmpty ? '?${params.join('&')}' : '';
    final data = await getJson('/commercial/workspaces/$wId/opportunities$queryStr');
    return data is Map && data['opportunities'] is List ? data['opportunities'] as List<dynamic> : const [];
  }

  Future<Map<String, dynamic>?> createOpportunity(Map<String, dynamic> payload) async {
    final wId = await stringWorkspaceId() ?? '1';
    final body = Map<String, dynamic>.from(payload);
    body['workspaceId'] = body['workspaceId']?.toString() ?? wId;
    body['companyId'] = body['companyId']?.toString() ?? '1';
    final res = await postJson('/commercial/opportunities', body);
    return res is Map<String, dynamic> ? res : null;
  }

  Future<Map<String, dynamic>?> changeOpportunityStage(String oppId, String targetStage) async {
    final res = await postJson('/commercial/opportunities/$oppId/stage', {'stage': targetStage});
    return res is Map<String, dynamic> ? res : null;
  }

  Future<Map<String, dynamic>?> winOpportunity(String oppId, String wonReason, String? evidence) async {
    final res = await postJson('/commercial/opportunities/$oppId/stage', {
      'stage': 'WON',
      'wonReason': wonReason,
      'evidence': evidence,
    });
    return res is Map<String, dynamic> ? res : null;
  }

  Future<Map<String, dynamic>?> loseOpportunity(String oppId, String lostReason, String? detail) async {
    final res = await postJson('/commercial/opportunities/$oppId/stage', {
      'stage': 'LOST',
      'lostReason': lostReason,
      'lostReasonDetail': detail,
    });
    return res is Map<String, dynamic> ? res : null;
  }

  // Customers
  Future<List<dynamic>> getCustomers() async {
    final wId = await stringWorkspaceId() ?? '1';
    final data = await getJson('/commercial/workspaces/$wId/customers');
    return data is Map && data['customers'] is List ? data['customers'] as List<dynamic> : const [];
  }

  Future<Map<String, dynamic>?> updateCustomerHealth(String customerId, String healthStatus, {String? lifecycleStatus}) async {
    final res = await postJson('/commercial/customers/$customerId/health', {
      'healthStatus': healthStatus,
      'lifecycleStatus': lifecycleStatus,
    });
    return res is Map<String, dynamic> ? res : null;
  }

  // Activities
  Future<List<dynamic>> getActivities({String? entityType, String? entityId}) async {
    final wId = await intWorkspaceId() ?? 1;
    final params = <String>[];
    if (entityType != null) params.add('entityType=$entityType');
    if (entityId != null) params.add('entityId=$entityId');
    final queryStr = params.isNotEmpty ? '?${params.join('&')}' : '';
    final data = await getJson('/commercial/workspaces/$wId/activities$queryStr');
    return data is Map && data['activities'] is List ? data['activities'] as List<dynamic> : const [];
  }

  Future<Map<String, dynamic>?> createActivity(Map<String, dynamic> payload) async {
    final res = await postJson('/commercial/activities', payload);
    return res is Map<String, dynamic> ? res : null;
  }

  // Funnel
  Future<Map<String, dynamic>?> getFunnelMetrics() async {
    final wId = await intWorkspaceId() ?? 1;
    final data = await getJson('/commercial/workspaces/$wId/funnel');
    return data is Map<String, dynamic> ? data : null;
  }
}
