import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/data/services/vault_service.dart';
import 'package:frontend/modules/graph/views/graph_view.dart';

class _FakeVaultService implements VaultService {
  _FakeVaultService(this._graph);

  final Map<String, dynamic> _graph;

  @override
  Future<Map<String, dynamic>> getGraph() async => _graph;

  @override
  Future<List<dynamic>> getBacklinks(String objectId) async => [];

  @override
  Future<Map<String, dynamic>?> getDocumentContent(String path) async => null;

  @override
  Future<List<dynamic>> getDocuments() async => [];

  @override
  Future<List<dynamic>> getKnowledgeObjects({String? type, String? status}) async => [];

  @override
  Future<bool> promoteKnowledgeObject(String objectId, {String targetStatus = 'approved'}) async => false;

  @override
  Future<void> writeDocument(String path, String content, {String? baseRevisionId, String kind = 'wiki'}) async {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  tearDown(() {
    Get.reset();
  });

  test('loadGraph populates nodes and edges from VaultService', () async {
    final controller = GraphController(
      vaultService: _FakeVaultService({
        'nodes': [
          {'id': 'a.md', 'label': 'a.md'},
          {'id': 'b.md', 'label': 'b.md'},
        ],
        'edges': [
          {'source': 'a.md', 'target': 'b.md'},
        ],
      }),
    );

    await controller.loadGraph();

    expect(controller.isLoading.value, isFalse);
    expect(controller.nodes, hasLength(2));
    expect(controller.linksFor('a.md'), ['b.md']);
    expect(controller.linksFor('b.md'), isEmpty);
  });

  test('loadGraph leaves nodes empty when VaultService returns nothing', () async {
    final controller = GraphController(vaultService: _FakeVaultService({}));

    await controller.loadGraph();

    expect(controller.nodes, isEmpty);
    expect(controller.edges, isEmpty);
  });
}
