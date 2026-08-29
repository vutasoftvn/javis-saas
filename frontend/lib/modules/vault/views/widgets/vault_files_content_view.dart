import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/vault_controller.dart';

class VaultFilesContentView extends StatelessWidget {
  final VaultController controller;

  const VaultFilesContentView({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    final selected = controller.selectedFolder.value;
    final docs = controller.filteredDocuments;
    final displayTitle = selected == 'all'
        ? 'Tất cả tài liệu'
        : (selected == 'root' ? 'Thư mục gốc' : selected);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Folder Header Top Bar
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

              // View Mode Switcher
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

        // Files Area
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
                        child: const Icon(Icons.folder_off_outlined, size: 40, color: Color(0xFF64748B)),
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
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0284C7).withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.35), width: 0.8),
                  ),
                  child: const Icon(Icons.description_rounded, color: Color(0xFF38BDF8), size: 20),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        fileName,
                        style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w700),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          const Icon(Icons.folder_outlined, size: 12, color: Color(0xFF64748B)),
                          const SizedBox(width: 4),
                          Text(folder == 'root' ? 'Gốc' : folder, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11.5)),
                          const SizedBox(width: 14),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(color: const Color(0xFF1E293B), borderRadius: BorderRadius.circular(4)),
                            child: Text(kind, style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 9.5, fontWeight: FontWeight.bold)),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                if (updatedAt.isNotEmpty)
                  Text(updatedAt, style: const TextStyle(color: Color(0xFF64748B), fontSize: 11.5)),
                const SizedBox(width: 12),
                const Icon(Icons.chevron_right_rounded, color: Color(0xFF475569), size: 18),
              ],
            ),
          ),
        );
      },
    );
  }

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
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0284C7).withValues(alpha: 0.18),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.35), width: 0.8),
                      ),
                      child: const Icon(Icons.description_rounded, color: Color(0xFF38BDF8), size: 20),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                      decoration: BoxDecoration(color: const Color(0xFF1E293B), borderRadius: BorderRadius.circular(6)),
                      child: Text(kind, style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 9.5, fontWeight: FontWeight.w700, letterSpacing: 0.4)),
                    ),
                  ],
                ),
                Text(
                  fileName,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Colors.white, fontSize: 13.5, fontWeight: FontWeight.w700, height: 1.35),
                ),
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
                      Text(updatedAt, style: const TextStyle(color: Color(0xFF64748B), fontSize: 10.5)),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
