import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/strategy_controller.dart';
import '../project_kickoff_view.dart';
import '../template_library_view.dart';

/// Điểm vào cho SaaS Project Stage & Agent Orchestration: chọn hoặc tạo một
/// Project rồi mở ProjectKickoffView cho project đó (design §"Primary
/// workflow" bước 1-2). Đây là màn hình founder thấy đầu tiên - quản trị
/// template nằm ở TemplateLibraryView riêng, mở qua nút góc trên.
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
                child: Text('Project & MVP Roadmap', style: TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.bold, fontSize: 18)),
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
                label: const Text('Project mới'),
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
                  child: Text('Chưa có Project nào. Bấm "Project mới" để bắt đầu roadmap.', style: TextStyle(color: AppTheme.textMutedDark)),
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
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        title: const Text('Project mới', style: TextStyle(color: AppTheme.textDark)),
        content: TextField(
          controller: titleController,
          autofocus: true,
          style: const TextStyle(color: AppTheme.textDark),
          decoration: const InputDecoration(hintText: 'Tên project', hintStyle: TextStyle(color: AppTheme.textMutedDark)),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Huỷ')),
          ElevatedButton(
            onPressed: () async {
              final title = titleController.text.trim();
              if (title.isEmpty) return;
              Navigator.pop(ctx);
              await controller.createProject(title: title);
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: AppTheme.backgroundDarker),
            child: const Text('Tạo'),
          ),
        ],
      ),
    );
  }
}
