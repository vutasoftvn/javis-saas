import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/vault/services/vault_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'workspace-1',
      'brain_id': 'brain-1',
    });
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('getDocuments', () {
    test('returns the documents list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/vault/brain-1/documents');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({
            'documents': [
              {'path': 'notes/plan.md', 'kind': 'wiki'},
            ],
          }),
          200,
        );
      });

      final docs = await VaultService().getDocuments();

      expect(docs, hasLength(1));
      expect(docs.first['path'], 'notes/plan.md');
    });

    test('returns an empty list when brain_id is missing', () async {
      SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a brain_id');
      });

      final docs = await VaultService().getDocuments();

      expect(docs, isEmpty);
    });

    test('returns an empty list when the request fails', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final docs = await VaultService().getDocuments();

      expect(docs, isEmpty);
    });
  });

  group('getDocumentContent', () {
    test('URL-encodes the document path', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/vault/brain-1/documents/notes%2Fplan.md');
        return http.Response(jsonEncode({'path': 'notes/plan.md', 'content': 'hello'}), 200);
      });

      final doc = await VaultService().getDocumentContent('notes/plan.md');

      expect(doc?['content'], 'hello');
    });

    test('returns null on a non-200 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('not found', 404));

      final doc = await VaultService().getDocumentContent('missing.md');

      expect(doc, isNull);
    });
  });

  group('getKnowledgeObjects', () {
    test('appends type and status filters when provided', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['type'], 'note');
        expect(request.url.queryParameters['status'], 'approved');
        return http.Response(jsonEncode({'items': []}), 200);
      });

      await VaultService().getKnowledgeObjects(type: 'note', status: 'approved');
    });

    test('returns an empty list when the request throws', () async {
      ApiClient.client = MockClient((request) async => throw Exception('network down'));

      final items = await VaultService().getKnowledgeObjects();

      expect(items, isEmpty);
    });
  });

  group('promoteKnowledgeObject', () {
    test('posts the target status and returns true on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/vault/brain-1/knowledge/obj-1/promote');
        expect(jsonDecode(request.body)['target_status'], 'archived');
        return http.Response('{}', 200);
      });

      final ok = await VaultService().promoteKnowledgeObject('obj-1', targetStatus: 'archived');

      expect(ok, isTrue);
    });

    test('returns false on a non-200 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('forbidden', 403));

      final ok = await VaultService().promoteKnowledgeObject('obj-1');

      expect(ok, isFalse);
    });
  });

  group('getGraph', () {
    test('returns the nodes/edges payload on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/vault/brain-1/graph');
        return http.Response(
          jsonEncode({
            'nodes': [
              {'id': 'a.md', 'label': 'a.md'},
            ],
            'edges': [],
          }),
          200,
        );
      });

      final graph = await VaultService().getGraph();

      expect(graph['nodes'], hasLength(1));
    });

    test('returns an empty graph when brain_id is missing', () async {
      SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a brain_id');
      });

      final graph = await VaultService().getGraph();

      expect(graph, {'nodes': [], 'edges': []});
    });
  });
}
