import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/vault/models/vault_document.dart';
import 'package:frontend/modules/vault/services/vault_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('createDocument decodes the MvpSuccess envelope', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/agent/vault/documents');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['title'], 'Quarterly plan');

      return http.Response(
        jsonEncode({
          'data': {
            'document_id': 'doc_1',
            'upload_id': 'doc_1',
            'upload_url': '/agent/vault/uploads/doc_1/content?workspace_id=ws_1001&secret=abc',
            'expires_at': '2026-09-07T12:00:00.000Z',
            'max_bytes': 10485760,
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-07T11:00:00.000Z',
            'sources': [
              {'kind': 'agent_db', 'ref': 'vault.documents'},
            ],
          },
        }),
        200,
      );
    });

    final service = VaultService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.createDocument(title: 'Quarterly plan', mediaType: 'text/plain');

    expect(result, isA<ApiSuccess<VaultDocumentUpload>>());
    final upload = (result as ApiSuccess<VaultDocumentUpload>).data;
    expect(upload.uploadId, 'doc_1');
    expect(upload.uploadUrl, contains('/agent/vault/uploads/'));
  });

  test('upload uses the opaque local upload URL from the server', () async {
    http.BaseRequest? capturedRequest;
    final recordedBytes = <int>[];

    final realClient = ApiClient.client;
    ApiClient.client = MockClient((request) async {
      capturedRequest = request;
      recordedBytes.addAll(request.bodyBytes);
      return http.Response('', 204);
    });
    addTearDown(() => ApiClient.client = realClient);

    final service = VaultService();
    final ok = await service.uploadContent(
      '/agent/vault/uploads/doc_1/content?workspace_id=ws_1001&secret=abc',
      utf8.encode('quarter plan content'),
    );

    expect(ok, isTrue);
    expect(capturedRequest, isNotNull);
    expect(capturedRequest!.method, 'PUT');
    expect(capturedRequest!.url.path, contains('/agent/vault/uploads/'));
    expect(utf8.decode(recordedBytes), 'quarter plan content');
  });

  test('listDocuments decodes the document list with action grants', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/agent/vault/documents');
      return http.Response(
        jsonEncode({
          'data': [
            {
              'document_id': 'doc_1',
              'workspace_id': 'ws_1001',
              'title': 'Handbook',
              'kind': 'document',
              'state': 'PUBLISHED',
              'current_version_id': 'v1',
              'knowledge_source_id': null,
              'created_by': 'user_1',
              'created_at': '2026-09-01T00:00:00.000Z',
              'updated_at': '2026-09-01T00:00:00.000Z',
              'can_review': false,
              'can_publish': false,
              'can_manage': true,
            },
          ],
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-07T11:00:00.000Z',
            'sources': [
              {'kind': 'agent_db', 'ref': 'vault.documents'},
            ],
          },
        }),
        200,
      );
    });

    final service = VaultService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.listDocuments();

    expect(result, isA<ApiSuccess<List<VaultDocument>>>());
    final docs = (result as ApiSuccess<List<VaultDocument>>).data;
    expect(docs.length, 1);
    expect(docs.first.title, 'Handbook');
    expect(docs.first.canManage, isTrue);
    expect(docs.first.state, VaultDocumentState.published);
  });

  test('purgeDocument surfaces a 409 legal-hold failure truthfully', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, contains('/purge'));
      return http.Response(jsonEncode({'detail': 'document is under legal hold'}), 409);
    });

    final service = VaultService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.purgeDocument('doc_1');

    expect(result, isA<ApiFailure<VaultArchiveOrPurgeResult>>());
    expect((result as ApiFailure<VaultArchiveOrPurgeResult>).failure.code, ApiFailureCode.conflict);
  });
}
