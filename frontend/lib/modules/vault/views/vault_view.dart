import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/vault_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/glassmorphism.dart';

import '../../../core/widgets/floating_app_bar.dart';

class VaultView extends GetView<VaultController> {
  const VaultView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<VaultController>()) {
      Get.put(VaultController());
    }

    return Container(
      color: Colors.transparent,
      child: Row(
        children: [
          // Main Content Area: Document Grid
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                JavisFloatingAppBar(
                  title: 'Lưu trữ (Vault)',
                  subtitle: 'Quản lý tài liệu tri thức Second Brain',
                  actions: [
                    Container(
                      decoration: const BoxDecoration(
                        color: AppTheme.primary,
                        shape: BoxShape.circle,
                      ),
                      child: IconButton(
                        tooltip: 'Đồng bộ tài liệu',
                        icon: const Icon(Icons.sync, color: Color(0xFF04070E), size: 20),
                        onPressed: controller.loadDocuments,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: TextField(
                    onChanged: (val) => controller.searchQuery.value = val,
                    decoration: InputDecoration(
                      hintText: 'Tìm kiếm tài liệu...',
                      prefixIcon: const Icon(Icons.search),
                      filled: true,
                      fillColor: AppTheme.surfaceDark,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppTheme.borderDark)),
                    ),
                    style: const TextStyle(color: AppTheme.textDark),
                  ),
                ),
                _buildKnowledgeStudioSection(),
                Expanded(
                  child: Obx(() {
                    if (controller.isLoading.value) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    if (controller.filteredDocuments.isEmpty) {
                      return const Center(
                        child: Text(
                          'Không tìm thấy tài liệu',
                          style: TextStyle(color: AppTheme.textMutedDark),
                        ),
                      );
                    }
                    
                    return GridView.builder(
                      padding: const EdgeInsets.all(24),
                      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                        maxCrossAxisExtent: 300,
                        crossAxisSpacing: 16,
                        mainAxisSpacing: 16,
                        childAspectRatio: 1.2,
                      ),
                      itemCount: controller.filteredDocuments.length,
                      itemBuilder: (context, index) {
                        final doc = controller.filteredDocuments[index];
                        final isWiki = doc['kind'] == 'wiki';
                        final String fileName = doc['path']?.split('/').last ?? 'Không rõ';
                        
                        return InkWell(
                          onTap: () => controller.openDocument(doc['path']),
                          borderRadius: BorderRadius.circular(16),
                          child: Glassmorphism(
                            blur: 15,
                            opacity: 0.15,
                            color: AppTheme.surfaceDark,
                            borderRadius: BorderRadius.circular(16),
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.all(16),
                                    decoration: BoxDecoration(
                                      color: isWiki ? AppTheme.primary.withValues(alpha: 0.1) : AppTheme.secondary.withValues(alpha: 0.1),
                                      shape: BoxShape.circle,
                                    ),
                                    child: Icon(
                                      isWiki ? Icons.article : Icons.insert_drive_file,
                                      size: 40,
                                      color: isWiki ? AppTheme.primaryLight : AppTheme.secondaryLight,
                                    ),
                                  ),
                                  const SizedBox(height: 16),
                                  Text(
                                    fileName,
                                    textAlign: TextAlign.center,
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      },
                    );
                  }),
                ),
              ],
            ),
          ),
          
          // Main Content Area: Document Viewer
          // Side Preview Pane
          Obx(() {
            if (!controller.isViewingDocument.value) {
              return const SizedBox.shrink();
            }

            return Container(
              width: 400,
              decoration: BoxDecoration(
                color: AppTheme.backgroundDark.withValues(alpha: 0.8),
                border: const Border(left: BorderSide(color: AppTheme.borderDark)),
              ),
              child: Glassmorphism(
                blur: 30,
                opacity: 0.4,
                color: AppTheme.surfaceDark,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                      decoration: const BoxDecoration(
                        border: Border(bottom: BorderSide(color: AppTheme.borderDark)),
                      ),
                      child: Row(
                        children: [
                          const Text('Xem trước', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                          const Spacer(),
                          Obx(() => IconButton(
                            icon: Icon(controller.isEditing.value ? Icons.save : Icons.edit),
                            onPressed: () {
                              if (controller.isEditing.value) {
                                controller.saveDocument();
                              } else {
                                controller.toggleEdit();
                              }
                            },
                          )),
                          IconButton(
                            icon: const Icon(Icons.close),
                            onPressed: controller.closeDocument,
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Obx(() => controller.isEditing.value 
                              ? TextField(
                                  controller: controller.textController,
                                  maxLines: null,
                                  style: const TextStyle(fontSize: 15, height: 1.6, color: AppTheme.textDark),
                                  decoration: const InputDecoration(border: InputBorder.none),
                                )
                              : Text(
                                  controller.selectedDocumentContent.value ?? '',
                                  style: const TextStyle(fontSize: 15, height: 1.6, color: AppTheme.textDark),
                                ),
                            ),
                            const SizedBox(height: 24),
                            const Divider(color: AppTheme.borderDark),
                            const SizedBox(height: 12),
                            // Backlinks Section (wikilinks graph)
                            const Text(
                              'Liên kết ngược (Backlinks)',
                              style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.primary),
                            ),
                            const SizedBox(height: 8),
                            Obx(() {
                              if (controller.backlinks.isEmpty) {
                                return const Text(
                                  'Chưa có tài liệu nào liên kết qua cú pháp [[...]]',
                                  style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                                );
                              }
                              return Column(
                                children: controller.backlinks.map((link) {
                                  final title = link['source_title'] as String? ?? 'Tài liệu liên quan';
                                  final type = link['source_type'] as String? ?? 'note';
                                  return Container(
                                    margin: const EdgeInsets.only(bottom: 6),
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF070C18),
                                      borderRadius: BorderRadius.circular(6),
                                      border: Border.all(color: const Color(0xFF1E293B)),
                                    ),
                                    child: Row(
                                      children: [
                                        const Icon(Icons.link, size: 14, color: Color(0xFF00F0FF)),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: Text(
                                            title,
                                            style: const TextStyle(fontSize: 12, color: Colors.white, fontWeight: FontWeight.w600),
                                          ),
                                        ),
                                        Text(
                                          type.toUpperCase(),
                                          style: const TextStyle(fontSize: 9, color: Color(0xFF64748B), fontWeight: FontWeight.bold),
                                        ),
                                      ],
                                    ),
                                  );
                                }).toList(),
                              );
                            }),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  static const List<String> _knowledgeTypes = ['note', 'research', 'decision', 'adr', 'lesson', 'concept'];
  static const List<String> _knowledgeStatuses = ['capture', 'candidate', 'approved', 'archived'];

  Widget _buildKnowledgeStudioSection() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppTheme.borderDark),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.hub_outlined, size: 16, color: AppTheme.primary),
                const SizedBox(width: 8),
                const Text(
                  'Tri thức có cấu trúc (Knowledge Studio)',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textDark),
                ),
                const Spacer(),
                Obx(() => Text(
                      '${controller.knowledgeObjects.length} mục',
                      style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                    )),
              ],
            ),
            const SizedBox(height: 10),
            Obx(() => Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    _filterChip('Tất cả loại', controller.selectedKnowledgeType.value.isEmpty, () {
                      controller.selectedKnowledgeType.value = '';
                      controller.loadKnowledgeObjects();
                    }),
                    ..._knowledgeTypes.map((t) => _filterChip(t, controller.selectedKnowledgeType.value == t, () {
                          controller.selectedKnowledgeType.value = t;
                          controller.loadKnowledgeObjects();
                        })),
                  ],
                )),
            const SizedBox(height: 6),
            Obx(() => Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    _filterChip('Tất cả trạng thái', controller.selectedKnowledgeStatus.value.isEmpty, () {
                      controller.selectedKnowledgeStatus.value = '';
                      controller.loadKnowledgeObjects();
                    }),
                    ..._knowledgeStatuses.map((s) => _filterChip(s, controller.selectedKnowledgeStatus.value == s, () {
                          controller.selectedKnowledgeStatus.value = s;
                          controller.loadKnowledgeObjects();
                        })),
                  ],
                )),
            const SizedBox(height: 12),
            Obx(() {
              if (controller.knowledgeObjects.isEmpty) {
                return const Text(
                  'Chưa có Knowledge Object nào.',
                  style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                );
              }
              return SizedBox(
                height: 86,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: controller.knowledgeObjects.length,
                  separatorBuilder: (_, _) => const SizedBox(width: 8),
                  itemBuilder: (context, index) {
                    final obj = controller.knowledgeObjects[index];
                    final id = obj['id'] as String? ?? '';
                    final title = obj['title'] as String? ?? 'Untitled';
                    final type = obj['object_type'] as String? ?? 'note';
                    final status = obj['status'] as String? ?? 'capture';
                    final isPromotable = status == 'capture' || status == 'candidate';

                    return Obx(() {
                      final isSelected = controller.selectedKnowledgeId.value == id;
                      return InkWell(
                        onTap: () {
                          controller.selectedKnowledgeId.value = id;
                          controller.loadBacklinks(id);
                        },
                        borderRadius: BorderRadius.circular(10),
                        child: Container(
                          width: 200,
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: isSelected ? AppTheme.primary.withValues(alpha: 0.08) : const Color(0xFF070C18),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: isSelected ? AppTheme.primary : AppTheme.borderDark),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                title,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.white),
                              ),
                              Row(
                                children: [
                                  Text(
                                    type.toUpperCase(),
                                    style: const TextStyle(fontSize: 9, color: AppTheme.textMutedDark, fontWeight: FontWeight.bold),
                                  ),
                                  const Spacer(),
                                  Text(
                                    status.toUpperCase(),
                                    style: TextStyle(
                                      fontSize: 9,
                                      fontWeight: FontWeight.bold,
                                      color: status == 'approved' ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
                                    ),
                                  ),
                                ],
                              ),
                              if (isPromotable)
                                SizedBox(
                                  width: double.infinity,
                                  child: TextButton(
                                    onPressed: () => controller.promoteObject(id),
                                    style: TextButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(vertical: 2),
                                      minimumSize: Size.zero,
                                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                    ),
                                    child: const Text(
                                      'Duyệt',
                                      style: TextStyle(fontSize: 10, color: AppTheme.primary, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      );
                    });
                  },
                ),
              );
            }),
            Obx(() {
              if (controller.selectedKnowledgeId.value == null) return const SizedBox.shrink();
              return Padding(
                padding: const EdgeInsets.only(top: 8),
                child: controller.backlinks.isEmpty
                    ? const Text(
                        'Mục này chưa có liên kết ngược nào.',
                        style: TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                      )
                    : Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: controller.backlinks.map((b) {
                          final srcTitle = b['source_title'] as String? ?? '';
                          return Chip(
                            label: Text(srcTitle, style: const TextStyle(fontSize: 10)),
                            backgroundColor: const Color(0xFF070C18),
                            side: const BorderSide(color: AppTheme.borderDark),
                          );
                        }).toList(),
                      ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _filterChip(String label, bool selected, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: selected ? AppTheme.primary.withValues(alpha: 0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: selected ? AppTheme.primary : AppTheme.borderDark),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 10.5,
            color: selected ? AppTheme.primaryLight : AppTheme.textMutedDark,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}
