import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../../../data/services/vault_service.dart';

class GraphController extends GetxController {
  GraphController({VaultService? vaultService}) : _vaultService = vaultService ?? VaultService();

  final VaultService _vaultService;

  final nodes = <Map<String, dynamic>>[].obs;
  final edges = <Map<String, dynamic>>[].obs;
  final isLoading = true.obs;

  @override
  void onInit() {
    super.onInit();
    loadGraph();
  }

  Future<void> loadGraph() async {
    isLoading.value = true;
    final graph = await _vaultService.getGraph();
    nodes.value = (graph['nodes'] as List? ?? []).cast<Map<String, dynamic>>();
    edges.value = (graph['edges'] as List? ?? []).cast<Map<String, dynamic>>();
    isLoading.value = false;
  }

  List<String> linksFor(String nodeId) => edges
      .where((e) => e['source'] == nodeId)
      .map((e) => e['target'] as String)
      .toList();
}

class GraphViewPage extends GetView<GraphController> {
  const GraphViewPage({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<GraphController>()) {
      Get.put(GraphController());
    }

    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      appBar: AppBar(
        title: const Text('Knowledge Graph'),
        backgroundColor: Colors.transparent,
      ),
      body: Obx(() {
        if (controller.isLoading.value) {
          return const Center(child: CircularProgressIndicator(color: AppTheme.primary));
        }

        if (controller.nodes.isEmpty) {
          return Center(
            child: Container(
              padding: const EdgeInsets.all(32),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
              ),
              child: const Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.hub_rounded, color: AppTheme.primaryLight, size: 48),
                  SizedBox(height: 16),
                  Text(
                    'Chưa có liên kết tri thức nào',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Thêm [[wikilink]] giữa các tài liệu trong Vault để hiển thị đồ thị liên kết tại đây.',
                    style: TextStyle(color: AppTheme.textMutedDark, fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          );
        }

        return RefreshIndicator(
          onRefresh: controller.loadGraph,
          child: ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: controller.nodes.length,
            separatorBuilder: (context, index) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final node = controller.nodes[index];
              final nodeId = node['id'] as String;
              final links = controller.linksFor(nodeId);
              return Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceDark,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.description_outlined, color: AppTheme.primaryLight, size: 18),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            (node['label'] as String?) ?? nodeId,
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                          ),
                        ),
                      ],
                    ),
                    if (links.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: links
                            .map(
                              (target) => Chip(
                                label: Text(target, style: const TextStyle(fontSize: 12)),
                                backgroundColor: AppTheme.primary.withValues(alpha: 0.12),
                                side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.3)),
                              ),
                            )
                            .toList(),
                      ),
                    ],
                  ],
                ),
              );
            },
          ),
        );
      }),
    );
  }
}
