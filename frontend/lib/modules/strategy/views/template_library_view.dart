import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/app_modal_dialog.dart';
import '../../../core/widgets/floating_app_bar.dart';
import '../controllers/project_orchestration_controller.dart';

class TemplateLibraryView extends StatelessWidget {
  static final RxInt _expandedTemplateIndex = (-1).obs;

  const TemplateLibraryView({super.key});

  ProjectOrchestrationController get controller => Get.find<ProjectOrchestrationController>();

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<ProjectOrchestrationController>()) {
      Get.put(ProjectOrchestrationController());
    }
    controller.loadWorkspaceTemplates();

    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CosaFloatingAppBar(
            title: 'Thư viện Template & Năng lực',
            subtitle: 'Xem chi tiết, chỉnh sửa năng lực và routing mặc định cho các dự án trong workspace.',
            icon: Icons.tune_rounded,
            actions: [
              ElevatedButton.icon(
                onPressed: controller.provisionWorkspaceTemplates,
                icon: const Icon(Icons.add_rounded, size: 16),
                label: const Text('Provision mặc định'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: AppTheme.backgroundDarker,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value && controller.workspaceTemplates.isEmpty) {
                return const Center(child: CircularProgressIndicator());
              }
              if (controller.workspaceTemplates.isEmpty) {
                return const Center(
                  child: Text(
                    'Chưa có template nào. Bấm "Provision mặc định" để khởi tạo 6 template.',
                    style: TextStyle(color: AppTheme.textMutedDark),
                  ),
                );
              }
              return ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                itemCount: controller.workspaceTemplates.length,
                itemBuilder: (context, index) {
                  final template = controller.workspaceTemplates[index] as Map<String, dynamic>;
                  return _TemplateCardItem(
                    template: template,
                    isExpanded: _expandedTemplateIndex.value == index,
                    onToggle: () {
                      if (_expandedTemplateIndex.value == index) {
                        _expandedTemplateIndex.value = -1;
                      } else {
                        _expandedTemplateIndex.value = index;
                      }
                    },
                    onReset: () => _confirmReset(context, template),
                    onEdit: () => _openEditDialog(context, template),
                  );
                },
              );
            }),
          ),
        ],
      ),
    );
  }

  void _confirmReset(BuildContext context, Map<String, dynamic> template) {
    AppModalDialog.show(
      context: context,
      title: 'Reset template "${template['name']}"?',
      subtitle: 'Tạo phiên bản local mới từ system seed',
      icon: Icons.restore_rounded,
      iconColor: AppTheme.warning,
      content: const Text(
        'Các stage đã kích hoạt trước đây vẫn giữ nguyên phiên bản template đã snapshot lúc activate - '
        'reset không làm thay đổi lịch sử hoặc kế hoạch đang chạy của chúng.',
        style: TextStyle(color: AppTheme.textMutedDark),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ')),
        ElevatedButton(
          onPressed: () {
            Get.back();
            controller.resetWorkspaceTemplate(template['id'].toString());
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.warning),
          child: const Text('Xác nhận Reset'),
        ),
      ],
    );
  }

  void _openEditDialog(BuildContext context, Map<String, dynamic> template) {
    final nameController = TextEditingController(text: template['name']?.toString() ?? '');
    final templateId = template['id'].toString();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            const Icon(Icons.edit_note_rounded, color: Color(0xFF00E5FF), size: 22),
            const SizedBox(width: 10),
            const Text(
              'Chỉnh sửa Template',
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        content: SizedBox(
          width: 480,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Tên Template:', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
              const SizedBox(height: 6),
              TextField(
                controller: nameController,
                style: const TextStyle(color: Colors.white, fontSize: 14),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: const Color(0xFF131D35),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: const BorderSide(color: Color(0xFF1E293B)),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Mã nguồn gốc: ${template['source_key'] ?? ''}',
                style: const TextStyle(color: Color(0xFF64748B), fontSize: 11),
              ),
              Text(
                'Phiên bản hiện tại: v${template['active_version_no'] ?? 1}',
                style: const TextStyle(color: Color(0xFF64748B), fontSize: 11),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Hủy', style: TextStyle(color: Color(0xFF94A3B8))),
          ),
          ElevatedButton(
            onPressed: () {
              final newName = nameController.text.trim();
              if (newName.isNotEmpty) {
                controller.updateWorkspaceTemplate(templateId, name: newName);
                Navigator.of(ctx).pop();
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF00E5FF),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            child: const Text('Lưu thay đổi', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }
}

class _TemplateCardItem extends StatelessWidget {
  final Map<String, dynamic> template;
  final bool isExpanded;
  final VoidCallback onToggle;
  final VoidCallback onReset;
  final VoidCallback onEdit;

  const _TemplateCardItem({
    required this.template,
    required this.isExpanded,
    required this.onToggle,
    required this.onReset,
    required this.onEdit,
  });

  @override
  Widget build(BuildContext context) {
    final capabilities = (template['capabilities'] as List<dynamic>?) ?? const [];

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isExpanded ? const Color(0xFF00E5FF).withValues(alpha: 0.4) : const Color(0xFF1E293B),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Card
          InkWell(
            onTap: onToggle,
            borderRadius: BorderRadius.circular(14),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF00E5FF).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.dashboard_customize_rounded, color: Color(0xFF00E5FF), size: 20),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              template['name']?.toString() ?? '',
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 15,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: const Color(0xFF1E293B),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                'v${template['active_version_no'] ?? 1}',
                                style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 10, fontWeight: FontWeight.bold),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${capabilities.length} năng lực được định nghĩa',
                          style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  // Action buttons
                  IconButton(
                    icon: const Icon(Icons.edit_outlined, color: Color(0xFF94A3B8), size: 18),
                    tooltip: 'Chỉnh sửa template',
                    onPressed: onEdit,
                  ),
                  OutlinedButton(
                    onPressed: onReset,
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      side: const BorderSide(color: Color(0xFF334155)),
                    ),
                    child: const Text('Reset', style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                  ),
                  const SizedBox(width: 8),
                  Icon(
                    isExpanded ? Icons.keyboard_arrow_up_rounded : Icons.keyboard_arrow_down_rounded,
                    color: const Color(0xFF64748B),
                  ),
                ],
              ),
            ),
          ),
          // Expanded Capabilities List
          if (isExpanded) ...[
            const Divider(height: 1, color: Color(0xFF1E293B)),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'DANH SÁCH NĂNG LỰC & CHẾ ĐỘ THỰC THI:',
                    style: TextStyle(
                      color: Color(0xFF64748B),
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const SizedBox(height: 10),
                  if (capabilities.isEmpty)
                    const Text('Chưa có năng lực nào.', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12))
                  else
                    ...capabilities.map((cap) {
                      final capMap = cap is Map<String, dynamic> ? cap : <String, dynamic>{};
                      final deliverables = (capMap['expected_deliverables'] as List<dynamic>?) ?? [];
                      final modes = (capMap['supported_execution_modes'] as List<dynamic>?) ?? [];
                      final risk = capMap['risk_level']?.toString() ?? 'low';

                      Color riskColor = const Color(0xFF10B981);
                      if (risk.toLowerCase() == 'medium') riskColor = const Color(0xFFF59E0B);
                      if (risk.toLowerCase() == 'high') riskColor = const Color(0xFFEF4444);

                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF131D35),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: const Color(0xFF1E293B)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    capMap['name']?.toString() ?? capMap['capability_key']?.toString() ?? '',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w600,
                                      fontSize: 13,
                                    ),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: riskColor.withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    'RỦI RO: ${risk.toUpperCase()}',
                                    style: TextStyle(color: riskColor, fontSize: 9, fontWeight: FontWeight.bold),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Key: ${capMap['capability_key'] ?? ''}',
                              style: const TextStyle(color: Color(0xFF64748B), fontSize: 10),
                            ),
                            if (deliverables.isNotEmpty) ...[
                              const SizedBox(height: 6),
                              Text(
                                'Đầu ra kỳ vọng: ${deliverables.join(', ')}',
                                style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                              ),
                            ],
                            if (modes.isNotEmpty) ...[
                              const SizedBox(height: 4),
                              Wrap(
                                spacing: 6,
                                children: modes.map((m) {
                                  return Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF1E293B),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(
                                      m.toString(),
                                      style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 9),
                                    ),
                                  );
                                }).toList(),
                              ),
                            ],
                          ],
                        ),
                      );
                    }),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
