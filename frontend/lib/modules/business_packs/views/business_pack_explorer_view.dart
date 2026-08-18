import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';
import '../controllers/business_pack_controller.dart';
import 'widgets/override_editor_dialog.dart';
import 'widgets/pack_conflict_dialog.dart';

class BusinessPackExplorerView extends StatelessWidget {
  const BusinessPackExplorerView({super.key});

  BusinessPackController get controller {
    if (!Get.isRegistered<BusinessPackController>()) {
      return Get.put(BusinessPackController());
    }
    return Get.find<BusinessPackController>();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF0B0F19),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header Bar
          JavisFloatingAppBar(
            title: 'Gói Tri Thức Nghiệp Vụ (Business Knowledge Packs)',
            subtitle: '12 bộ khung chuẩn hóa SOP, Template biểu mẫu và Căn cứ pháp lý Việt Nam cho Doanh nghiệp Tự trị.',
            icon: Icons.auto_stories_rounded,
            actions: [
              IconButton(
                onPressed: () => controller.loadPacks(),
                tooltip: 'Làm mới danh sách',
                icon: const Icon(Icons.refresh_rounded, color: Colors.white70),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Domain Selector Bar
          _buildDomainSelector(context),
          const SizedBox(height: 12),

          // Main 2-Column Content
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value && controller.packs.isEmpty) {
                return const Center(child: CircularProgressIndicator());
              }

              final pack = controller.selectedPack.value;
              if (pack == null) {
                return const Center(
                  child: Text(
                    'Chọn một gói nghiệp vụ để xem chi tiết',
                    style: TextStyle(color: AppTheme.textMutedDark),
                  ),
                );
              }

              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Left Pane: Pack Summary & Legal Citations
                  SizedBox(
                    width: 380,
                    child: _buildPackInfoPane(context, pack),
                  ),
                  const SizedBox(width: 16),

                  // Right Pane: Tabs of Capabilities, Templates, and SOPs
                  Expanded(
                    child: _buildPackContentPane(context, pack),
                  ),
                ],
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildDomainSelector(BuildContext context) {
    return Obx(() {
      if (controller.packs.isEmpty) return const SizedBox.shrink();

      return SizedBox(
        height: 48,
        child: ListView.separated(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          scrollDirection: Axis.horizontal,
          itemCount: controller.packs.length,
          separatorBuilder: (context, index) => const SizedBox(width: 8),
          itemBuilder: (context, index) {
            final p = controller.packs[index];
            final packId = p['id'] ?? p['name'] ?? '';
            final isSelected = controller.selectedPack.value?['id'] == packId ||
                controller.selectedPack.value?['name'] == packId;

            return FilterChip(
              avatar: Icon(
                _getDomainIcon(packId),
                size: 16,
                color: isSelected ? Colors.black : AppTheme.primary,
              ),
              label: Text(p['display_name'] ?? p['title'] ?? packId.toString().toUpperCase()),
              selected: isSelected,
              selectedColor: AppTheme.primary,
              backgroundColor: const Color(0xFF0F172A),
              side: BorderSide(
                color: isSelected ? AppTheme.primary : const Color(0xFF1E293B),
              ),
              labelStyle: TextStyle(
                color: isSelected ? Colors.black : Colors.white,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                fontSize: 12,
              ),
              onSelected: (_) => controller.selectPack(packId),
            );
          },
        ),
      );
    });
  }

  Widget _buildPackInfoPane(BuildContext context, Map<String, dynamic> pack) {
    final packId = pack['id'] ?? pack['name'] ?? '';
    final capabilities = pack['capabilities'] as List? ?? [];
    final templates = pack['templates'] as List? ?? [];
    final sops = pack['sops'] as List? ?? [];

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(_getDomainIcon(packId), color: AppTheme.primary, size: 20),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            pack['display_name'] ?? pack['title'] ?? packId,
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                          ),
                          Text(
                            'v${pack['version'] ?? '1.0.0'} • Phân loại: ${pack['classification'] ?? 'CORE'}',
                            style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 11),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  pack['description'] ?? 'Bộ tài liệu và năng lực nghiệp vụ tự động hóa.',
                  style: const TextStyle(color: Colors.white70, fontSize: 12),
                ),
              ],
            ),
          ),

          // Statistics Row
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildStatBadge('${capabilities.length}', 'Năng lực AI', Icons.psychology_outlined),
                _buildStatBadge('${templates.length}', 'Templates', Icons.description_outlined),
                _buildStatBadge('${sops.length}', 'Quy trình SOP', Icons.checklist_rtl_rounded),
              ],
            ),
          ),
          const Divider(height: 1, color: Color(0xFF1E293B)),

          // Legal Sources Section
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.gavel_outlined, size: 16, color: Color(0xFF10B981)),
                      SizedBox(width: 8),
                      Text(
                        'Căn Cứ Pháp Lý Bảo Chứng (VN Law)',
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Expanded(
                    child: Obx(() {
                      if (controller.isLoadingLegal.value) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      if (controller.legalSources.isEmpty) {
                        return const Center(
                          child: Text(
                            'Chưa có liên kết pháp lý cụ thể.',
                            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
                          ),
                        );
                      }
                      return ListView.separated(
                        itemCount: controller.legalSources.length,
                        separatorBuilder: (context, index) => const SizedBox(height: 8),
                        itemBuilder: (context, idx) {
                          final source = controller.legalSources[idx];
                          return _buildLegalSourceCard(context, packId, source);
                        },
                      );
                    }),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatBadge(String count, String label, IconData icon) {
    return Column(
      children: [
        Row(
          children: [
            Icon(icon, size: 14, color: AppTheme.primary),
            const SizedBox(width: 4),
            Text(count, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
          ],
        ),
        Text(label, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 11)),
      ],
    );
  }

  Widget _buildLegalSourceCard(BuildContext context, String packId, Map<String, dynamic> source) {
    final sourceId = source['id'] ?? source['code'] ?? 'VN-LAW';
    final title = source['title'] ?? source['name'] ?? sourceId;
    final status = source['status'] ?? 'applicable';

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF090D16),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 12),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: (status == 'applicable' ? const Color(0xFF10B981) : Colors.amber).withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  status.toUpperCase(),
                  style: TextStyle(
                    color: status == 'applicable' ? const Color(0xFF10B981) : Colors.amber,
                    fontSize: 9,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          if (source['articles'] != null) ...[
            const SizedBox(height: 4),
            Text(
              'Điều khoản: ${(source['articles'] as List).take(3).join(', ')}',
              style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 10),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildPackContentPane(BuildContext context, Map<String, dynamic> pack) {
    final packId = pack['id'] ?? pack['name'] ?? '';
    final templates = pack['templates'] as List? ?? [];
    final sops = pack['sops'] as List? ?? [];
    final capabilities = pack['capabilities'] as List? ?? [];

    return DefaultTabController(
      length: 3,
      child: Container(
        decoration: BoxDecoration(
          color: const Color(0xFF0F172A),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFF1E293B)),
        ),
        child: Column(
          children: [
            // Tabs Bar & Actions
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: const BoxDecoration(
                border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
              ),
              child: Row(
                children: [
                  const Expanded(
                    child: TabBar(
                      isScrollable: true,
                      indicatorColor: AppTheme.primary,
                      labelColor: AppTheme.primary,
                      unselectedLabelColor: AppTheme.textMutedDark,
                      tabs: [
                        Tab(text: 'Biểu Mẫu & Living Artifacts'),
                        Tab(text: 'Quy Trình Chuẩn (SOPs)'),
                        Tab(text: 'Năng Lực Tự Động Hóa (Capabilities)'),
                      ],
                    ),
                  ),
                  // Check updates button
                  TextButton.icon(
                    onPressed: () => _onCheckUpdates(context, packId),
                    icon: const Icon(Icons.cloud_sync_outlined, size: 16),
                    label: const Text('Kiểm tra cập nhật', style: TextStyle(fontSize: 12)),
                    style: TextButton.styleFrom(foregroundColor: AppTheme.primary),
                  ),
                ],
              ),
            ),

            // Tab Views
            Expanded(
              child: TabBarView(
                children: [
                  // Tab 1: Templates
                  _buildTemplatesList(context, packId, templates),
                  // Tab 2: SOPs
                  _buildSopsList(context, packId, sops),
                  // Tab 3: Capabilities
                  _buildCapabilitiesList(context, packId, capabilities),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTemplatesList(BuildContext context, String packId, List templates) {
    if (templates.isEmpty) {
      return const Center(child: Text('Chưa có Template nào trong gói này.', style: TextStyle(color: AppTheme.textMutedDark)));
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: templates.length,
      separatorBuilder: (context, index) => const SizedBox(height: 12),
      itemBuilder: (context, index) {
        final item = templates[index];
        final id = item['id'] ?? item['name'] ?? 'template-$index';
        final title = item['title'] ?? item['display_name'] ?? id;
        final docType = item['document_type'] ?? 'FRM';
        final isOverridden = item['is_overridden'] ?? false;

        return _buildAssetCard(
          context: context,
          packId: packId,
          assetId: id,
          assetType: 'template',
          title: title,
          typeBadge: docType,
          description: item['description'] ?? 'Biểu mẫu văn bản chuẩn nghiệp vụ.',
          isOverridden: isOverridden,
          onView: () async {
            await controller.viewTemplate(packId, id);
            if (context.mounted) {
              _showAssetDetailModal(context, packId, id, 'template', title, isOverridden);
            }
          },
          onOverride: () => _openOverrideEditor(context, packId, id, 'template', title, isOverridden),
        );
      },
    );
  }

  Widget _buildSopsList(BuildContext context, String packId, List sops) {
    if (sops.isEmpty) {
      return const Center(child: Text('Chưa có SOP nào trong gói này.', style: TextStyle(color: AppTheme.textMutedDark)));
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: sops.length,
      separatorBuilder: (context, index) => const SizedBox(height: 12),
      itemBuilder: (context, index) {
        final item = sops[index];
        final id = item['id'] ?? item['name'] ?? 'sop-$index';
        final title = item['title'] ?? item['display_name'] ?? id;
        final isOverridden = item['is_overridden'] ?? false;

        return _buildAssetCard(
          context: context,
          packId: packId,
          assetId: id,
          assetType: 'sop',
          title: title,
          typeBadge: 'SOP',
          description: item['description'] ?? 'Quy trình thực thi và checklist chuẩn hóa.',
          isOverridden: isOverridden,
          onView: () async {
            await controller.viewSOP(packId, id);
            if (context.mounted) {
              _showAssetDetailModal(context, packId, id, 'sop', title, isOverridden);
            }
          },
          onOverride: () => _openOverrideEditor(context, packId, id, 'sop', title, isOverridden),
        );
      },
    );
  }

  Widget _buildCapabilitiesList(BuildContext context, String packId, List capabilities) {
    if (capabilities.isEmpty) {
      return const Center(child: Text('Chưa có Capability nào trong gói này.', style: TextStyle(color: AppTheme.textMutedDark)));
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: capabilities.length,
      separatorBuilder: (context, index) => const SizedBox(height: 12),
      itemBuilder: (context, index) {
        final item = capabilities[index];
        final id = item['id'] ?? item['name'] ?? 'cap-$index';
        final title = item['title'] ?? item['display_name'] ?? id;

        return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF090D16),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.bolt_rounded, size: 18, color: AppTheme.primary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      item['execution_mode'] ?? 'AUTONOMOUS',
                      style: const TextStyle(color: AppTheme.primary, fontSize: 10, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                item['description'] ?? 'Năng lực AI thực thi nhiệm vụ theo kịch bản chuẩn.',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildAssetCard({
    required BuildContext context,
    required String packId,
    required String assetId,
    required String assetType,
    required String title,
    required String typeBadge,
    required String description,
    required bool isOverridden,
    required VoidCallback onView,
    required VoidCallback onOverride,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF090D16),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: isOverridden ? AppTheme.primary.withValues(alpha: 0.5) : const Color(0xFF1E293B)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(typeBadge, style: const TextStyle(color: AppTheme.primary, fontSize: 10, fontWeight: FontWeight.bold)),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                    ),
                    if (isOverridden) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0xFF10B981).withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Text('CUSTOMIZED', style: TextStyle(color: Color(0xFF10B981), fontSize: 9, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 6),
                Text(description, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 11)),
              ],
            ),
          ),
          const SizedBox(width: 12),
          IconButton(
            icon: const Icon(Icons.visibility_outlined, size: 18, color: Colors.white70),
            tooltip: 'Xem nội dung',
            onPressed: onView,
          ),
          IconButton(
            icon: Icon(Icons.tune_rounded, size: 18, color: isOverridden ? AppTheme.primary : Colors.white70),
            tooltip: 'Tùy biến cho công ty',
            onPressed: onOverride,
          ),
        ],
      ),
    );
  }

  void _showAssetDetailModal(
    BuildContext context,
    String packId,
    String assetId,
    String assetType,
    String title,
    bool isOverridden,
  ) {
    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: const Color(0xFF0F172A),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Container(
          width: 800,
          height: 650,
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(title, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                  IconButton(icon: const Icon(Icons.close, color: Colors.white70), onPressed: () => Get.back()),
                ],
              ),
              const Divider(color: Color(0xFF1E293B)),
              Expanded(
                child: Obx(() {
                  if (controller.isResolvingAsset.value) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  final asset = controller.activeAsset.value;
                  final body = asset?['body'] ?? asset?['content'] ?? 'Chưa có nội dung.';
                  return SingleChildScrollView(
                    child: SelectableText(
                      body.toString(),
                      style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.5),
                    ),
                  );
                }),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _openOverrideEditor(
    BuildContext context,
    String packId,
    String assetId,
    String assetType,
    String title,
    bool isOverridden,
  ) async {
    // Resolve current body
    if (assetType == 'template') {
      await controller.viewTemplate(packId, assetId);
    } else {
      await controller.viewSOP(packId, assetId);
    }
    final asset = controller.activeAsset.value;
    final currentBody = asset?['body'] ?? asset?['content'] ?? '';

    if (!context.mounted) return;

    showDialog(
      context: context,
      builder: (ctx) => OverrideEditorDialog(
        packId: packId,
        assetId: assetId,
        assetType: assetType,
        title: title,
        currentBody: currentBody.toString(),
        isCustomized: isOverridden,
        onSave: (body, notes) {
          controller.saveOverride(
            packId: packId,
            assetId: assetId,
            assetType: assetType,
            bodyOverride: body,
            notes: notes,
          );
        },
        onResetToFactory: () {
          controller.resetAssetToFactory(packId, assetId);
        },
      ),
    );
  }

  void _onCheckUpdates(BuildContext context, String packId) async {
    final updateResult = await controller.checkUpdates(packId);
    if (updateResult == null) return;

    final hasUpdates = updateResult['has_updates'] ?? false;
    final conflicts = updateResult['conflicts'] as List? ?? [];

    if (!context.mounted) return;

    if (!hasUpdates) {
      Get.snackbar(
        'Đã cập nhật',
        'Gói $packId đang ở phiên bản mới nhất.',
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
      return;
    }

    if (conflicts.isNotEmpty) {
      final conflict = conflicts.first;
      final assetId = conflict['asset_id'] ?? '';
      showDialog(
        context: context,
        builder: (ctx) => PackConflictDialog(
          packId: packId,
          assetId: assetId,
          oldContent: conflict['company_content'] ?? '',
          newContent: conflict['factory_content'] ?? '',
          onResolve: (resolution, mergedBody) {
            controller.resolveConflict(
              packId: packId,
              assetId: assetId,
              resolution: resolution,
              mergedBody: mergedBody,
            );
          },
        ),
      );
    } else {
      Get.snackbar(
        'Có bản cập nhật mới',
        'Phiên bản mới khả dụng, không phát hiện xung đột.',
        backgroundColor: const Color(0xFF3B82F6),
        colorText: Colors.white,
      );
    }
  }

  IconData _getDomainIcon(String domain) {
    switch (domain.toLowerCase()) {
      case 'governance':
        return Icons.gavel_rounded;
      case 'operations':
        return Icons.precision_manufacturing_rounded;
      case 'sales':
        return Icons.point_of_sale_rounded;
      case 'reporting':
        return Icons.bar_chart_rounded;
      case 'finance':
        return Icons.account_balance_wallet_rounded;
      case 'marketing':
        return Icons.campaign_rounded;
      case 'legal':
        return Icons.balance_rounded;
      case 'customer':
        return Icons.support_agent_rounded;
      case 'product_tech':
        return Icons.devices_other_rounded;
      case 'people':
        return Icons.people_alt_rounded;
      case 'training':
        return Icons.school_rounded;
      case 'growth':
        return Icons.trending_up_rounded;
      case 'strategy':
        return Icons.lightbulb_rounded;
      default:
        return Icons.folder_special_rounded;
    }
  }
}
