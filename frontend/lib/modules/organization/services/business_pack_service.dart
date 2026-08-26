import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../core/services/secure_storage_service.dart';
import '../../../core/network/api_client.dart';

class BusinessPackService {
  Future<String?> _getWorkspaceId() async {
    return SecureStorageService.read('workspace_id');
  }

  /// Liệt kê toàn bộ các gói nghiệp vụ (12 Business Domains)
  Future<List<Map<String, dynamic>>> listPacks() async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return [];

    try {
      final response = await ApiClient.get('/business/packs?workspace_id=$workspaceId');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        final List items = decoded['data'] ?? [];
        return items.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('BusinessPackService.listPacks error: $e');
    }
    return [];
  }

  /// Lấy chi tiết một gói (Capabilities, Templates, SOPs, References)
  Future<Map<String, dynamic>?> getPackDetails(String packId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/business/packs/$packId?workspace_id=$workspaceId');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('BusinessPackService.getPackDetails error: $e');
    }
    return null;
  }

  /// Phân giải Template (ưu tiên Company Override nếu có)
  Future<Map<String, dynamic>?> resolveTemplate(String packId, String templateId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/business/packs/$packId/templates/$templateId?workspace_id=$workspaceId');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('BusinessPackService.resolveTemplate error: $e');
    }
    return null;
  }

  /// Phân giải SOP (ưu tiên Company Override nếu có)
  Future<Map<String, dynamic>?> resolveSOP(String packId, String sopId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.get('/business/packs/$packId/sops/$sopId?workspace_id=$workspaceId');
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('BusinessPackService.resolveSOP error: $e');
    }
    return null;
  }

  /// Tạo hoặc cập nhật Company Override (Admin Only)
  Future<Map<String, dynamic>?> createOrUpdateOverride({
    required String packId,
    required String assetId,
    required String assetType,
    Map<String, dynamic>? contentOverride,
    String? bodyOverride,
    String? notes,
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/business/packs/$packId/overrides?workspace_id=$workspaceId',
        body: {
          'asset_id': assetId,
          'asset_type': assetType,
          'content_override': contentOverride ?? {},
          'body_override': bodyOverride,
          'notes': notes,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('BusinessPackService.createOrUpdateOverride error: $e');
    }
    return null;
  }

  /// Khôi phục tài sản về Factory Default
  Future<bool> resetToFactory(String packId, String assetId) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return false;

    try {
      final response = await ApiClient.delete(
        '/business/packs/$packId/overrides/$assetId?workspace_id=$workspaceId',
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('BusinessPackService.resetToFactory error: $e');
      return false;
    }
  }

  /// Phân giải danh sách căn cứ pháp lý
  Future<List<Map<String, dynamic>>> resolveLegalSources(String packId, {List<String>? tags}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return [];

    try {
      String url = '/business/packs/$packId/legal/resolve?workspace_id=$workspaceId';
      if (tags != null && tags.isNotEmpty) {
        url += '&tags=${tags.join(',')}';
      }
      final response = await ApiClient.get(url);
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        final List items = decoded['data'] ?? [];
        return items.map((e) => e as Map<String, dynamic>).toList();
      }
    } catch (e) {
      debugPrint('BusinessPackService.resolveLegalSources error: $e');
    }
    return [];
  }

  /// Ghi chú diễn giải pháp lý doanh nghiệp
  Future<bool> addLegalAnnotation({
    required String packId,
    required String legalSourceId,
    required String applicabilityStatus,
    required List<String> notes,
    List<String>? linkedSops,
    List<String>? linkedTemplates,
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return false;

    try {
      final response = await ApiClient.post(
        '/business/packs/$packId/legal/annotations?workspace_id=$workspaceId',
        body: {
          'legal_source_id': legalSourceId,
          'applicability_status': applicabilityStatus,
          'notes': notes,
          'linked_sops': linkedSops ?? [],
          'linked_templates': linkedTemplates ?? [],
        },
      );
      return response.statusCode == 200 || response.statusCode == 201;
    } catch (e) {
      debugPrint('BusinessPackService.addLegalAnnotation error: $e');
      return false;
    }
  }

  /// Kiểm tra các bản cập nhật mới từ hệ sinh thái
  Future<Map<String, dynamic>?> checkForUpdates(String packId, {Map<String, dynamic>? updateManifest}) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/business/packs/$packId/updates/check?workspace_id=$workspaceId',
        body: {
          'update_manifest': updateManifest,
        },
      );
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('BusinessPackService.checkForUpdates error: $e');
    }
    return null;
  }

  /// Tạo visual diff so sánh bản cũ và bản mới
  Future<String?> generateDiff({
    required String packId,
    required String oldContent,
    required String newContent,
    String fromLabel = "Old Factory",
    String toLabel = "Company Override / New Factory",
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/business/packs/$packId/updates/diff?workspace_id=$workspaceId',
        body: {
          'old_content': oldContent,
          'new_content': newContent,
          'from_label': fromLabel,
          'to_label': toLabel,
        },
      );
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data']?['diff'] as String?;
      }
    } catch (e) {
      debugPrint('BusinessPackService.generateDiff error: $e');
    }
    return null;
  }

  /// Áp dụng giải quyết xung đột (KEEP_COMPANY, ACCEPT_FACTORY, MERGE, RESET_FACTORY)
  Future<Map<String, dynamic>?> resolveConflict({
    required String packId,
    required String assetId,
    required String resolution,
    String? mergedBody,
    Map<String, dynamic>? mergedMetadata,
  }) async {
    final workspaceId = await _getWorkspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;

    try {
      final response = await ApiClient.post(
        '/business/packs/$packId/updates/resolve?workspace_id=$workspaceId',
        body: {
          'asset_id': assetId,
          'resolution': resolution,
          'merged_body': mergedBody,
          'merged_metadata': mergedMetadata,
        },
      );
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        return decoded['data'] as Map<String, dynamic>?;
      }
    } catch (e) {
      debugPrint('BusinessPackService.resolveConflict error: $e');
    }
    return null;
  }
}
