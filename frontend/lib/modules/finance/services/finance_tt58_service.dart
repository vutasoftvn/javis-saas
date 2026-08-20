import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/network/api_client.dart';

class FinanceTT58Service {
  Future<String?> _getWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('workspace_id');
  }

  Future<Map<String, dynamic>?> getFounderLiteMetrics() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/workspaces/$workspaceId/finance/tt58/metrics/founder-lite');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('FinanceTT58Service.getFounderLiteMetrics error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> createAndPostDocument({
    required String documentNo,
    required String documentType,
    required double amount,
    required String direction,
    required String description,
    String category = 'DOANH_THU',
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      // 1. Tạo chứng từ DRAFT
      final createRes = await ApiClient.post(
        '/workspaces/$workspaceId/finance/tt58/documents',
        body: {
          'document_no': documentNo,
          'document_type': documentType,
          'total_amount': amount,
          'description': description,
          'direction': direction,
        },
      );

      if (createRes.statusCode != 200) return null;
      final createdData = jsonDecode(createRes.body)['data'] as Map<String, dynamic>;
      final docId = createdData['id']?.toString();
      if (docId == null) return null;

      // 2. Ghi sổ (Post)
      final postRes = await ApiClient.post(
        '/workspaces/$workspaceId/finance/tt58/documents/$docId/post',
        body: {
          'amount': amount,
          'direction': direction,
          'description': description,
          'category': category,
        },
      );

      if (postRes.statusCode == 200) {
        return jsonDecode(postRes.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('FinanceTT58Service.createAndPostDocument error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> voidDocument(String documentId, String reason) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/workspaces/$workspaceId/finance/tt58/documents/$documentId/void',
        body: {'reason': reason},
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('FinanceTT58Service.voidDocument error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> getReportB01() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/workspaces/$workspaceId/finance/tt58/reports/b01');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('FinanceTT58Service.getReportB01 error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> getReportB02() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/workspaces/$workspaceId/finance/tt58/reports/b02');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('FinanceTT58Service.getReportB02 error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> getReportB03() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/workspaces/$workspaceId/finance/tt58/reports/b03');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('FinanceTT58Service.getReportB03 error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> getReportF01() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/workspaces/$workspaceId/finance/tt58/reports/f01');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('FinanceTT58Service.getReportF01 error: $e');
    }
    return null;
  }
}
