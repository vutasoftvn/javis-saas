import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';
import '../controllers/vault_controller.dart';

class VaultView extends GetView<VaultController> {
  const VaultView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<VaultController>()) {
      Get.put(VaultController());
    }

    return Container(
      color: const Color(0xFF040711),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // ── 1. SIDEBAR PHỤ: CÂY THƯ MỤC CHA -> CON (Bên trái) ─────────────
          _buildFolderOnlySidebar(),

          // ── 2. KHUNG NỘI DUNG CHÍNH (Bên phải) ────────────────────────────
          Expanded(
            child: Obx(() {
              if (controller.isViewingDocumentDetail) {
                return _buildDocumentDetailView(context);
              } else {
                return _buildFolderFilesListView(context);
              }
            }),
          ),
        ],
      ),
    );
  }

  // ── 1. SIDEBAR PHỤ (Chỉ hiển thị cây thư mục cha -> con) ───────────────────
  Widget _buildFolderOnlySidebar() {
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
                // Knowledge Studio Toggle
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
                // Sync Button
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

          // Knowledge Studio Collapsible Section
          _buildKnowledgeStudioCollapsible(),

          // Section Title
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

          // Hierarchical Folder Tree List
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
                  // 1. "Tất cả tài liệu" Item
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

                  // 2. Hierarchical Root Children (e.g. mID -> roadmaps)
                  for (final entry in treeRoot.children.entries)
                    ..._buildFolderNodeTree(entry.value, level: 0, selectedFolder: selected),

                  // 3. Root Files Folder (if any files in root)
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

  // ── RECURSIVE FOLDER NODE TREE RENDERER ──────────────────────────────────────
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
      onToggleExpand: hasChildren
          ? () => controller.toggleFolderExpansion(node.fullPath)
          : null,
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
            color: isSelected
                ? const Color(0xFF0284C7).withValues(alpha: 0.22)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: isSelected
                  ? const Color(0xFF00F0FF).withValues(alpha: 0.6)
                  : Colors.transparent,
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
              Icon(
                icon,
                size: 16,
                color: isSelected ? const Color(0xFF00F0FF) : const Color(0xFF38BDF8),
              ),
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
                  color: isSelected
                      ? const Color(0xFF00F0FF).withValues(alpha: 0.2)
                      : const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: isSelected
                        ? const Color(0xFF00F0FF).withValues(alpha: 0.4)
                        : const Color(0xFF1E293B),
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

  // ── 2A. VIEW DANH SÁCH FILE TRONG THƯ MỤC (Folder Files List & Grid) ────────
  Widget _buildFolderFilesListView(BuildContext context) {
    final selected = controller.selectedFolder.value;
    final docs = controller.filteredDocuments;
    final displayTitle = selected == 'all'
        ? 'Tất cả tài liệu'
        : (selected == 'root' ? 'Thư mục gốc' : selected);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Folder Header Top Bar with View Mode Switcher
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          decoration: const BoxDecoration(
            color: Color(0xFF070C18),
            border: Border(bottom: BorderSide(color: Color(0xFF1E293B), width: 1)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFF0284C7).withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.4)),
                ),
                child: const Icon(Icons.folder_open_rounded, size: 18, color: Color(0xFF38BDF8)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      displayTitle,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15.5,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${docs.length} tài liệu trong thư mục này',
                      style: const TextStyle(color: Color(0xFF64748B), fontSize: 11.5),
                    ),
                  ],
                ),
              ),

              // View Mode Switcher Buttons (ListView & GridView with LocalStorage persistence)
              Obx(() {
                final isList = controller.viewMode.value == 'list';
                return Container(
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // List View Button
                      InkWell(
                        onTap: () => controller.setViewMode('list'),
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: isList ? const Color(0xFF0284C7).withValues(alpha: 0.25) : Colors.transparent,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: isList ? const Color(0xFF38BDF8).withValues(alpha: 0.6) : Colors.transparent,
                              width: 1,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                Icons.view_headline_rounded,
                                size: 16,
                                color: isList ? const Color(0xFF38BDF8) : const Color(0xFF64748B),
                              ),
                              const SizedBox(width: 5),
                              Text(
                                'Danh sách',
                                style: TextStyle(
                                  fontSize: 11.5,
                                  fontWeight: isList ? FontWeight.w700 : FontWeight.w500,
                                  color: isList ? Colors.white : const Color(0xFF94A3B8),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 4),

                      // Grid View Button
                      InkWell(
                        onTap: () => controller.setViewMode('grid'),
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: !isList ? const Color(0xFF0284C7).withValues(alpha: 0.25) : Colors.transparent,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: !isList ? const Color(0xFF38BDF8).withValues(alpha: 0.6) : Colors.transparent,
                              width: 1,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                Icons.grid_view_rounded,
                                size: 15,
                                color: !isList ? const Color(0xFF38BDF8) : const Color(0xFF64748B),
                              ),
                              const SizedBox(width: 5),
                              Text(
                                'Lưới card',
                                style: TextStyle(
                                  fontSize: 11.5,
                                  fontWeight: !isList ? FontWeight.w700 : FontWeight.w500,
                                  color: !isList ? Colors.white : const Color(0xFF94A3B8),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ],
          ),
        ),

        // Files List / Grid Area
        Expanded(
          child: docs.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0B1220),
                          shape: BoxShape.circle,
                          border: Border.all(color: const Color(0xFF1E293B)),
                        ),
                        child: const Icon(
                          Icons.folder_off_outlined,
                          size: 40,
                          color: Color(0xFF64748B),
                        ),
                      ),
                      const SizedBox(height: 14),
                      const Text(
                        'Thư mục này hiện chưa có file nào',
                        style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13.5),
                      ),
                    ],
                  ),
                )
              : Obx(() {
                  if (controller.viewMode.value == 'grid') {
                    return _buildFilesGrid(docs);
                  } else {
                    return _buildFilesList(docs);
                  }
                }),
        ),
      ],
    );
  }

  // ── 2A-1. CHẾ ĐỘ LIST VIEW (Hiển thị đầy đủ nội dung trên 1 dòng trải dài) ───
  Widget _buildFilesList(List<dynamic> docs) {
    return ListView.separated(
      padding: const EdgeInsets.all(24),
      itemCount: docs.length,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final doc = docs[index];
        final String path = doc['path'] ?? '';
        final String fileName = controller.getFileName(path);
        final String folder = controller.getFolderName(path);
        final String kind = (doc['kind'] as String?)?.toUpperCase() ?? 'MARKDOWN';
        final String updatedAt = doc['updated_at']?.toString().split('T').first ?? '';

        return InkWell(
          onTap: () => controller.openDocument(path),
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            decoration: BoxDecoration(
              color: const Color(0xFF0B1220),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF1E293B)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.25),
                  blurRadius: 6,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Row(
              children: [
                // 1. File Icon
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0284C7).withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: const Color(0xFF38BDF8).withValues(alpha: 0.35),
                      width: 0.8,
                    ),
                  ),
                  child: const Icon(
                    Icons.description_rounded,
                    color: Color(0xFF38BDF8),
                    size: 20,
                  ),
                ),
                const SizedBox(width: 16),

                // 2. Tên file (Trải rộng)
                Expanded(
                  flex: 4,
                  child: Text(
                    fileName,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 16),

                // 3. Đường dẫn Thư mục
                Expanded(
                  flex: 3,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.folder_outlined, size: 13, color: Color(0xFF64748B)),
                      const SizedBox(width: 6),
                      Flexible(
                        child: Text(
                          folder == 'root' ? 'Gốc' : folder,
                          style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),

                // 4. Ngày cập nhật
                if (updatedAt.isNotEmpty)
                  Expanded(
                    flex: 2,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.access_time_rounded, size: 13, color: Color(0xFF64748B)),
                        const SizedBox(width: 6),
                        Text(
                          updatedAt,
                          style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                const SizedBox(width: 16),

                // 5. Loại tài liệu (Kind Badge)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3.5),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0xFF334155), width: 0.8),
                  ),
                  child: Text(
                    kind,
                    style: const TextStyle(
                      color: Color(0xFF38BDF8),
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
                const SizedBox(width: 16),

                // 6. Action Arrow
                const Icon(
                  Icons.arrow_forward_ios_rounded,
                  size: 14,
                  color: Color(0xFF00F0FF),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  // ── 2A-2. CHẾ ĐỘ GRID VIEW (Card Responsive) ────────────────────────────────
  Widget _buildFilesGrid(List<dynamic> docs) {
    return GridView.builder(
      padding: const EdgeInsets.all(24),
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 280,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
        childAspectRatio: 1.25,
      ),
      itemCount: docs.length,
      itemBuilder: (context, index) {
        final doc = docs[index];
        final String path = doc['path'] ?? '';
        final String fileName = controller.getFileName(path);
        final String folder = controller.getFolderName(path);
        final String kind = (doc['kind'] as String?)?.toUpperCase() ?? 'MARKDOWN';
        final String updatedAt = doc['updated_at']?.toString().split('T').first ?? '';

        return InkWell(
          onTap: () => controller.openDocument(path),
          borderRadius: BorderRadius.circular(14),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF0B1220),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0xFF1E293B)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.25),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Top: Icon + Kind Badge
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0284C7).withValues(alpha: 0.18),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: const Color(0xFF38BDF8).withValues(alpha: 0.35),
                          width: 0.8,
                        ),
                      ),
                      child: const Icon(
                        Icons.description_rounded,
                        color: Color(0xFF38BDF8),
                        size: 20,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        kind,
                        style: const TextStyle(
                          color: Color(0xFF38BDF8),
                          fontSize: 9.5,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.4,
                        ),
                      ),
                    ),
                  ],
                ),

                // Middle: File Name
                Text(
                  fileName,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13.5,
                    fontWeight: FontWeight.w700,
                    height: 1.35,
                  ),
                ),

                // Bottom: Folder & Update Time
                Row(
                  children: [
                    const Icon(Icons.folder_outlined, size: 12, color: Color(0xFF64748B)),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        folder == 'root' ? 'Gốc' : folder,
                        style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (updatedAt.isNotEmpty)
                      Text(
                        updatedAt,
                        style: const TextStyle(color: Color(0xFF64748B), fontSize: 10.5),
                      ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  // ── 2B. VIEW CHI TIẾT TÀI LIỆU MARKDOWN (Document Detail View) ──────────────
  Widget _buildDocumentDetailView(BuildContext context) {
    final docPath = controller.selectedDocumentPath.value ?? '';
    final folder = controller.getFolderName(docPath);
    final fileName = controller.getFileName(docPath);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Navigation Header Bar (Back button + Clickable Breadcrumbs + Actions)
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          decoration: const BoxDecoration(
            color: Color(0xFF070C18),
            border: Border(bottom: BorderSide(color: Color(0xFF1E293B), width: 1)),
          ),
          child: Row(
            children: [
              // Back Button
              Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: controller.backToFolderList,
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0F172A),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFF1E293B)),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.arrow_back_rounded, size: 15, color: Color(0xFF00F0FF)),
                        SizedBox(width: 6),
                        Text(
                          'Quay lại thư mục',
                          style: TextStyle(
                            color: Color(0xFFE2E8F0),
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 14),

              // Clickable Breadcrumbs
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      InkWell(
                        onTap: () => controller.selectFolder('all'),
                        child: const Text(
                          'Vault',
                          style: TextStyle(color: Color(0xFF64748B), fontSize: 13, fontWeight: FontWeight.w600),
                        ),
                      ),
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 6),
                        child: Icon(Icons.chevron_right_rounded, size: 14, color: Color(0xFF475569)),
                      ),
                      if (folder != 'root') ...[
                        InkWell(
                          onTap: () => controller.selectFolder(folder),
                          child: Text(
                            folder,
                            style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 13, fontWeight: FontWeight.w600),
                          ),
                        ),
                        const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 6),
                          child: Icon(Icons.chevron_right_rounded, size: 14, color: Color(0xFF475569)),
                        ),
                      ],
                      Text(
                        fileName,
                        style: const TextStyle(color: Colors.white, fontSize: 13.5, fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                ),
              ),

              // Action Toolbar
              // 1. Sao chép Markdown
              InkWell(
                onTap: () {
                  final content = controller.selectedDocumentContent.value ?? '';
                  if (content.isNotEmpty) {
                    Clipboard.setData(ClipboardData(text: content));
                    Get.snackbar(
                      'Đã sao chép',
                      'Nội dung Markdown đã được chép vào Clipboard',
                      backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.2),
                      colorText: const Color(0xFF10B981),
                      duration: const Duration(seconds: 2),
                    );
                  }
                },
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.copy_all_rounded, size: 15, color: Color(0xFF94A3B8)),
                      SizedBox(width: 5),
                      Text(
                        'Sao chép',
                        style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 8),

              // 2. Chỉnh sửa / Lưu
              Obx(() {
                final isEditing = controller.isEditing.value;
                return InkWell(
                  onTap: () {
                    if (isEditing) {
                      controller.saveDocument();
                    } else {
                      controller.toggleEdit();
                    }
                  },
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      gradient: isEditing
                          ? const LinearGradient(colors: [Color(0xFF059669), Color(0xFF10B981)])
                          : null,
                      color: isEditing ? null : const Color(0xFF0284C7).withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: isEditing ? const Color(0xFF10B981) : const Color(0xFF38BDF8),
                        width: 1,
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          isEditing ? Icons.save_rounded : Icons.edit_rounded,
                          size: 15,
                          color: Colors.white,
                        ),
                        const SizedBox(width: 5),
                        Text(
                          isEditing ? 'Lưu' : 'Chỉnh sửa',
                          style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700),
                        ),
                      ],
                    ),
                  ),
                );
              }),
            ],
          ),
        ),

        // Document Content Body
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 28),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 960),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Obx(() {
                      if (controller.isEditing.value) {
                        return Container(
                          decoration: BoxDecoration(
                            color: const Color(0xFF080D1A),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: const Color(0xFF1E293B)),
                          ),
                          padding: const EdgeInsets.all(20),
                          child: TextField(
                            controller: controller.textController,
                            maxLines: null,
                            style: const TextStyle(
                              fontSize: 14.5,
                              height: 1.65,
                              fontFamily: 'monospace',
                              color: Color(0xFFE2E8F0),
                            ),
                            decoration: const InputDecoration(
                              border: InputBorder.none,
                              hintText: 'Nhập nội dung tài liệu Markdown...',
                              hintStyle: TextStyle(color: Color(0xFF64748B)),
                            ),
                          ),
                        );
                      }

                      final rawContent = controller.selectedDocumentContent.value ?? '';
                      if (rawContent.isEmpty) {
                        return const Center(
                          child: Padding(
                            padding: EdgeInsets.symmetric(vertical: 40),
                            child: Text(
                              'Tài liệu rỗng',
                              style: TextStyle(color: Color(0xFF64748B), fontStyle: FontStyle.italic),
                            ),
                          ),
                        );
                      }

                      // Formatted Obsidian Markdown Body
                      return MarkdownBody(
                        data: rawContent,
                        selectable: true,
                        onTapLink: (text, href, title) {
                          if (href != null) {
                            if (href.startsWith('http://') || href.startsWith('https://')) {
                              final uri = Uri.tryParse(href);
                              if (uri != null) {
                                launchUrl(uri, mode: LaunchMode.externalApplication);
                              }
                            } else {
                              controller.openDocument(href);
                            }
                          }
                        },
                        styleSheet: MarkdownStyleSheet(
                          h1: const TextStyle(
                            color: Colors.white,
                            fontSize: 22,
                            fontWeight: FontWeight.w800,
                            height: 1.4,
                            letterSpacing: -0.5,
                          ),
                          h1Padding: const EdgeInsets.only(top: 10, bottom: 16),
                          h2: const TextStyle(
                            color: Color(0xFF38BDF8),
                            fontSize: 17.5,
                            fontWeight: FontWeight.w700,
                            height: 1.4,
                          ),
                          h2Padding: const EdgeInsets.only(top: 20, bottom: 10),
                          h3: const TextStyle(
                            color: Color(0xFFF1F5F9),
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            height: 1.4,
                          ),
                          h3Padding: const EdgeInsets.only(top: 14, bottom: 8),
                          p: const TextStyle(
                            color: Color(0xFFCBD5E1),
                            fontSize: 14.5,
                            height: 1.65,
                          ),
                          pPadding: const EdgeInsets.only(bottom: 12),
                          strong: const TextStyle(
                            color: Color(0xFFF8FAFC),
                            fontWeight: FontWeight.w700,
                          ),
                          em: const TextStyle(
                            color: Color(0xFF94A3B8),
                            fontStyle: FontStyle.italic,
                          ),
                          code: const TextStyle(
                            color: Color(0xFF38BDF8),
                            backgroundColor: Color(0xFF1E293B),
                            fontFamily: 'monospace',
                            fontSize: 13,
                          ),
                          codeblockDecoration: BoxDecoration(
                            color: const Color(0xFF080D1A),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: const Color(0xFF1E293B)),
                          ),
                          codeblockPadding: const EdgeInsets.all(14),
                          blockquote: const TextStyle(
                            color: Color(0xFFCBD5E1),
                            fontSize: 14,
                            height: 1.5,
                            fontStyle: FontStyle.italic,
                          ),
                          blockquoteDecoration: BoxDecoration(
                            color: const Color(0xFF00F0FF).withValues(alpha: 0.05),
                            borderRadius: BorderRadius.circular(6),
                            border: const Border(
                              left: BorderSide(color: Color(0xFF00F0FF), width: 3.5),
                            ),
                          ),
                          blockquotePadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          listBullet: const TextStyle(
                            color: Color(0xFF00F0FF),
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                          ),
                          horizontalRuleDecoration: BoxDecoration(
                            border: Border(
                              top: BorderSide(
                                color: const Color(0xFF334155).withValues(alpha: 0.8),
                                width: 1,
                              ),
                            ),
                          ),
                          tableHead: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 13.5,
                          ),
                          tableBody: const TextStyle(
                            color: Color(0xFFCBD5E1),
                            fontSize: 13.5,
                          ),
                          tableBorder: TableBorder.all(
                            color: const Color(0xFF1E293B),
                            width: 1,
                          ),
                          tableCellsPadding: const EdgeInsets.all(10),
                        ),
                      );
                    }),
                    const SizedBox(height: 32),
                    const Divider(color: Color(0xFF1E293B)),
                    const SizedBox(height: 16),

                    // Backlinks & Related Nodes Section
                    _buildBacklinksSection(),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  // ── KNOWLEDGE STUDIO COLLAPSIBLE SECTION ────────────────────────────────────
  Widget _buildKnowledgeStudioCollapsible() {
    return Obx(() {
      if (!controller.showKnowledgeStudio.value) {
        return const SizedBox.shrink();
      }

      return Container(
        margin: const EdgeInsets.fromLTRB(10, 0, 10, 8),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: const Color(0xFF0B1220),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: const Color(0xFF1E293B)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.auto_awesome_rounded, size: 13, color: Color(0xFF00F0FF)),
                const SizedBox(width: 6),
                const Text(
                  'Knowledge Objects',
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                const Spacer(),
                Text(
                  '${controller.knowledgeObjects.length} mục',
                  style: const TextStyle(fontSize: 10, color: Color(0xFF64748B)),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 4,
              runSpacing: 4,
              children: [
                _filterChip('Tất cả', controller.selectedKnowledgeType.value.isEmpty, () {
                  controller.selectedKnowledgeType.value = '';
                  controller.loadKnowledgeObjects();
                }),
                ...['note', 'research', 'decision', 'concept'].map((t) => _filterChip(
                      t,
                      controller.selectedKnowledgeType.value == t,
                      () {
                        controller.selectedKnowledgeType.value = t;
                        controller.loadKnowledgeObjects();
                      },
                    )),
              ],
            ),
          ],
        ),
      );
    });
  }

  Widget _filterChip(String label, bool selected, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: selected ? const Color(0xFF00F0FF).withValues(alpha: 0.18) : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected ? const Color(0xFF00F0FF) : const Color(0xFF1E293B),
            width: 0.8,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 9.5,
            color: selected ? Colors.white : const Color(0xFF94A3B8),
            fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
      ),
    );
  }

  // ── BACKLINKS SECTION ───────────────────────────────────────────────────────
  Widget _buildBacklinksSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.hub_rounded, size: 16, color: Color(0xFF00F0FF)),
            SizedBox(width: 8),
            Text(
              'Liên kết hai chiều (Obsidian Wikilinks [[...]])',
              style: TextStyle(
                fontSize: 13.5,
                fontWeight: FontWeight.w700,
                color: Color(0xFF38BDF8),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Obx(() {
          if (controller.backlinks.isEmpty) {
            return const Text(
              'Chưa có tài liệu nào liên kết ngược tới file này qua cú pháp [[...]]',
              style: TextStyle(fontSize: 12.5, color: Color(0xFF64748B), fontStyle: FontStyle.italic),
            );
          }
          return Wrap(
            spacing: 8,
            runSpacing: 8,
            children: controller.backlinks.map((link) {
              final title = link['source_title'] as String? ?? 'Tài liệu liên quan';
              final type = link['source_type'] as String? ?? 'note';
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFF0B1220),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF1E293B)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.link_rounded, size: 14, color: Color(0xFF00F0FF)),
                    const SizedBox(width: 8),
                    Text(
                      title,
                      style: const TextStyle(fontSize: 12.5, color: Colors.white, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      type.toUpperCase(),
                      style: const TextStyle(fontSize: 9.5, color: Color(0xFF64748B), fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              );
            }).toList(),
          );
        }),
      ],
    );
  }
}
