import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/vault_controller.dart';
import 'vault_knowledge_studio_panel.dart';

class VaultFolderTreeSidebar extends StatelessWidget {
  final VaultController controller;

  const VaultFolderTreeSidebar({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 280,
      decoration: const BoxDecoration(
        color: Color(0xFF070C18),
        border: Border(
          right: BorderSide(color: Color(0xFF1E293B), width: 1),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Top Header
          Container(
            padding: const EdgeInsets.fromLTRB(16, 16, 12, 12),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: Color(0xFF1E293B), width: 1)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: const Color(0xFF00F0FF).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: const Color(0xFF00F0FF).withValues(alpha: 0.3),
                      width: 0.8,
                    ),
                  ),
                  child: const Icon(
                    Icons.folder_copy_rounded,
                    color: Color(0xFF00F0FF),
                    size: 16,
                  ),
                ),
                const SizedBox(width: 10),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'LƯU TRỮ (VAULT)',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 12.5,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.6,
                        ),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Thư mục tri thức Second Brain',
                        style: TextStyle(
                          color: Color(0xFF64748B),
                          fontSize: 10,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
                Obx(() => IconButton(
                      icon: Icon(
                        Icons.auto_awesome_rounded,
                        size: 18,
                        color: controller.showKnowledgeStudio.value
                            ? const Color(0xFF00F0FF)
                            : const Color(0xFF64748B),
                      ),
                      tooltip: 'Knowledge Studio',
                      onPressed: () => controller.showKnowledgeStudio.toggle(),
                    )),
                IconButton(
                  icon: const Icon(Icons.sync_rounded, size: 18, color: Color(0xFF94A3B8)),
                  tooltip: 'Đồng bộ tài liệu',
                  onPressed: controller.loadDocuments,
                ),
              ],
            ),
          ),

          // Search Input
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
            child: TextField(
              onChanged: (val) => controller.searchQuery.value = val,
              decoration: InputDecoration(
                hintText: 'Tìm kiếm tài liệu...',
                hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12.5),
                prefixIcon: const Icon(Icons.search_rounded, color: Color(0xFF38BDF8), size: 18),
                suffixIcon: Obx(() => controller.searchQuery.value.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear_rounded, size: 16, color: Color(0xFF94A3B8)),
                        onPressed: () => controller.searchQuery.value = '',
                      )
                    : const SizedBox.shrink()),
                filled: true,
                fillColor: const Color(0xFF0B1220),
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: Color(0xFF1E293B)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: Color(0xFF1E293B)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: Color(0xFF00F0FF), width: 1.0),
                ),
              ),
              style: const TextStyle(color: Colors.white, fontSize: 13),
            ),
          ),

          VaultKnowledgeStudioPanel(controller: controller),

          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 6),
            child: Row(
              children: [
                const Icon(Icons.account_tree_rounded, size: 13, color: Color(0xFF38BDF8)),
                const SizedBox(width: 6),
                const Text(
                  'CÂY THƯ MỤC',
                  style: TextStyle(
                    color: Color(0xFF38BDF8),
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                  ),
                ),
                const Spacer(),
                Obx(() => Text(
                      '${controller.documents.length} file',
                      style: const TextStyle(color: Color(0xFF64748B), fontSize: 10.5),
                    )),
              ],
            ),
          ),

          Expanded(
            child: Obx(() {
              if (controller.isLoading.value) {
                return const Center(
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF00F0FF)),
                  ),
                );
              }

              final totalCount = controller.documents.length;
              final selected = controller.selectedFolder.value;
              final treeRoot = controller.folderTree;

              return ListView(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                children: [
                  _buildFolderItem(
                    title: 'Tất cả tài liệu',
                    folderPath: 'all',
                    count: totalCount,
                    isSelected: selected == 'all',
                    icon: Icons.all_inbox_rounded,
                    level: 0,
                    hasChildren: false,
                    isExpanded: false,
                    onToggleExpand: null,
                  ),
                  const SizedBox(height: 4),
                  const Divider(color: Color(0xFF1E293B), height: 10),
                  const SizedBox(height: 4),

                  for (final entry in treeRoot.children.entries)
                    ..._buildFolderNodeTree(entry.value, level: 0, selectedFolder: selected),

                  if (treeRoot.fileCount > 0)
                    _buildFolderItem(
                      title: 'Thư mục gốc',
                      folderPath: 'root',
                      count: treeRoot.fileCount,
                      isSelected: selected == 'root',
                      icon: Icons.folder_rounded,
                      level: 0,
                      hasChildren: false,
                      isExpanded: false,
                      onToggleExpand: null,
                    ),
                ],
              );
            }),
          ),
        ],
      ),
    );
  }

  List<Widget> _buildFolderNodeTree(
    VaultFolderNode node, {
    required int level,
    required String selectedFolder,
  }) {
    final widgets = <Widget>[];
    final isSelected = selectedFolder == node.fullPath;
    final isExpanded = controller.isFolderExpanded(node.fullPath);
    final hasChildren = node.children.isNotEmpty;

    widgets.add(_buildFolderItem(
      title: node.name,
      folderPath: node.fullPath,
      count: node.fileCount,
      isSelected: isSelected,
      icon: isExpanded ? Icons.folder_open_rounded : Icons.folder_rounded,
      level: level,
      hasChildren: hasChildren,
      isExpanded: isExpanded,
      onToggleExpand: hasChildren ? () => controller.toggleFolderExpansion(node.fullPath) : null,
    ));

    if (hasChildren && isExpanded) {
      for (final child in node.children.values) {
        widgets.addAll(_buildFolderNodeTree(child, level: level + 1, selectedFolder: selectedFolder));
      }
    }

    return widgets;
  }

  Widget _buildFolderItem({
    required String title,
    required String folderPath,
    required int count,
    required bool isSelected,
    required IconData icon,
    required int level,
    required bool hasChildren,
    required bool isExpanded,
    required VoidCallback? onToggleExpand,
  }) {
    return Padding(
      padding: EdgeInsets.only(left: level * 14.0, bottom: 3),
      child: InkWell(
        onTap: () => controller.selectFolder(folderPath),
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFF0284C7).withValues(alpha: 0.22) : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: isSelected ? const Color(0xFF00F0FF).withValues(alpha: 0.6) : Colors.transparent,
              width: 1,
            ),
          ),
          child: Row(
            children: [
              if (hasChildren)
                InkWell(
                  onTap: onToggleExpand,
                  borderRadius: BorderRadius.circular(4),
                  child: Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: Icon(
                      isExpanded ? Icons.expand_more_rounded : Icons.chevron_right_rounded,
                      size: 15,
                      color: const Color(0xFF94A3B8),
                    ),
                  ),
                )
              else
                const SizedBox(width: 4),
              Icon(icon, size: 16, color: isSelected ? const Color(0xFF00F0FF) : const Color(0xFF38BDF8)),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    color: isSelected ? Colors.white : const Color(0xFFE2E8F0),
                    fontSize: 12.5,
                    fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                decoration: BoxDecoration(
                  color: isSelected ? const Color(0xFF00F0FF).withValues(alpha: 0.2) : const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: isSelected ? const Color(0xFF00F0FF).withValues(alpha: 0.4) : const Color(0xFF1E293B),
                    width: 0.8,
                  ),
                ),
                child: Text(
                  '$count',
                  style: TextStyle(
                    color: isSelected ? const Color(0xFF7DD3FC) : const Color(0xFF64748B),
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
