import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/knowledge/models/project_knowledge.dart';
import 'package:frontend/modules/knowledge/services/project_knowledge_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'workspace_id': '1001',
    });
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('searches project knowledge through the generated endpoint', () async {
    http.Request? capturedRequest;
    final mockHttp = MockClient((request) async {
      capturedRequest = request;
      expect(request.method, 'POST');
      expect(request.url.path, '/agent/knowledge/projects/proj-42/search');

      return http.Response(
        jsonEncode({
          'data': {
            'items': [
              {
                'text': 'Our pricing strategy is SaaS tiered pricing.',
                'citations': [
                  {
                    'documentId': 'doc-123',
                    'versionId': 'ver-456',
                    'chunkId': 'chk-789',
                    'title': 'Pricing Strategy',
                    'excerpt': 'Our pricing strategy is SaaS tiered pricing.',
                  }
                ],
              }
            ],
            'citations': [
              {
                'documentId': 'doc-123',
                'versionId': 'ver-456',
                'chunkId': 'chk-789',
                'title': 'Pricing Strategy',
                'excerpt': 'Our pricing strategy is SaaS tiered pricing.',
              }
            ],
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-10T12:00:00Z',
            'sources': [{'kind': 'agent_db', 'ref': 'knowledge.projects'}],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = ProjectKnowledgeService(client: requestClient);

    final result = await service.search('proj-42', query: 'pricing', limit: 5);

    expect(result, isA<ApiSuccess<ProjectKnowledgeSearchResult>>());
    final success = result as ApiSuccess<ProjectKnowledgeSearchResult>;
    expect(success.data.citations.length, 1);
    final cit = success.data.citations.first;
    expect(cit.documentId, 'doc-123');
    expect(cit.versionId, 'ver-456');
    expect(cit.chunkId, 'chk-789');
    expect(cit.title, 'Pricing Strategy');
    expect(cit.excerpt, 'Our pricing strategy is SaaS tiered pricing.');

    expect(success.data.items.length, 1);
    expect(success.data.items.first.citations.first.documentId, 'doc-123');

    expect(capturedRequest, isNotNull);
    final body = jsonDecode(capturedRequest!.body) as Map<String, dynamic>;
    expect(body['query'], 'pricing');
    expect(body['limit'], 5);
  });

  test('returns ApiFailure when search returns 404 for foreign or not found project', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({'detail': 'not found'}),
        404,
        headers: {'content-type': 'application/json'},
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = ProjectKnowledgeService(client: requestClient);

    final result = await service.search('foreign-proj', query: 'pricing');
    expect(result, isA<ApiFailure<ProjectKnowledgeSearchResult>>());
  });
}
