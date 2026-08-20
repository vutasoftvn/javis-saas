import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/network/api_client.dart';

class RevenueEngineService {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<Map<String, dynamic>?> getIcp() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/workspaces/$workspaceId/revenue/icp');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>? ?? decoded;
      }
    } catch (e) {
      debugPrint('RevenueEngineService.getIcp error: $e');
    }
    return null;
  }

  Future<List<dynamic>> getLeads({String? stage}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return [];

    try {
      final url = stage != null
          ? '/workspaces/$workspaceId/revenue/crm/leads?stage=$stage'
          : '/workspaces/$workspaceId/revenue/crm/leads';
      final response = await ApiClient.get(url);
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as List<dynamic>? ?? [];
      }
    } catch (e) {
      debugPrint('RevenueEngineService.getLeads error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> scoreLead(String leadId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/workspaces/$workspaceId/revenue/crm/leads/$leadId/score',
        body: {},
      );
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>? ?? decoded;
      }
    } catch (e) {
      debugPrint('RevenueEngineService.scoreLead error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> getPipeline() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/workspaces/$workspaceId/revenue/crm/pipeline');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>? ?? decoded;
      }
    } catch (e) {
      debugPrint('RevenueEngineService.getPipeline error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> updateOpportunityStage({
    required String opportunityId,
    required String stage,
    String? lostReason,
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final body = <String, dynamic>{
        'stage': stage,
      };
      if (lostReason != null) body['lost_reason'] = lostReason;

      final response = await ApiClient.patch(
        '/workspaces/$workspaceId/revenue/crm/opportunities/$opportunityId/stage',
        body: body,
      );
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>? ?? decoded;
      }
    } catch (e) {
      debugPrint('RevenueEngineService.updateOpportunityStage error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> convertLeadToOpportunity({
    required String leadId,
    String? title,
    double estimatedValue = 50000000.0,
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final body = <String, dynamic>{
        'estimated_value': estimatedValue,
      };
      if (title != null) body['title'] = title;

      final response = await ApiClient.post(
        '/workspaces/$workspaceId/revenue/crm/leads/$leadId/convert-to-opportunity',
        body: body,
      );
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>? ?? decoded;
      }
    } catch (e) {
      debugPrint('RevenueEngineService.convertLeadToOpportunity error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> generateOutreach({
    required String leadId,
    String channel = 'email',
    String tone = 'professional',
    String? focusPainPoint,
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final body = <String, dynamic>{
        'lead_id': leadId,
        'channel': channel,
        'tone': tone,
      };
      if (focusPainPoint != null && focusPainPoint.isNotEmpty) {
        body['focus_pain_point'] = focusPainPoint;
      }

      final response = await ApiClient.post(
        '/workspaces/$workspaceId/revenue/outreach/generate',
        body: body,
      );
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>? ?? decoded;
      }
    } catch (e) {
      debugPrint('RevenueEngineService.generateOutreach error: $e');
    }
    return null;
  }

  Future<List<dynamic>> getAccounts({
    String? accountType,
    String? lifecycleStatus,
    String? search,
    String? tag,
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return [];

    try {
      final params = <String>[];
      if (accountType != null && accountType.isNotEmpty) params.add('account_type=$accountType');
      if (lifecycleStatus != null && lifecycleStatus.isNotEmpty) params.add('lifecycle_status=$lifecycleStatus');
      if (search != null && search.isNotEmpty) params.add('search=${Uri.encodeComponent(search)}');
      if (tag != null && tag.isNotEmpty) params.add('tag=${Uri.encodeComponent(tag)}');

      final queryStr = params.isNotEmpty ? '?${params.join('&')}' : '';
      final response = await ApiClient.get('/workspaces/$workspaceId/revenue/crm/accounts$queryStr');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as List<dynamic>? ?? [];
      }
    } catch (e) {
      debugPrint('RevenueEngineService.getAccounts error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> createAccount({
    required String name,
    String category = 'CUSTOMER',
    String? domain,
    String? industry,
    String? sizeSegment,
    String? source,
    String? lifecycleStatus,
    List<String>? tags,
    String? contactName,
    String? contactPhone,
    String? contactEmail,
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final body = <String, dynamic>{
        'name': name,
        'category': category,
      };
      if (domain != null) body['domain'] = domain;
      if (industry != null) body['industry'] = industry;
      if (sizeSegment != null) body['size_segment'] = sizeSegment;
      if (source != null) body['source'] = source;
      if (lifecycleStatus != null) body['lifecycle_status'] = lifecycleStatus;
      if (tags != null) body['tags'] = tags;
      if (contactName != null) body['contact_name'] = contactName;
      if (contactPhone != null) body['contact_phone'] = contactPhone;
      if (contactEmail != null) body['contact_email'] = contactEmail;

      final response = await ApiClient.post(
        '/workspaces/$workspaceId/revenue/crm/accounts',
        body: body,
      );
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>? ?? decoded;
      }
    } catch (e) {
      debugPrint('RevenueEngineService.createAccount error: $e');
    }
    return null;
  }
}
