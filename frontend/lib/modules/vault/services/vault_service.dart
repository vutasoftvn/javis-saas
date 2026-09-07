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
    return _client.request<List<VaultDocument>>(
      MvpEndpoint.vaultDocumentList,
      decode: (json) {
        final list = json is List ? json : const [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => VaultDocument.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<VaultDocument>> getDocument(String documentId) async {
    return _client.request<VaultDocument>(
      MvpEndpoint.vaultDocumentGet,
      pathParams: {'id': documentId},
      decode: (json) => VaultDocument.fromJson(json as Map<String, dynamic>),
    );
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

    return _client.request<VaultDocumentUpload>(
      MvpEndpoint.vaultDocumentCreate,
      body: body,
      decode: (json) => VaultDocumentUpload.fromJson(json as Map<String, dynamic>),
    );
  }

  /// [uploadUrl] LUÔN là giá trị server trả từ [createDocument] — không bao
  /// giờ tự dựng chuỗi này ở client (xem docstring class).
  Future<bool> uploadContent(String uploadUrl, List<int> bytes) async {
    final response = await ApiClient.putBytes(uploadUrl, bytes);
    return response.statusCode == 204;
  }

  Future<ApiResult<VaultUploadStatus>> completeUpload(String uploadId) async {
    return _client.request<VaultUploadStatus>(
      MvpEndpoint.vaultUploadComplete,
      pathParams: {'id': uploadId},
      decode: (json) => VaultUploadStatus.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<VaultUploadStatus>> reviewDocument(
    String documentId, {
    required String reason,
    required String idempotencyKey,
  }) async {
    return _client.request<VaultUploadStatus>(
      MvpEndpoint.vaultDocumentReview,
      pathParams: {'id': documentId},
      body: {'reason': reason, 'idempotency_key': idempotencyKey},
      decode: (json) => VaultUploadStatus.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<VaultUploadStatus>> publishDocument(
    String documentId, {
    required String reason,
    required String idempotencyKey,
  }) async {
    return _client.request<VaultUploadStatus>(
      MvpEndpoint.vaultDocumentPublish,
      pathParams: {'id': documentId},
      body: {'reason': reason, 'idempotency_key': idempotencyKey},
      decode: (json) => VaultUploadStatus.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<VaultArchiveOrPurgeResult>> archiveDocument(String documentId) async {
    return _client.request<VaultArchiveOrPurgeResult>(
      MvpEndpoint.vaultDocumentArchive,
      pathParams: {'id': documentId},
      decode: (json) => VaultArchiveOrPurgeResult.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<VaultArchiveOrPurgeResult>> purgeDocument(String documentId) async {
    return _client.request<VaultArchiveOrPurgeResult>(
      MvpEndpoint.vaultDocumentPurge,
      pathParams: {'id': documentId},
      decode: (json) => VaultArchiveOrPurgeResult.fromJson(json as Map<String, dynamic>),
    );
  }
}
