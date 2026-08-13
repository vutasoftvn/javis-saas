import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../controllers/project_orchestration_controller.dart';

/// Founder kickoff journey (design §"Primary workflow" 1-4): brief đã có sẵn
/// (Project được tạo trước ở nơi khác) -> AI đề xuất MVP roadmap -> founder
/// sửa & xác nhận -> chọn 1 stage để lập kế hoạch & kích hoạt. Đây là luồng
/// ngắn dành cho founder; quản trị template nằm ở TemplateLibraryView riêng.
class ProjectKickoffView extends StatelessWidget {
  final String projectId;
  const ProjectKickoffView({super.key, required this.projectId});

  ProjectOrchestrationController get controller => Get.find<ProjectOrchestrationController>();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      appBar: AppBar(
        backgroundColor: AppTheme.surfaceDarkHeader,
        title: const Text('MVP Roadmap'),
      ),
      body: Obx(() {
        final error = controller.errorMessage.value;
        return SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (error != null)
                Container(
                  margin: const EdgeInsets.only(bottom: 16),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.error.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.error.withValues(alpha: 0.4)),
                  ),
                  child: Text(error, style: const TextStyle(color: AppTheme.error)),
                ),
              _buildRoadmapDraftSection(),
              const SizedBox(height: 24),
              _buildConfirmedStagesSection(),
            ],
          ),
        );
      }),
    );
  }

  Widget _buildRoadmapDraftSection() {
    return Obx(() {
      final draft = controller.roadmapDraft.value;
      final stageDrafts = (draft?['stages'] as List<dynamic>?) ?? const [];
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppTheme.borderDark),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text('MVP Roadmap (nháp)', style: TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.bold, fontSize: 16)),
                ),
                ElevatedButton.icon(
                  onPressed: controller.isGeneratingRoadmap.value ? null : () => controller.generateRoadmap(projectId),
                  icon: controller.isGeneratingRoadmap.value
                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.auto_awesome_rounded, size: 16),
                  label: const Text('AI đề xuất roadmap'),
                  style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: AppTheme.backgroundDarker),
                ),
              ],
            ),
            if (stageDrafts.isEmpty)
              const Padding(
                padding: EdgeInsets.only(top: 12),
                child: Text('Chưa có roadmap nháp. Bấm "AI đề xuất roadmap" để bắt đầu.', style: TextStyle(color: AppTheme.textMutedDark)),
              )
            else ...[
              const SizedBox(height: 12),
              for (final stage in stageDrafts) _draftStageCard(stage as Map<String, dynamic>),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: controller.isSaving.value
                          ? null
                          : () => controller.saveRoadmapDraft(projectId, List<Map<String, dynamic>>.from(stageDrafts)),
                      child: const Text('Lưu nháp'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: controller.isSaving.value
                          ? null
                          : () async {
                              await controller.saveRoadmapDraft(projectId, List<Map<String, dynamic>>.from(stageDrafts));
                              await controller.confirmRoadmap(projectId);
                            },
                      style: ElevatedButton.styleFrom(backgroundColor: AppTheme.success),
                      child: const Text('Xác nhận Roadmap'),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      );
    });
  }

  Widget _draftStageCard(Map<String, dynamic> stage) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDarkLighter,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(stage['title']?.toString() ?? '', style: const TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(stage['hypothesis']?.toString() ?? '', style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildConfirmedStagesSection() {
    return Obx(() {
      if (controller.stages.isEmpty) return const SizedBox.shrink();
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppTheme.borderDark),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Các stage đã xác nhận', style: TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 12),
            for (final stage in controller.stages) _confirmedStageRow(stage as Map<String, dynamic>),
          ],
        ),
      );
    });
  }

  Widget _confirmedStageRow(Map<String, dynamic> stage) {
    final status = stage['status']?.toString() ?? '';
    final stageId = stage['id']?.toString() ?? '';
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: AppTheme.surfaceDarkLighter, borderRadius: BorderRadius.circular(10)),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${stage['sequence_no']}. ${stage['title'] ?? ''}', style: const TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.w600)),
                Text(status, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
              ],
            ),
          ),
          if (status == 'CONFIRMED')
            ElevatedButton(
              onPressed: () => controller.planStage(projectId, stageId),
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: AppTheme.backgroundDarker),
              child: const Text('Lập kế hoạch'),
            ),
          Obx(() {
            final plan = controller.stagePlanDraft.value;
            if (plan == null || status != 'CONFIRMED') return const SizedBox.shrink();
            return Padding(
              padding: const EdgeInsets.only(left: 8),
              child: ElevatedButton(
                onPressed: controller.isSaving.value ? null : () => controller.activateStage(projectId, stageId),
                style: ElevatedButton.styleFrom(backgroundColor: AppTheme.success),
                child: const Text('Kích hoạt'),
              ),
            );
          }),
        ],
      ),
    );
  }
}
