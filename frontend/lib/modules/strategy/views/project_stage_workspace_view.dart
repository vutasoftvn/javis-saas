import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../controllers/project_orchestration_controller.dart';

/// Không gian làm việc của stage đang ACTIVE: dịch vụ AI được routing, và
/// cổng Week 13. Founder duyệt từng service assessment trước khi có bất kỳ
/// assignment nào được tạo - năng lực REGULATED/HIGH luôn hiển thị rõ yêu
/// cầu "Cần chuyên gia phê duyệt" và không cho chọn chế độ tự động.
class ProjectStageWorkspaceView extends StatelessWidget {
  final String projectId;
  final String stageId;
  const ProjectStageWorkspaceView({super.key, required this.projectId, required this.stageId});

  ProjectOrchestrationController get controller => Get.find<ProjectOrchestrationController>();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      appBar: AppBar(backgroundColor: AppTheme.surfaceDarkHeader, title: const Text('Stage đang hoạt động')),
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
                  ),
                  child: Text(error, style: const TextStyle(color: AppTheme.error)),
                ),
              _buildServiceAssessmentSection(),
              const SizedBox(height: 24),
              _buildWeek13Section(),
            ],
          ),
        );
      }),
    );
  }

  Widget _buildServiceAssessmentSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(14), border: Border.all(color: AppTheme.borderDark)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Expanded(child: Text('Dịch vụ AI đề xuất', style: TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.bold, fontSize: 16))),
              ElevatedButton(
                onPressed: () => controller.generateServiceAssessment(projectId, stageId),
                style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: AppTheme.backgroundDarker),
                child: const Text('Đánh giá dịch vụ'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Obx(() => Column(children: [for (final a in controller.serviceAssessments) _assessmentRow(a as Map<String, dynamic>)])),
          Obx(() {
            if (controller.serviceAssessments.isEmpty) return const SizedBox.shrink();
            return Align(
              alignment: Alignment.centerRight,
              child: ElevatedButton(
                onPressed: controller.isSaving.value ? null : () => _confirmAllApproved(),
                style: ElevatedButton.styleFrom(backgroundColor: AppTheme.success),
                child: const Text('Duyệt các dịch vụ REQUIRED'),
              ),
            );
          }),
        ],
      ),
    );
  }

  void _confirmAllApproved() {
    final decisions = controller.serviceAssessments
        .where((a) => (a as Map)['disposition'] != 'OPTIONAL')
        .map<Map<String, dynamic>>((a) => {'assessment_id': (a as Map)['id'], 'approved': true})
        .toList();
    if (decisions.isEmpty) return;
    controller.confirmServiceAssessment(projectId, stageId, decisions);
  }

  Widget _assessmentRow(Map<String, dynamic> assessment) {
    final requiresReview = assessment['professional_review_required'] == true;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: AppTheme.surfaceDarkLighter, borderRadius: BorderRadius.circular(10)),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(assessment['disposition']?.toString() ?? '', style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold, fontSize: 12)),
                    const SizedBox(width: 8),
                    Text(assessment['reason']?.toString() ?? '', style: const TextStyle(color: AppTheme.textDark, fontSize: 13)),
                  ],
                ),
                if (requiresReview)
                  const Padding(
                    padding: EdgeInsets.only(top: 4),
                    child: Text('Cần chuyên gia phê duyệt', style: TextStyle(color: AppTheme.warning, fontSize: 12, fontWeight: FontWeight.w600)),
                  ),
                Text('Chế độ: ${assessment['execution_mode']}', style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
              ],
            ),
          ),
          Text(assessment['status']?.toString() ?? '', style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _buildWeek13Section() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(14), border: Border.all(color: AppTheme.borderDark)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Expanded(child: Text('Week 13 Gate', style: TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.bold, fontSize: 16))),
              ElevatedButton(
                onPressed: () => controller.generateWeek13(stageId),
                style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: AppTheme.backgroundDarker),
                child: const Text('Tổng hợp bằng chứng'),
              ),
            ],
          ),
          Obx(() {
            final result = controller.week13Result.value;
            if (result == null) return const SizedBox.shrink();
            final facts = result['facts'] as Map<String, dynamic>? ?? {};
            final recommendation = result['ai_recommendation'] as Map<String, dynamic>?;
            return Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Commitment hoàn thành: ${facts['completed_commitments']}/${facts['total_commitments']}', style: const TextStyle(color: AppTheme.textMutedDark)),
                  Text('Số tài liệu bằng chứng: ${facts['evidence_document_count']}', style: const TextStyle(color: AppTheme.textMutedDark)),
                  if (recommendation != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        'AI khuyến nghị: ${recommendation['recommended_decision']} - ${recommendation['reasoning']}',
                        style: const TextStyle(color: AppTheme.primary),
                      ),
                    ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final decision in ['GO', 'ITERATE', 'HOLD', 'STOP', 'PIVOT'])
                        OutlinedButton(
                          onPressed: () => controller.confirmWeek13Decision(stageId, decision, 'Founder quyết định $decision tại Week 13'),
                          child: Text(decision),
                        ),
                    ],
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
