import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:get/get.dart';

import '../../../core/theme/app_theme.dart';
import '../controllers/prompt_registry_controller.dart';

class PromptRegistryView extends StatelessWidget {
  const PromptRegistryView({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.put(PromptRegistryController());

    return Scaffold(
      backgroundColor: const Color(0xFF060A14),
      body: SafeArea(
        child: Column(
          children: [
            _buildTopBar(context, controller),
            _buildDomainTabs(controller),
            const Divider(height: 1, color: Color(0xFF1E293B)),
            Expanded(
              child: Obx(() {
                if (controller.isLoading.value && controller.prompts.isEmpty) {
                  return const Center(
                    child: CircularProgressIndicator(
                      valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primary),
                    ),
                  );
                }

                return LayoutBuilder(
                  builder: (context, constraints) {
                    final isNarrow = constraints.maxWidth < 850;

                    if (isNarrow) {
                      // On narrow screens, show either list or detail based on selection
                      return Obx(() {
                        if (controller.selectedPrompt.value != null && controller.selectedDetail.value != null) {
                          return _buildDetailPane(context, controller, isMobile: true);
                        }
                        return _buildMasterListPane(controller);
                      });
                    }

                    // Desktop dual-pane master-detail
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        SizedBox(
                          width: 360,
                          child: _buildMasterListPane(controller),
                        ),
                        const VerticalDivider(width: 1, color: Color(0xFF1E293B)),
                        Expanded(
                          child: _buildDetailPane(context, controller, isMobile: false),
                        ),
                      ],
                    );
                  },
                );
              }),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTopBar(BuildContext context, PromptRegistryController controller) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      decoration: const BoxDecoration(
        color: Color(0xFF080F1E),
        border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: AppTheme.primaryGradient,
              borderRadius: BorderRadius.circular(10),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.primary.withValues(alpha: 0.3),
                  blurRadius: 10,
                  spreadRadius: 1,
                ),
              ],
            ),
            child: const Icon(Icons.terminal_rounded, color: Color(0xFF04070E), size: 20),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'Quản trị Prompt AI',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Cấu hình và tuỳ biến Prompt Templates theo từng bộ phận hệ thống',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.6),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          Obx(() {
            final isOwner = controller.isOwner.value;
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: isOwner
                    ? const Color(0xFF10B981).withValues(alpha: 0.15)
                    : const Color(0xFF64748B).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: isOwner
                      ? const Color(0xFF10B981).withValues(alpha: 0.4)
                      : const Color(0xFF64748B).withValues(alpha: 0.3),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isOwner ? Icons.verified_user_rounded : Icons.visibility_rounded,
                    size: 14,
                    color: isOwner ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    isOwner ? 'Chế độ Founder' : 'Chỉ xem',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: isOwner ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                    ),
                  ),
                ],
              ),
            );
          }),
          const SizedBox(width: 12),
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Colors.white70),
            tooltip: 'Tải lại danh sách',
            onPressed: () => controller.loadPrompts(),
          ),
        ],
      ),
    );
  }

  Widget _buildDomainTabs(PromptRegistryController controller) {
    return Container(
      color: const Color(0xFF070C18),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Obx(() {
        final domains = controller.availableDomains;
        final selected = controller.selectedDomain.value;

        return SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: domains.map((domain) {
              final isSelected = selected == domain;
              final count = controller.getDomainCount(domain);
              final label = domain == 'all' ? 'Tất cả' : domain;

              return Padding(
                padding: const EdgeInsets.only(right: 8),
                child: InkWell(
                  onTap: () => controller.selectDomain(domain),
                  borderRadius: BorderRadius.circular(10),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? AppTheme.primary.withValues(alpha: 0.15)
                          : const Color(0xFF0D172A),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: isSelected
                            ? AppTheme.primary
                            : const Color(0xFF1E293B),
                        width: isSelected ? 1.5 : 1,
                      ),
                      boxShadow: isSelected
                          ? [
                              BoxShadow(
                                color: AppTheme.primary.withValues(alpha: 0.25),
                                blurRadius: 8,
                                spreadRadius: 0.5,
                              ),
                            ]
                          : [],
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          label,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                            color: isSelected ? AppTheme.primary : Colors.white70,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: isSelected
                                ? AppTheme.primary.withValues(alpha: 0.3)
                                : const Color(0xFF1E293B),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '$count',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: isSelected ? Colors.white : Colors.white60,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        );
      }),
    );
  }

  Widget _buildMasterListPane(PromptRegistryController controller) {
    return Container(
      color: const Color(0xFF070C18),
      child: Column(
        children: [
          // Search box
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: controller.searchController,
              onChanged: controller.updateSearch,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: 'Tìm kiếm prompt...',
                hintStyle: const TextStyle(color: Colors.white38, fontSize: 13),
                prefixIcon: const Icon(Icons.search_rounded, color: Colors.white38, size: 18),
                suffixIcon: controller.searchQuery.value.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear_rounded, size: 16, color: Colors.white54),
                        onPressed: () {
                          controller.searchController.clear();
                          controller.updateSearch('');
                        },
                      )
                    : null,
                contentPadding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                filled: true,
                fillColor: const Color(0xFF0D172A),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF1E293B)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF1E293B)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: AppTheme.primary),
                ),
              ),
            ),
          ),
          // List items
          Expanded(
            child: Obx(() {
              final list = controller.filteredPrompts;
              if (list.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.search_off_rounded, size: 40, color: Colors.white.withValues(alpha: 0.3)),
                      const SizedBox(height: 10),
                      Text(
                        'Không tìm thấy prompt nào',
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 13),
                      ),
                    ],
                  ),
                );
              }

              return ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                itemCount: list.length,
                separatorBuilder: (_, _) => const SizedBox(height: 8),
                itemBuilder: (context, index) {
                  final item = list[index];
                  return Obx(() {
                    final selected = controller.selectedPrompt.value;
                    final isSelected = selected != null &&
                        selected['domain'] == item['domain'] &&
                        selected['name'] == item['name'];

                    return _buildPromptListItem(item, isSelected, () {
                      controller.selectPrompt(item);
                    });
                  });
                },
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildPromptListItem(Map<String, dynamic> item, bool isSelected, VoidCallback onTap) {
    final name = item['name'] as String? ?? '';

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          color: isSelected
              ? const Color(0xFF0F1F38)
              : const Color(0xFF0D172A),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? AppTheme.primary : const Color(0xFF1E293B),
            width: isSelected ? 1.5 : 1,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: AppTheme.primary.withValues(alpha: 0.2),
                    blurRadius: 10,
                    spreadRadius: 0.5,
                  ),
                ]
              : [],
        ),
        child: Row(
          children: [
            if (isSelected) ...[
              Container(
                width: 3,
                height: 18,
                margin: const EdgeInsets.only(right: 10),
                decoration: BoxDecoration(
                  color: AppTheme.primary,
                  borderRadius: BorderRadius.circular(2),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.primary.withValues(alpha: 0.8),
                      blurRadius: 6,
                    ),
                  ],
                ),
              ),
            ],
            Expanded(
              child: Text(
                name,
                style: TextStyle(
                  color: isSelected ? Colors.white : Colors.white70,
                  fontSize: 14,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                  letterSpacing: -0.2,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              size: 18,
              color: isSelected ? AppTheme.primary : Colors.white24,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailPane(BuildContext context, PromptRegistryController controller, {required bool isMobile}) {
    return Obx(() {
      final prompt = controller.selectedPrompt.value;
      if (prompt == null) {
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.touch_app_outlined, size: 48, color: Colors.white.withValues(alpha: 0.2)),
              const SizedBox(height: 12),
              Text(
                'Chọn một prompt từ danh sách để xem và chỉnh sửa',
                style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 14),
              ),
            ],
          ),
        );
      }

      if (controller.isLoadingDetail.value) {
        return const Center(
          child: CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primary),
          ),
        );
      }

      final detail = controller.selectedDetail.value ?? {};
      final domain = prompt['domain'] as String? ?? '';
      final name = prompt['name'] as String? ?? '';
      final isWired = prompt['is_wired'] == true;
      final isOverridden = prompt['is_overridden'] == true;
      final revisions = (detail['revisions'] as List?) ?? [];
      final defaultContent = detail['default_content'] as String? ?? '';
      final isOwner = controller.isOwner.value;

      return Container(
        color: const Color(0xFF060A14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Detail Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              decoration: const BoxDecoration(
                color: Color(0xFF080F1E),
                border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      if (isMobile) ...[
                        IconButton(
                          icon: const Icon(Icons.arrow_back_rounded, color: Colors.white70),
                          onPressed: () => controller.selectedPrompt.value = null,
                        ),
                        const SizedBox(width: 8),
                      ],
                      // Breadcrumb
                      Expanded(
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: const Color(0xFF00E5FF).withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                domain,
                                style: const TextStyle(
                                  color: Color(0xFF00E5FF),
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                            const Padding(
                              padding: EdgeInsets.symmetric(horizontal: 8),
                              child: Text('/', style: TextStyle(color: Colors.white38, fontSize: 14)),
                            ),
                            Flexible(
                              child: Text(
                                name,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 16,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 8),
                            IconButton(
                              icon: const Icon(Icons.copy_rounded, size: 16, color: Colors.white38),
                              tooltip: 'Sao chép định danh: $domain/$name',
                              onPressed: () {
                                Clipboard.setData(ClipboardData(text: '$domain/$name'));
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text('Đã sao chép "$domain/$name" vào clipboard'),
                                    duration: const Duration(seconds: 2),
                                  ),
                                );
                              },
                            ),
                          ],
                        ),
                      ),
                      // Action buttons
                      if (isOwner) ...[
                        if (controller.hasUnsavedChanges.value) ...[
                          TextButton(
                            onPressed: controller.isSaving.value ? null : controller.discardChanges,
                            child: const Text('Hủy thay đổi', style: TextStyle(color: Colors.white60)),
                          ),
                          const SizedBox(width: 8),
                        ],
                        OutlinedButton(
                          onPressed: controller.isResetting.value
                              ? null
                              : () => _confirmReset(context, controller, domain, name),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFFF59E0B),
                            side: const BorderSide(color: Color(0xFFF59E0B)),
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          ),
                          child: controller.isResetting.value
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFFF59E0B)),
                                )
                              : const Text('Đặt lại gốc'),
                        ),
                        const SizedBox(width: 10),
                        FilledButton(
                          onPressed: (controller.isSaving.value || !controller.hasUnsavedChanges.value)
                              ? null
                              : controller.saveCurrentPrompt,
                          style: FilledButton.styleFrom(
                            backgroundColor: AppTheme.primary,
                            foregroundColor: const Color(0xFF04070E),
                            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                            disabledBackgroundColor: const Color(0xFF1E293B),
                          ),
                          child: controller.isSaving.value
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                                )
                              : const Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.save_rounded, size: 16),
                                    SizedBox(width: 6),
                                    Text('Lưu phiên bản'),
                                  ],
                                ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 10),
                  // Status metadata chips row
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      _buildStatusPill(
                        isWired ? 'Đang kết nối AI thực tế' : 'Catalog (chưa gắn luồng chạy)',
                        isWired ? const Color(0xFF38BDF8) : const Color(0xFF94A3B8),
                        isWired ? Icons.bolt_rounded : Icons.info_outline_rounded,
                      ),
                      _buildStatusPill(
                        isOverridden ? 'Bản tuỳ chỉnh (${revisions.length} phiên bản)' : 'Bản mặc định gốc',
                        isOverridden ? const Color(0xFF10B981) : const Color(0xFF64748B),
                        isOverridden ? Icons.history_edu_rounded : Icons.lock_outline_rounded,
                      ),
                      if (controller.hasUnsavedChanges.value)
                        _buildStatusPill(
                          'Có thay đổi chưa lưu',
                          const Color(0xFFF59E0B),
                          Icons.warning_amber_rounded,
                        ),
                    ],
                  ),
                ],
              ),
            ),
            // Detail Navigation Tabs
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
              decoration: const BoxDecoration(
                color: Color(0xFF070C18),
                border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
              ),
              child: Row(
                children: [
                  _buildSubTabButton(
                    controller: controller,
                    index: 0,
                    icon: Icons.edit_document,
                    label: isOwner ? 'Soạn thảo Prompt' : 'Nội dung Prompt',
                  ),
                  const SizedBox(width: 10),
                  _buildSubTabButton(
                    controller: controller,
                    index: 1,
                    icon: Icons.history_rounded,
                    label: 'Lịch sử (${revisions.length})',
                  ),
                  const SizedBox(width: 10),
                  _buildSubTabButton(
                    controller: controller,
                    index: 2,
                    icon: Icons.compare_arrows_rounded,
                    label: 'So sánh bản gốc',
                  ),
                ],
              ),
            ),
            // Tab Content
            Expanded(
              child: Obx(() {
                final tab = controller.selectedDetailTab.value;
                switch (tab) {
                  case 1:
                    return _buildRevisionsTab(context, controller, revisions);
                  case 2:
                    return _buildDefaultComparisonTab(controller, defaultContent);
                  case 0:
                  default:
                    return _buildEditorTab(context, controller, isOwner);
                }
              }),
            ),
          ],
        ),
      );
    });
  }

  Widget _buildStatusPill(String label, Color color, IconData icon) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSubTabButton({
    required PromptRegistryController controller,
    required int index,
    required IconData icon,
    required String label,
  }) {
    return Obx(() {
      final isSelected = controller.selectedDetailTab.value == index;
      return InkWell(
        onTap: () => controller.selectedDetailTab.value = index,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFF142442) : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: isSelected ? AppTheme.primary : Colors.transparent,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 15,
                color: isSelected ? AppTheme.primary : Colors.white60,
              ),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                  color: isSelected ? AppTheme.primary : Colors.white70,
                ),
              ),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildEditorTab(BuildContext context, PromptRegistryController controller, bool isOwner) {
    final variables = controller.detectedVariables;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Founder helper banner
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isOwner
                  ? const Color(0xFF10B981).withValues(alpha: 0.08)
                  : const Color(0xFFF59E0B).withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: isOwner
                    ? const Color(0xFF10B981).withValues(alpha: 0.25)
                    : const Color(0xFFF59E0B).withValues(alpha: 0.25),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  isOwner ? Icons.shield_outlined : Icons.lock_outline_rounded,
                  color: isOwner ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    isOwner
                        ? 'Chế độ Founder: Bạn có thể chỉnh sửa prompt template này và bấm "Lưu phiên bản" để áp dụng cho toàn bộ Workspace.'
                        : 'Chế độ chỉ xem: Chỉ thành viên có vai trò Founder (Owner) mới có quyền chỉnh sửa prompt hệ thống.',
                    style: TextStyle(
                      fontSize: 12,
                      color: isOwner ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Detected Variables Chips
          if (variables.isNotEmpty) ...[
            Row(
              children: [
                const Icon(Icons.code_rounded, size: 16, color: Color(0xFF00E5FF)),
                const SizedBox(width: 6),
                const Text(
                  'Biến truyền vào phát hiện trong Prompt:',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.white70),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: variables.map((v) {
                return Tooltip(
                  message: 'Biến: \${$v}',
                  child: InkWell(
                    onTap: isOwner
                        ? () {
                            final current = controller.contentController.text;
                            final cursor = controller.contentController.selection.baseOffset;
                            final insertText = '\${$v}';
                            if (cursor >= 0 && cursor <= current.length) {
                              final newText = current.substring(0, cursor) + insertText + current.substring(cursor);
                              controller.contentController.text = newText;
                              controller.contentController.selection = TextSelection.collapsed(offset: cursor + insertText.length);
                            }
                          }
                        : null,
                    borderRadius: BorderRadius.circular(6),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF00E5FF).withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: const Color(0xFF00E5FF).withValues(alpha: 0.3)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            '\${$v}',
                            style: const TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFF00E5FF),
                            ),
                          ),
                          if (isOwner) ...[
                            const SizedBox(width: 4),
                            const Icon(Icons.add_rounded, size: 12, color: Color(0xFF00E5FF)),
                          ],
                        ],
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 16),
          ],

          // Text Editor Container
          Container(
            decoration: BoxDecoration(
              color: const Color(0xFF04070E),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: controller.hasUnsavedChanges.value
                    ? const Color(0xFFF59E0B).withValues(alpha: 0.5)
                    : const Color(0xFF1E293B),
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.5),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Editor header bar
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: const BoxDecoration(
                    color: Color(0xFF0D172A),
                    borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
                    border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.description_outlined, size: 15, color: Colors.white60),
                          SizedBox(width: 6),
                          Text(
                            'Template Content',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                              color: Colors.white70,
                              fontFamily: 'monospace',
                            ),
                          ),
                        ],
                      ),
                      Row(
                        children: [
                          IconButton(
                            icon: const Icon(Icons.copy_rounded, size: 16, color: Colors.white60),
                            tooltip: 'Sao chép toàn bộ nội dung',
                            onPressed: () {
                              Clipboard.setData(ClipboardData(text: controller.contentController.text));
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Đã sao chép nội dung prompt vào clipboard'),
                                  duration: Duration(seconds: 2),
                                ),
                              );
                            },
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                // Editor text area
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: TextField(
                    controller: controller.contentController,
                    readOnly: !isOwner,
                    maxLines: null,
                    minLines: 15,
                    style: const TextStyle(
                      color: Color(0xFFE2E8F0),
                      fontSize: 13,
                      fontFamily: 'monospace',
                      height: 1.6,
                    ),
                    decoration: InputDecoration(
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none,
                      filled: false,
                      hintText: 'Nhập nội dung prompt template...',
                      hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.2)),
                    ),
                  ),
                ),
                // Editor footer status bar
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: const BoxDecoration(
                    color: Color(0xFF080F1E),
                    borderRadius: BorderRadius.vertical(bottom: Radius.circular(12)),
                    border: Border(top: BorderSide(color: Color(0xFF1E293B))),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Ký tự: ${controller.contentController.text.length} | Dòng: ${controller.contentController.text.split('\n').length}',
                        style: const TextStyle(fontSize: 11, color: Colors.white38, fontFamily: 'monospace'),
                      ),
                      if (controller.hasUnsavedChanges.value)
                        const Row(
                          children: [
                            Icon(Icons.circle, size: 8, color: Color(0xFFF59E0B)),
                            SizedBox(width: 4),
                            Text(
                              'Chưa lưu',
                              style: TextStyle(fontSize: 11, color: Color(0xFFF59E0B), fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRevisionsTab(BuildContext context, PromptRegistryController controller, List revisions) {
    if (revisions.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.history_toggle_off_rounded, size: 40, color: Colors.white.withValues(alpha: 0.3)),
            const SizedBox(height: 10),
            Text(
              'Chưa có lịch sử phiên bản nào được ghi nhận',
              style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 13),
            ),
          ],
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(20),
      itemCount: revisions.length,
      separatorBuilder: (_, _) => const SizedBox(height: 12),
      itemBuilder: (context, index) {
        final rev = revisions[index] as Map<String, dynamic>;
        final revNo = rev['revision_no'] ?? (revisions.length - index);
        final createdAt = rev['created_at'] ?? 'Chưa rõ';
        final isDefault = rev['is_default'] == true;
        final revContent = rev['content'] as String? ?? '';

        return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF0D172A),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: isDefault
                              ? const Color(0xFF64748B).withValues(alpha: 0.2)
                              : const Color(0xFF10B981).withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: isDefault
                                ? const Color(0xFF64748B).withValues(alpha: 0.4)
                                : const Color(0xFF10B981).withValues(alpha: 0.4),
                          ),
                        ),
                        child: Text(
                          isDefault ? 'Bản gốc (Revision 0)' : 'Revision $revNo',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: isDefault ? const Color(0xFF94A3B8) : const Color(0xFF10B981),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        createdAt.toString(),
                        style: const TextStyle(fontSize: 12, color: Colors.white38),
                      ),
                    ],
                  ),
                  if (controller.isOwner.value)
                    FilledButton.tonal(
                      onPressed: () => controller.restoreRevision(revContent),
                      style: FilledButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        minimumSize: const Size(0, 32),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.restore_rounded, size: 14),
                          SizedBox(width: 4),
                          Text('Nạp vào editor', style: TextStyle(fontSize: 11)),
                        ],
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF04070E),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF1E293B)),
                ),
                child: Text(
                  revContent.isEmpty ? '(Nội dung rỗng)' : revContent,
                  maxLines: 6,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 12,
                    color: Colors.white70,
                    height: 1.5,
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildDefaultComparisonTab(PromptRegistryController controller, String defaultContent) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF0284C7).withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFF0284C7).withValues(alpha: 0.3)),
            ),
            child: const Row(
              children: [
                Icon(Icons.info_outline_rounded, color: Color(0xFF38BDF8), size: 20),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Dưới đây là nội dung template mặc định được định nghĩa trong mã nguồn hệ thống. Nếu muốn hoàn tác mọi tuỳ chỉnh, hãy bấm "Đặt lại gốc".',
                    style: TextStyle(fontSize: 12, color: Color(0xFF38BDF8)),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF04070E),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: SelectableText(
              defaultContent.isEmpty ? '(Không có nội dung mặc định)' : defaultContent,
              style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 13,
                color: Color(0xFFCBD5E1),
                height: 1.6,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmReset(
    BuildContext context,
    PromptRegistryController controller,
    String domain,
    String name,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        backgroundColor: const Color(0xFF0D172A),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Color(0xFF1E293B)),
        ),
        title: const Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: Color(0xFFF59E0B)),
            SizedBox(width: 10),
            Text('Xác nhận đặt lại gốc', style: TextStyle(color: Colors.white, fontSize: 16)),
          ],
        ),
        content: Text(
          'Bạn có chắc chắn muốn đặt lại prompt "$domain/$name" về bản mẫu mặc định của hệ thống? Các tuỳ chỉnh hiện tại sẽ được lưu vào lịch sử nhưng không còn được áp dụng.',
          style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.5),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogCtx).pop(false),
            child: const Text('Hủy', style: TextStyle(color: Colors.white60)),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogCtx).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFFF59E0B),
              foregroundColor: Colors.black,
            ),
            child: const Text('Đặt lại mặc định'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await controller.resetCurrentPrompt();
    }
  }
}
