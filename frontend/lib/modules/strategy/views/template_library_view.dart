import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/app_modal_dialog.dart';
import '../controllers/project_orchestration_controller.dart';

/// Quản trị workspace-local template - thuộc workspace settings, KHÔNG nằm
/// trong founder kickoff path (design §"API and UI direction"). Reset tạo
/// một local version mới từ system seed; các stage đã snapshot version cũ
/// không bị ảnh hưởng - dialog xác nhận nói rõ điều đó trước khi thực hiện.
class TemplateLibraryView extends StatelessWidget {
  const TemplateLibraryView({super.key});

  ProjectOrchestrationController get controller => Get.find<ProjectOrchestrationController>();

  @override
  Widget build(BuildContext context) {
    controller.loadWorkspaceTemplates();
    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      appBar: AppBar(
        backgroundColor: AppTheme.surfaceDarkHeader,
        title: const Text('Thư viện Template'),
        actions: [
          TextButton(
            onPressed: controller.provisionWorkspaceTemplates,
            child: const Text('Provision mặc định'),
          ),
        ],
      ),
      body: Obx(() {
        if (controller.isLoading.value && controller.workspaceTemplates.isEmpty) {
          return const Center(child: CircularProgressIndicator());
        }
        if (controller.workspaceTemplates.isEmpty) {
          return const Center(
            child: Text('Chưa có template nào. Bấm "Provision mặc định" để khởi tạo 6 template.', style: TextStyle(color: AppTheme.textMutedDark)),
          );
        }
        return ListView.builder(
          padding: const EdgeInsets.all(20),
          itemCount: controller.workspaceTemplates.length,
          itemBuilder: (context, index) {
            final template = controller.workspaceTemplates[index] as Map<String, dynamic>;
            return _templateCard(context, template);
          },
        );
      }),
    );
  }

  Widget _templateCard(BuildContext context, Map<String, dynamic> template) {
    final capabilities = (template['capabilities'] as List<dynamic>?) ?? const [];
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(14), border: Border.all(color: AppTheme.borderDark)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(template['name']?.toString() ?? '', style: const TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.bold, fontSize: 16)),
              ),
              Text('v${template['active_version_no']}', style: const TextStyle(color: AppTheme.textMutedDark)),
              const SizedBox(width: 12),
              OutlinedButton(
                onPressed: () => _confirmReset(context, template),
                child: const Text('Reset'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text('${capabilities.length} năng lực', style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
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
}
