import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/modules/vault/models/vault_models.dart';
import 'package:frontend/modules/vault/services/vault_mvp_service.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      'auth_token': 'test-token',
      'workspace_id': 'ws_1001',
    });
  });

  test('vault 503 is unavailable, not an empty documents collection', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({'code': 'unavailable', 'message': 'Service temporarily unavailable'}),
        503,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = VaultMvpService(client: requestClient);

    final result = await service.listDocuments();
    expect(result, isA<ApiFailure<List<VaultDocument>>>());
    expect((result as ApiFailure<List<VaultDocument>>).failure.code, ApiFailureCode.unavailable);
  });

  test('empty documents response returns ApiSuccess with empty dataState', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': [],
          'meta': {
            'dataState': 'empty',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'agent_db', 'ref': 'vault.documents'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = VaultMvpService(client: requestClient);

    final result = await service.listDocuments();
    expect(result, isA<ApiSuccess<List<VaultDocument>>>());
    final success = result as ApiSuccess<List<VaultDocument>>;
    expect(success.data, isEmpty);
    expect(success.meta.dataState, ApiDataState.empty);
    expect(success.meta.sources.first.kind, 'agent_db');
  });

  test('create upload ticket returns populated ApiSuccess', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, contains('/agent/vault/documents/upload-ticket'));
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['file_name'], 'architecture.pdf');

      return http.Response(
        jsonEncode({
          'data': {
            'ticket_id': 'tkt_123',
            'document_id': 'doc_456',
            'upload_url': '/agent/vault/documents/doc_456/upload',
            'expires_at': '2026-08-31T12:15:00.000Z',
            'max_bytes': 2048,
            'media_type': 'application/pdf',
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'agent_db', 'ref': 'vault.documents'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = VaultMvpService(client: requestClient);

    final result = await service.createUploadTicket(
      fileName: 'architecture.pdf',
      mediaType: 'application/pdf',
      sizeBytes: 2048,
    );
    expect(result, isA<ApiSuccess<VaultUploadTicket>>());
    final success = result as ApiSuccess<VaultUploadTicket>;
    expect(success.data.ticketId, 'tkt_123');
    expect(success.data.documentId, 'doc_456');
  });

  test('confirm upload returns indexed document ApiSuccess', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, contains('/agent/vault/documents/doc_456/confirm'));

      return http.Response(
        jsonEncode({
          'data': {
            'document_id': 'doc_456',
            'workspace_id': 'ws_1001',
            'title': 'architecture.pdf',
            'kind': 'document',
            'state': 'INDEXED',
            'current_version_id': 'ver_789',
            'knowledge_source_id': null,
            'created_by': 'user_1',
            'created_at': '2026-08-31T12:00:00.000Z',
            'updated_at': '2026-08-31T12:05:00.000Z',
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:05:00.000Z',
            'sources': [{'kind': 'agent_db', 'ref': 'vault.documents'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = VaultMvpService(client: requestClient);

    final result = await service.confirmUpload('doc_456', checksumSha256: 'sha256:abc', sizeBytes: 2048);
    expect(result, isA<ApiSuccess<VaultDocument>>());
    final success = result as ApiSuccess<VaultDocument>;
    expect(success.data.documentId, 'doc_456');
    expect(success.data.state, 'INDEXED');
  });

  test('retrieval query returns search hits truthfully', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, contains('/agent/vault/retrieval/query'));
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['query'], 'architecture');

      return http.Response(
        jsonEncode({
          'data': [
            {
              'source_id': 'doc_456',
              'title': 'architecture.pdf',
              'content': 'Architecture document content...',
              'score': 0.95,
              'metadata': {'kind': 'document'},
            }
          ],
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'agent_db', 'ref': 'vault.knowledge_retrieval'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = VaultMvpService(client: requestClient);

    final result = await service.retrievalQuery('architecture');
    expect(result, isA<ApiSuccess<List<VaultRetrievalHit>>>());
    final success = result as ApiSuccess<List<VaultRetrievalHit>>;
    expect(success.data.length, 1);
    expect(success.data.first.title, 'architecture.pdf');
    expect(success.data.first.score, 0.95);
  });
}
