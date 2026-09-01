import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';
import '../controllers/project_orchestration_controller.dart';

/// Founder kickoff journey: brief đã có sẵn -> MVP roadmap (tạo/sửa thủ công hoặc AI)
/// -> founder sửa & xác nhận -> chọn 1 stage để lập kế hoạch & kích hoạt.
class ProjectKickoffView extends StatefulWidget {
  final String projectId;
  final VoidCallback onBack;
  final void Function(String stageId) onOpenStageWorkspace;

  const ProjectKickoffView({
    super.key,
    required this.projectId,
    required this.onBack,
    required this.onOpenStageWorkspace,
  });

  @override
  State<ProjectKickoffView> createState() => _ProjectKickoffViewState();
}

class _ProjectKickoffViewState extends State<ProjectKickoffView> {
  ProjectOrchestrationController get controller => Get.find<ProjectOrchestrationController>();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && widget.projectId.isNotEmpty) {
        controller.loadStages(widget.projectId);
      }
    });
  }

  @override
  void didUpdateWidget(covariant ProjectKickoffView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.projectId != widget.projectId && widget.projectId.isNotEmpty) {
      controller.loadStages(widget.projectId);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CosaFloatingAppBar(
            title: 'Lộ trình MVP (Roadmap)',
            subtitle: 'Đề xuất giai đoạn lộ trình thủ công hoặc bằng AI, lập kế hoạch OKR/12 tuần và kích hoạt từng giai đoạn.',
            icon: Icons.rocket_launch_outlined,
            actions: [
              TextButton.icon(
                onPressed: widget.onBack,
                icon: const Icon(Icons.arrow_back_rounded, size: 16, color: AppTheme.textMutedDark),
                label: const Text('Quay lại danh sách dự án', style: TextStyle(color: AppTheme.textMutedDark)),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: Obx(() {
              final error = controller.errorMessage.value;
              return SingleChildScrollView(
                padding: const EdgeInsets.symmetric(vertical: 4),
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
                        child: Row(
                          children: [
                            const Icon(Icons.error_outline_rounded, color: AppTheme.error, size: 18),
                            const SizedBox(width: 8),
                            Expanded(child: Text(error, style: const TextStyle(color: AppTheme.error))),
                          ],
                        ),
                      ),
                    _buildRoadmapDraftSection(),
                    const SizedBox(height: 24),
                    _buildConfirmedStagesSection(),
                  ],
                ),
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildRoadmapDraftSection() {
    return Obx(() {
      final draft = controller.roadmapDraft.value;
      final stageDrafts = (draft?['stages'] as List<dynamic>?) ?? const [];
      final hasConfirmed = controller.stages.isNotEmpty;
      final isDraftOpen = draft != null;

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
            // Header with title and quick actions
            Wrap(
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 8,
              runSpacing: 8,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      isDraftOpen
                          ? (hasConfirmed ? 'Chỉnh sửa Lộ trình MVP (Bản nháp)' : 'Lộ trình MVP (Bản nháp)')
                          : (hasConfirmed ? 'Lộ trình MVP (Đã xác nhận)' : 'Lộ trình MVP (Chưa khởi tạo)'),
                      style: const TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                    if (isDraftOpen) ...[
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppTheme.primary.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
                        ),
                        child: const Text('Chế độ soạn thảo', style: TextStyle(color: AppTheme.primary, fontSize: 11, fontWeight: FontWeight.w500)),
                      ),
                    ],
                  ],
                ),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    // Manual creation button
                    OutlinedButton.icon(
                      onPressed: () {
                        if (!isDraftOpen) {
                          if (hasConfirmed) {
                            controller.initDraftFromExisting();
                          } else {
                            controller.initEmptyDraft();
                          }
                        } else {
                          _showStageEditDialog(context, null, isNew: true);
                        }
                      },
                      icon: const Icon(Icons.edit_note_rounded, size: 16),
                      label: Text(isDraftOpen ? '+ Thêm giai đoạn' : (hasConfirmed ? 'Sửa thủ công' : 'Tạo thủ công')),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.textDark,
                        side: const BorderSide(color: AppTheme.borderDark),
                      ),
                    ),
                    // AI Prompt Custom button
                    OutlinedButton.icon(
                      onPressed: controller.isGeneratingRoadmap.value ? null : () => _showAiPromptDialog(context),
                      icon: const Icon(Icons.psychology_outlined, size: 16, color: AppTheme.primary),
                      label: const Text('AI kèm yêu cầu', style: TextStyle(color: AppTheme.primary)),
                      style: OutlinedButton.styleFrom(
                        side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.5)),
                      ),
                    ),
                    // Quick AI generate button
                    ElevatedButton.icon(
                      onPressed: controller.isGeneratingRoadmap.value ? null : () => controller.generateRoadmap(widget.projectId),
                      icon: controller.isGeneratingRoadmap.value
                          ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.backgroundDarker))
                          : const Icon(Icons.auto_awesome_rounded, size: 16),
                      label: Text(
                        controller.isGeneratingRoadmap.value
                            ? 'AI đang suy nghĩ...'
                            : (stageDrafts.isEmpty ? (hasConfirmed ? 'AI đề xuất lại' : 'AI đề xuất lộ trình') : 'AI đề xuất lại'),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primary,
                        foregroundColor: AppTheme.backgroundDarker,
                      ),
                    ),
                  ],
                ),
              ],
            ),

            if (!isDraftOpen || stageDrafts.isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 14, bottom: 4),
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceDarkLighter.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.borderDark.withValues(alpha: 0.5)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.info_outline_rounded, color: AppTheme.textMutedDark, size: 20),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          hasConfirmed
                              ? 'Dự án đã có ${controller.stages.length} giai đoạn đã xác nhận bên dưới. Bấm "Sửa thủ công" hoặc "AI đề xuất lại" nếu bạn muốn điều chỉnh hoặc tạo bộ giai đoạn mới.'
                              : 'Chưa có lộ trình nháp. Bạn có thể chọn "Tạo thủ công" để tự nhập giai đoạn hoặc bấm "AI đề xuất lộ trình" để AI tự động lên kế hoạch.',
                          style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13, height: 1.4),
                        ),
                      ),
                    ],
                  ),
                ),
              )
            else ...[
              const SizedBox(height: 16),
              for (int i = 0; i < stageDrafts.length; i++)
                _draftStageCard(
                  stageDrafts[i] as Map<String, dynamic>,
                  index: i,
                  totalStages: stageDrafts.length,
                ),
              const SizedBox(height: 12),
              // Bottom actions for adding stage and saving
              Wrap(
                alignment: WrapAlignment.spaceBetween,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 8,
                runSpacing: 8,
                children: [
                  OutlinedButton.icon(
                    onPressed: () => _showStageEditDialog(context, null, isNew: true),
                    icon: const Icon(Icons.add_rounded, size: 16),
                    label: const Text('Thêm giai đoạn mới'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.textDark,
                      side: const BorderSide(color: AppTheme.borderDark),
                    ),
                  ),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      if (hasConfirmed)
                        TextButton(
                          onPressed: () => controller.clearRoadmapDraft(),
                          child: const Text('Hủy soạn thảo', style: TextStyle(color: AppTheme.textMutedDark)),
                        ),
                      OutlinedButton(
                        onPressed: controller.isSaving.value
                            ? null
                            : () => controller.saveRoadmapDraft(
                                  widget.projectId,
                                  List<Map<String, dynamic>>.from(stageDrafts),
                                ),
                        child: const Text('Lưu nháp lộ trình'),
                      ),
                      ElevatedButton.icon(
                        onPressed: controller.isSaving.value
                            ? null
                            : () async {
                                final saved = await controller.saveRoadmapDraft(
                                  widget.projectId,
                                  List<Map<String, dynamic>>.from(stageDrafts),
                                );
                                if (saved) {
                                  await controller.confirmRoadmap(widget.projectId);
                                }
                              },
                        icon: const Icon(Icons.check_circle_outline_rounded, size: 16),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.success,
                          foregroundColor: Colors.white,
                        ),
                        label: const Text('Xác nhận Lộ trình'),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ],
        ),
      );
    });
  }

  Widget _draftStageCard(Map<String, dynamic> stage, {required int index, required int totalStages}) {
    final title = stage['title']?.toString() ?? 'Giai đoạn ${index + 1}';
    final hypothesis = stage['hypothesis']?.toString() ?? '';
    final scope = (stage['scope'] as List<dynamic>?) ?? [];
    final nonGoals = (stage['non_goals'] as List<dynamic>?) ?? [];
    final exitCriteria = (stage['exit_criteria'] as List<dynamic>?) ?? [];

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDarkLighter,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row of stage card
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: AppTheme.surfaceDark.withValues(alpha: 0.6),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(9)),
              border: Border(bottom: BorderSide(color: AppTheme.borderDark.withValues(alpha: 0.5))),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    '${index + 1}',
                    style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold, fontSize: 12),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.w600, fontSize: 15),
                  ),
                ),
                // Reorder and Action buttons
                if (index > 0)
                  IconButton(
                    icon: const Icon(Icons.arrow_upward_rounded, size: 16),
                    tooltip: 'Di chuyển lên',
                    color: AppTheme.textMutedDark,
                    onPressed: () => controller.moveDraftStage(index, index - 1),
                  ),
                if (index < totalStages - 1)
                  IconButton(
                    icon: const Icon(Icons.arrow_downward_rounded, size: 16),
                    tooltip: 'Di chuyển xuống',
                    color: AppTheme.textMutedDark,
                    onPressed: () => controller.moveDraftStage(index, index + 1),
                  ),
                IconButton(
                  icon: const Icon(Icons.edit_outlined, size: 16),
                  tooltip: 'Chỉnh sửa thủ công',
                  color: AppTheme.primary,
                  onPressed: () => _showStageEditDialog(context, stage, stageIndex: index),
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline_rounded, size: 16),
                  tooltip: 'Xoá giai đoạn',
                  color: AppTheme.error,
                  onPressed: () => controller.removeDraftStage(index),
                ),
              ],
            ),
          ),
          // Content
          Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (hypothesis.isNotEmpty) ...[
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.lightbulb_outline_rounded, size: 16, color: AppTheme.warning),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          hypothesis,
                          style: const TextStyle(color: AppTheme.textDark, fontSize: 13, height: 1.4),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                ],
                if (scope.isNotEmpty) ...[
                  const Text('Phạm vi (Scope):', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 11, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: scope.map((item) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppTheme.backgroundDarker,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: AppTheme.borderDark),
                      ),
                      child: Text('• $item', style: const TextStyle(color: AppTheme.textDark, fontSize: 12)),
                    )).toList(),
                  ),
                  const SizedBox(height: 8),
                ],
                if (exitCriteria.isNotEmpty) ...[
                  const Text('Tiêu chí hoàn thành (Exit criteria):', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 11, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: exitCriteria.map((item) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppTheme.success.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: AppTheme.success.withValues(alpha: 0.3)),
                      ),
                      child: Text('✓ $item', style: const TextStyle(color: AppTheme.success, fontSize: 12)),
                    )).toList(),
                  ),
                ],
                if (nonGoals.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  const Text('Ngoài phạm vi (Non-goals):', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 11, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: nonGoals.map((item) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppTheme.backgroundDarker,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: AppTheme.borderDark.withValues(alpha: 0.6)),
                      ),
                      child: Text('✕ $item', style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                    )).toList(),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConfirmedStagesSection() {
    return Obx(() {
      if (controller.stages.isEmpty) return const SizedBox.shrink();
      final isDraftOpen = controller.roadmapDraft.value != null;
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
                  child: Text(
                    'Các giai đoạn trong Lộ trình (Roadmap)',
                    style: TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                ),
                if (!isDraftOpen)
                  OutlinedButton.icon(
                    onPressed: () => controller.initDraftFromExisting(),
                    icon: const Icon(Icons.edit_note_rounded, size: 16),
                    label: const Text('Chỉnh sửa Lộ trình'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.textDark,
                      side: const BorderSide(color: AppTheme.borderDark),
                    ),
                  ),
              ],
            ),
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
    final hypothesis = stage['hypothesis']?.toString() ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDarkLighter,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: status == 'ACTIVE' ? AppTheme.success.withValues(alpha: 0.5) : AppTheme.borderDark,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: status == 'ACTIVE'
                  ? AppTheme.success.withValues(alpha: 0.15)
                  : AppTheme.primary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              'GĐ ${stage['sequence_no']}',
              style: TextStyle(
                color: status == 'ACTIVE' ? AppTheme.success : AppTheme.primary,
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        stage['title']?.toString() ?? '',
                        style: const TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.w600, fontSize: 14),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: status == 'ACTIVE'
                            ? AppTheme.success.withValues(alpha: 0.2)
                            : AppTheme.surfaceDark,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: status == 'ACTIVE' ? AppTheme.success : AppTheme.borderDark,
                        ),
                      ),
                      child: Text(
                        status,
                        style: TextStyle(
                          color: status == 'ACTIVE' ? AppTheme.success : AppTheme.textMutedDark,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
                if (hypothesis.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    hypothesis,
                    style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 12),
          if (status == 'CONFIRMED')
            ElevatedButton(
              onPressed: () => controller.planStage(widget.projectId, stageId),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: AppTheme.backgroundDarker,
              ),
              child: const Text('Lập kế hoạch'),
            ),
          if (status == 'CONFIRMED')
            Obx(() {
              final plan = controller.stagePlanDraft.value;
              if (plan == null) return const SizedBox.shrink();
              return Padding(
                padding: const EdgeInsets.only(left: 8),
                child: ElevatedButton(
                  onPressed: controller.isSaving.value ? null : () => controller.activateStage(widget.projectId, stageId),
                  style: ElevatedButton.styleFrom(backgroundColor: AppTheme.success, foregroundColor: Colors.white),
                  child: const Text('Kích hoạt'),
                ),
              );
            }),
          if (status == 'ACTIVE')
            ElevatedButton.icon(
              onPressed: () => widget.onOpenStageWorkspace(stageId),
              icon: const Icon(Icons.launch_rounded, size: 16),
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.success, foregroundColor: Colors.white),
              label: const Text('Vào không gian làm việc'),
            ),
        ],
      ),
    );
  }

  // Dialog for editing/creating a single stage
  void _showStageEditDialog(BuildContext context, Map<String, dynamic>? initialStage, {int? stageIndex, bool isNew = false}) {
    final titleCtrl = TextEditingController(text: initialStage?['title']?.toString() ?? '');
    final hypothesisCtrl = TextEditingController(text: initialStage?['hypothesis']?.toString() ?? '');

    final scopeItems = List<String>.from((initialStage?['scope'] as List<dynamic>?)?.map((e) => e.toString()) ?? []).obs;
    final nonGoalsItems = List<String>.from((initialStage?['non_goals'] as List<dynamic>?)?.map((e) => e.toString()) ?? []).obs;
    final exitCriteriaItems = List<String>.from((initialStage?['exit_criteria'] as List<dynamic>?)?.map((e) => e.toString()) ?? []).obs;

    final newScopeCtrl = TextEditingController();
    final newNonGoalCtrl = TextEditingController();
    final newExitCriteriaCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: AppTheme.borderDark)),
        title: Row(
          children: [
            Icon(isNew ? Icons.add_circle_outline_rounded : Icons.edit_note_rounded, color: AppTheme.primary, size: 22),
            const SizedBox(width: 10),
            Text(
              isNew ? 'Thêm Giai đoạn mới' : 'Chỉnh sửa Giai đoạn',
              style: const TextStyle(color: AppTheme.textDark, fontSize: 17, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        content: SizedBox(
          width: 550,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Title
                const Text('Tên giai đoạn *', style: TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.w600, fontSize: 13)),
                const SizedBox(height: 6),
                TextField(
                  controller: titleCtrl,
                  style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
                  decoration: InputDecoration(
                    hintText: 'Ví dụ: Phát triển nguyên mẫu đăng nhập và onboarding',
                    hintStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                    filled: true,
                    fillColor: AppTheme.backgroundDarker,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppTheme.borderDark)),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  ),
                ),
                const SizedBox(height: 14),

                // Hypothesis
                const Text('Giả thuyết kiểm chứng (Hypothesis)', style: TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.w600, fontSize: 13)),
                const SizedBox(height: 6),
                TextField(
                  controller: hypothesisCtrl,
                  maxLines: 3,
                  style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
                  decoration: InputDecoration(
                    hintText: 'Mô tả giả thuyết cốt lõi cần kiểm chứng trong giai đoạn này...',
                    hintStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                    filled: true,
                    fillColor: AppTheme.backgroundDarker,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppTheme.borderDark)),
                    contentPadding: const EdgeInsets.all(12),
                  ),
                ),
                const SizedBox(height: 16),

                // Scope List Editor
                _buildListEditor(
                  title: 'Phạm vi công việc (Scope)',
                  items: scopeItems,
                  inputCtrl: newScopeCtrl,
                  hintText: 'Nhập công việc và bấm Thêm...',
                  itemColor: AppTheme.primary,
                ),
                const SizedBox(height: 16),

                // Exit Criteria List Editor
                _buildListEditor(
                  title: 'Tiêu chí hoàn thành (Exit Criteria)',
                  items: exitCriteriaItems,
                  inputCtrl: newExitCriteriaCtrl,
                  hintText: 'Nhập tiêu chí nghiệm thu và bấm Thêm...',
                  itemColor: AppTheme.success,
                ),
                const SizedBox(height: 16),

                // Non-Goals List Editor
                _buildListEditor(
                  title: 'Ngoài phạm vi (Non-goals)',
                  items: nonGoalsItems,
                  inputCtrl: newNonGoalCtrl,
                  hintText: 'Nhập việc KHÔNG làm trong giai đoạn này...',
                  itemColor: AppTheme.textMutedDark,
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Hủy', style: TextStyle(color: AppTheme.textMutedDark)),
          ),
          ElevatedButton(
            onPressed: () {
              final title = titleCtrl.text.trim();
              if (title.isEmpty) {
                Get.snackbar('Lỗi', 'Vui lòng nhập tên giai đoạn', snackPosition: SnackPosition.BOTTOM);
                return;
              }
              final stageData = {
                'title': title,
                'hypothesis': hypothesisCtrl.text.trim(),
                'scope': scopeItems.toList(),
                'non_goals': nonGoalsItems.toList(),
                'exit_criteria': exitCriteriaItems.toList(),
              };

              if (isNew || stageIndex == null) {
                controller.addDraftStage(initialData: stageData);
              } else {
                controller.updateDraftStage(stageIndex, stageData);
              }
              Navigator.of(ctx).pop();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primary,
              foregroundColor: AppTheme.backgroundDarker,
            ),
            child: Text(isNew ? 'Thêm giai đoạn' : 'Lưu thay đổi'),
          ),
        ],
      ),
    );
  }

  Widget _buildListEditor({
    required String title,
    required RxList<String> items,
    required TextEditingController inputCtrl,
    required String hintText,
    required Color itemColor,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.w600, fontSize: 13)),
        const SizedBox(height: 6),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: inputCtrl,
                style: const TextStyle(color: AppTheme.textDark, fontSize: 13),
                decoration: InputDecoration(
                  hintText: hintText,
                  hintStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
                  filled: true,
                  fillColor: AppTheme.backgroundDarker,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppTheme.borderDark)),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                ),
                onSubmitted: (val) {
                  if (val.trim().isNotEmpty) {
                    items.add(val.trim());
                    inputCtrl.clear();
                  }
                },
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              icon: const Icon(Icons.add_rounded, size: 20),
              color: AppTheme.primary,
              style: IconButton.styleFrom(
                backgroundColor: AppTheme.surfaceDarkLighter,
                side: const BorderSide(color: AppTheme.borderDark),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              onPressed: () {
                if (inputCtrl.text.trim().isNotEmpty) {
                  items.add(inputCtrl.text.trim());
                  inputCtrl.clear();
                }
              },
            ),
          ],
        ),
        const SizedBox(height: 6),
        Obx(() {
          if (items.isEmpty) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: 4),
              child: Text('Chưa có mục nào', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontStyle: FontStyle.italic)),
            );
          }
          return Wrap(
            spacing: 6,
            runSpacing: 6,
            children: items.map((item) => Chip(
              backgroundColor: itemColor.withValues(alpha: 0.12),
              side: BorderSide(color: itemColor.withValues(alpha: 0.3)),
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
              label: Text(item, style: TextStyle(color: itemColor, fontSize: 12)),
              deleteIcon: Icon(Icons.close_rounded, size: 14, color: itemColor),
              onDeleted: () => items.remove(item),
            )).toList(),
          );
        }),
      ],
    );
  }

  // Dialog for AI prompt / instruction
  void _showAiPromptDialog(BuildContext context) {
    final promptCtrl = TextEditingController();
    final suggestions = [
      'Tập trung phát triển MVP B2B tinh gọn',
      'Chia thành 3 giai đoạn ngắn hạn 4 tuần',
      'Ưu tiên bảo mật dữ liệu và tích hợp SSO',
      'Tập trung trải nghiệm người dùng và chuyển đổi nhanh',
    ];

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: AppTheme.borderDark)),
        title: const Row(
          children: [
            Icon(Icons.auto_awesome_rounded, color: AppTheme.primary, size: 22),
            SizedBox(width: 10),
            Text(
              'AI Đề xuất / Tinh chỉnh Lộ trình',
              style: TextStyle(color: AppTheme.textDark, fontSize: 17, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        content: SizedBox(
          width: 520,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Nhập hướng dẫn hoặc yêu cầu cụ thể để AI tối ưu hóa các giai đoạn lộ trình cho dự án:',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13, height: 1.4),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: promptCtrl,
                maxLines: 4,
                style: const TextStyle(color: AppTheme.textDark, fontSize: 14),
                decoration: InputDecoration(
                  hintText: 'Ví dụ: Hãy chia lộ trình thành 2 giai đoạn chính, giai đoạn 1 tập trung hoàn toàn vào xác thực người dùng và thanh toán...',
                  hintStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                  filled: true,
                  fillColor: AppTheme.backgroundDarker,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: AppTheme.borderDark)),
                  contentPadding: const EdgeInsets.all(12),
                ),
              ),
              const SizedBox(height: 12),
              const Text('Gợi ý nhanh:', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontWeight: FontWeight.w600)),
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: suggestions.map((s) => ActionChip(
                  backgroundColor: AppTheme.surfaceDarkLighter,
                  side: const BorderSide(color: AppTheme.borderDark),
                  label: Text(s, style: const TextStyle(color: AppTheme.textDark, fontSize: 11)),
                  onPressed: () {
                    promptCtrl.text = s;
                  },
                )).toList(),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Hủy', style: TextStyle(color: AppTheme.textMutedDark)),
          ),
          ElevatedButton.icon(
            onPressed: () {
              final instruction = promptCtrl.text.trim();
              Navigator.of(ctx).pop();
              controller.generateRoadmap(widget.projectId, instruction: instruction.isNotEmpty ? instruction : null);
            },
            icon: const Icon(Icons.auto_awesome_rounded, size: 16),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primary,
              foregroundColor: AppTheme.backgroundDarker,
            ),
            label: const Text('Bắt đầu AI tạo lộ trình'),
          ),
        ],
      ),
    );
  }
}
