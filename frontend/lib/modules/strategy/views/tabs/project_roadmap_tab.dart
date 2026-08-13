import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../controllers/strategy_controller.dart';
import '../project_kickoff_view.dart';
import '../template_library_view.dart';

/// Điểm vào cho SaaS Project Stage & Agent Orchestration: chọn hoặc tạo một
/// Dự án rồi mở ProjectKickoffView cho dự án đó (design §"Primary workflow"
/// bước 1-2). Mô tả dự án ở đây chính là brief mà AI dùng kết hợp Foundation
/// (vision/mission/core values) để thiết kế MVP roadmap và OKRs/12WY - xem
/// ProjectOrchestrationService.generate_roadmap / RoutingService.plan_stage.
class ProjectRoadmapTab extends StatefulWidget {
  const ProjectRoadmapTab({super.key});

  @override
  State<ProjectRoadmapTab> createState() => _ProjectRoadmapTabState();
}

class _ProjectRoadmapTabState extends State<ProjectRoadmapTab> {
  StrategyController get controller => Get.find<StrategyController>();

  @override
  void initState() {
    super.initState();
    controller.loadProjects();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text('Dự án & MVP Roadmap', style: TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.bold, fontSize: 18)),
              ),
              TextButton.icon(
                onPressed: () => Get.to(() => const TemplateLibraryView()),
                icon: const Icon(Icons.tune_rounded, size: 16, color: AppTheme.textMutedDark),
                label: const Text('Quản trị Template', style: TextStyle(color: AppTheme.textMutedDark)),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: () => _showCreateProjectDialog(context),
                icon: const Icon(Icons.add_rounded, size: 16),
                label: const Text('Dự án mới'),
                style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: AppTheme.backgroundDarker),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value && controller.projects.isEmpty) {
                return const Center(child: CircularProgressIndicator());
              }
              if (controller.projects.isEmpty) {
                return const Center(
                  child: Text('Chưa có dự án nào. Bấm "Dự án mới" để bắt đầu roadmap.', style: TextStyle(color: AppTheme.textMutedDark)),
                );
              }
              return ListView.builder(
                itemCount: controller.projects.length,
                itemBuilder: (context, index) {
                  final project = controller.projects[index] as Map<String, dynamic>;
                  return _projectCard(project);
                },
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _projectCard(Map<String, dynamic> project) {
    final projectId = project['id']?.toString() ?? '';
    final description = project['description']?.toString();
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppTheme.borderDark)),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(project['title']?.toString() ?? '', style: const TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.w600, fontSize: 15)),
                if (description != null && description.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(description, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12), maxLines: 2, overflow: TextOverflow.ellipsis),
                  ),
                if (project['phase'] != null)
                  Text(project['phase'].toString(), style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
              ],
            ),
          ),
          ElevatedButton(
            onPressed: projectId.isEmpty ? null : () => Get.to(() => ProjectKickoffView(projectId: projectId)),
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: AppTheme.backgroundDarker),
            child: const Text('MVP Roadmap'),
          ),
        ],
      ),
    );
  }

  void _showCreateProjectDialog(BuildContext context) {
    final titleController = TextEditingController();
    final descriptionController = TextEditingController();
    AppModalDialog.show(
      context: context,
      title: 'Dự án mới',
      subtitle: 'Mô tả càng chi tiết, AI càng thiết kế roadmap và OKRs sát với chiến lược công ty',
      icon: Icons.rocket_launch_outlined,
      maxWidth: 560,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Tên dự án', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
          const SizedBox(height: 6),
          TextField(
            controller: titleController,
            autofocus: true,
            style: const TextStyle(color: AppTheme.textDark),
            decoration: InputDecoration(
              hintText: 'Ví dụ: Nền tảng định danh điện tử',
              hintStyle: const TextStyle(color: AppTheme.textMutedDark),
              filled: true,
              fillColor: AppTheme.surfaceDarkLighter,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
            ),
          ),
          const SizedBox(height: 16),
          const Text('Mô tả dự án (brief cho AI)', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
          const SizedBox(height: 6),
          TextField(
            controller: descriptionController,
            maxLines: 4,
            style: const TextStyle(color: AppTheme.textDark),
            decoration: InputDecoration(
              hintText: 'Vấn đề đang giải quyết, khách hàng mục tiêu, giá trị cốt lõi của dự án...',
              hintStyle: const TextStyle(color: AppTheme.textMutedDark),
              filled: true,
              fillColor: AppTheme.surfaceDarkLighter,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ')),
        ElevatedButton(
          onPressed: () async {
            final title = titleController.text.trim();
            if (title.isEmpty) return;
            final description = descriptionController.text.trim();
            Get.back();
            await controller.createProject(title: title, description: description.isEmpty ? null : description);
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: AppTheme.backgroundDarker),
          child: const Text('Tạo dự án'),
        ),
      ],
    );
  }
}
