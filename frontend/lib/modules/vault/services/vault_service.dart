// Founder Trial R1 — legacy surface removed from the MVP contract. Every
// request here now returns MvpRequestClient.unavailable(); the retained
// class shell keeps callers compiling until the module is deleted.
// ignore_for_file: unused_field, unused_import, unused_element
import 'package:http/http.dart' as http;

import '../../../core/network/api_client.dart';
import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/vault_document.dart';

/// Task 12 (plan local-first-enterprise-knowledge) — client thật cho Vault
/// document lifecycle (create → upload → complete → review/publish →
/// archive/purge). Chỉ gọi qua `MvpEndpoint` (typed, contract-checked) —
/// NGOẠI LỆ duy nhất là [uploadContent], vốn PHẢI dùng URL opaque server tự
/// sinh (không phải template cố định, path đổi theo upload_id + chứa ticket
/// secret trong query — xem apps/cosa/api/vault_routes.py::create_document),
/// nên đi qua [ApiClient.putBytes] trực tiếp thay vì [MvpRequestClient].
class VaultService {
  final MvpRequestClient _client;

  VaultService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  Future<ApiResult<List<VaultDocument>>> listDocuments() async {
    return MvpRequestClient.unavailable<List<VaultDocument>>('vaultDocumentList was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<VaultDocument>> getDocument(String documentId) async {
    return MvpRequestClient.unavailable<VaultDocument>('vaultDocumentGet was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<VaultDocumentUpload>> createDocument({
    required String title,
    required String mediaType,
    String? classification,
    String? visibility,
  }) async {
    final body = <String, dynamic>{
      'title': title,
      'media_type': mediaType,
    };
    if (classification != null) body['classification'] = classification;
    if (visibility != null) body['visibility'] = visibility;

    return MvpRequestClient.unavailable<VaultDocumentUpload>('vaultDocumentCreate was removed from the Founder Trial R1 contract');
  }

  /// [uploadUrl] LUÔN là giá trị server trả từ [createDocument] — không bao
  /// giờ tự dựng chuỗi này ở client (xem docstring class).
  Future<bool> uploadContent(String uploadUrl, List<int> bytes) async {
    final response = await ApiClient.putBytes(uploadUrl, bytes);
    return response.statusCode == 204;
  }

  Future<ApiResult<VaultUploadStatus>> completeUpload(String uploadId) async {
    return MvpRequestClient.unavailable<VaultUploadStatus>('vaultUploadComplete was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<VaultUploadStatus>> reviewDocument(
    String documentId, {
    required String reason,
    required String idempotencyKey,
  }) async {
    return MvpRequestClient.unavailable<VaultUploadStatus>('vaultDocumentReview was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<VaultUploadStatus>> publishDocument(
    String documentId, {
    required String reason,
    required String idempotencyKey,
  }) async {
    return MvpRequestClient.unavailable<VaultUploadStatus>('vaultDocumentPublish was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<VaultArchiveOrPurgeResult>> archiveDocument(String documentId) async {
    return MvpRequestClient.unavailable<VaultArchiveOrPurgeResult>('vaultDocumentArchive was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<VaultArchiveOrPurgeResult>> purgeDocument(String documentId) async {
    return MvpRequestClient.unavailable<VaultArchiveOrPurgeResult>('vaultDocumentPurge was removed from the Founder Trial R1 contract');
  }
}
