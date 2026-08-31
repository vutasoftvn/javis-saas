import 'package:http/http.dart' as http;

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/vault_models.dart';

class VaultMvpService {
  final MvpRequestClient _client;

  VaultMvpService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  // ─── Document Operations ───

  Future<ApiResult<List<VaultDocument>>> listDocuments({String? state, int limit = 50}) async {
    final query = <String, String>{
      'limit': limit.toString(),
    };
    if (state != null) {
      query['state'] = state;
    }

    return _client.request<List<VaultDocument>>(
      MvpEndpoint.vaultDocumentList,
      query: query,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => VaultDocument.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<VaultDocumentDetail>> getDocument(String id) async {
    return _client.request<VaultDocumentDetail>(
      MvpEndpoint.vaultDocumentGet,
      pathParams: {'id': id},
      decode: (json) => VaultDocumentDetail.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<VaultUploadTicket>> createUploadTicket({
    required String fileName,
    required String mediaType,
    required int sizeBytes,
  }) async {
    return _client.request<VaultUploadTicket>(
      MvpEndpoint.vaultDocumentUploadTicket,
      body: {
        'file_name': fileName,
        'media_type': mediaType,
        'size_bytes': sizeBytes,
      },
      decode: (json) => VaultUploadTicket.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<VaultDocument>> confirmUpload(
    String id, {
    required String checksumSha256,
    required int sizeBytes,
  }) async {
    return _client.request<VaultDocument>(
      MvpEndpoint.vaultDocumentConfirmUpload,
      pathParams: {'id': id},
      body: {
        'checksum_sha256': checksumSha256,
        'size_bytes': sizeBytes,
      },
      decode: (json) => VaultDocument.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<Map<String, dynamic>>> deleteDocument(String id) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.vaultDocumentDelete,
      pathParams: {'id': id},
      decode: (json) => json as Map<String, dynamic>,
    );
  }

  // ─── Knowledge Graph, Sources & Retrieval ───

  Future<ApiResult<VaultKnowledgeGraph>> getKnowledgeGraph() async {
    return _client.request<VaultKnowledgeGraph>(
      MvpEndpoint.vaultKnowledgeGraph,
      decode: (json) => VaultKnowledgeGraph.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<List<VaultIndexedSource>>> listIndexedSources() async {
    return _client.request<List<VaultIndexedSource>>(
      MvpEndpoint.vaultKnowledgeIndexedSources,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => VaultIndexedSource.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<List<VaultRetrievalHit>>> retrievalQuery(
    String query, {
    int limit = 10,
    double minScore = 0.0,
  }) async {
    return _client.request<List<VaultRetrievalHit>>(
      MvpEndpoint.vaultKnowledgeRetrievalQuery,
      body: {
        'query': query,
        'limit': limit,
        'min_score': minScore,
      },
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => VaultRetrievalHit.fromJson(e))
            .toList();
      },
    );
  }
}
