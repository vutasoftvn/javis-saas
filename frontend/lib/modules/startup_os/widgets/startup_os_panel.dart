import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/network/api_result.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/app_toast.dart';
import '../controllers/startup_os_controller.dart';
import '../models/onboard_dimension_fields.dart';
import '../models/startup_os_models.dart';
import 'create_goal_dialog.dart';
import 'onboard_wizard_dialog.dart';
import 'project_triage_dialog.dart';

/// Màn Startup OS (plan 2026-09-18 Phase 4): độ tươi ngữ cảnh 7 chiều, cây Goal
/// với tiến độ gộp, Goal cần rà soát giả định và dự án khám phá chờ triage.
class StartupOsPanel extends GetView<StartupOsController> {
  const StartupOsPanel({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (controller.isLoading.value &&
          controller.goalTree.isEmpty &&
          controller.cadences.isEmpty) {
        return const Center(child: CircularProgressIndicator());
      }
      return RefreshIndicator(
        onRefresh: controller.loadAll,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const ContextFreshnessCard(),
            const SizedBox(height: 16),
            const GoalTreeCard(),
            if (controller.pendingProjects.isNotEmpty || controller.projectsError.value != null) ...[
              const SizedBox(height: 16),
              const PendingProjectsCard(),
            ],
          ],
        ),
      );
    });
  }
}

class _SectionError extends StatelessWidget {
  const _SectionError(this.failure, {required this.onRetry});

  final ApiFailureDetail failure;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const Icon(Icons.error_outline, color: AppTheme.error, size: 18),
        const SizedBox(width: 8),
        Expanded(child: Text(startupOsFailureMessage(failure))),
        TextButton(onPressed: onRetry, child: const Text('Thử lại')),
      ],
    );
  }
}

Color freshnessColor(Freshness f) => switch (f) {
      Freshness.fresh => AppTheme.success,
      Freshness.dueSoon => AppTheme.info,
      Freshness.due => AppTheme.warning,
      Freshness.overdue || Freshness.missing => AppTheme.error,
    };

String freshnessLabel(DimensionCadence c) => switch (c.freshness) {
      Freshness.missing => 'Chưa ghi nhận',
      Freshness.overdue => 'Quá hạn (${c.daysSinceLastReview} ngày)',
      Freshness.due => 'Đến hạn (${c.daysSinceLastReview} ngày)',
      Freshness.dueSoon => 'Sắp đến hạn',
      Freshness.fresh => 'Mới cập nhật',
    };

Future<void> openOnboardWizard(BuildContext context, {required bool fullSetup}) async {
  final controller = Get.find<StartupOsController>();
  final outcome = await showDialog<OnboardSubmitOutcome>(
    context: context,
    builder: (_) => OnboardWizardDialog(controller: controller, fullSetup: fullSetup),
  );
  switch (outcome) {
    case OnboardSubmitted(:final dimensions):
      AppToast.success('Đã lưu ${dimensions.length} chiều và chốt snapshot ngữ cảnh.');
    case OnboardSubmitFailed(:final message):
      AppToast.error(message);
    case null:
      break;
  }
}

class ContextFreshnessCard extends GetView<StartupOsController> {
  const ContextFreshnessCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Obx(() {
          final cadences = controller.cadences;
          final error = controller.cadenceError.value;
          final reviewCount = controller.goalsNeedingReview.length;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 4,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  const Text('Độ tươi ngữ cảnh 7 chiều',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  if (reviewCount > 0)
                    Chip(
                      key: const Key('goals-needing-review-badge'),
                      backgroundColor: AppTheme.warning.withValues(alpha: 0.15),
                      label: Text('$reviewCount mục tiêu cần rà soát giả định'),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              if (error != null) _SectionError(error, onRetry: controller.loadAll),
              if (cadences.isEmpty && error == null)
                const Text('Chưa tải được trạng thái ngữ cảnh.'),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final c in cadences)
                    Chip(
                      key: Key('cadence-${c.dimension}'),
                      avatar: CircleAvatar(backgroundColor: freshnessColor(c.freshness), radius: 6),
                      label: Text(
                        '${dimensionTitle(c.dimension)} · ${freshnessLabel(c)}',
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  ElevatedButton.icon(
                    key: const Key('fast-update-button'),
                    icon: const Icon(Icons.bolt, size: 18),
                    label: const Text('Cập nhật nhanh (2 phút)'),
                    onPressed: () => openOnboardWizard(context, fullSetup: false),
                  ),
                  OutlinedButton.icon(
                    key: const Key('full-setup-button'),
                    icon: const Icon(Icons.assignment_outlined, size: 18),
                    label: const Text('Thiết lập đầy đủ 7 chiều'),
                    onPressed: () => openOnboardWizard(context, fullSetup: true),
                  ),
                ],
              ),
            ],
          );
        }),
      ),
    );
  }
}

class GoalTreeCard extends GetView<StartupOsController> {
  const GoalTreeCard({super.key});

  Future<void> _addGoal(BuildContext context) async {
    final stale = controller.staleFastDimensions;
    if (stale.isNotEmpty) {
      final choice = await showDialog<String>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Ngữ cảnh chưa cập nhật'),
          content: Text(
            'Các chiều ${stale.map((c) => dimensionTitle(c.dimension)).join(', ')} '
            'đang cũ hoặc chưa có. Mục tiêu sẽ gắn với snapshot ngữ cảnh hiện tại.',
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, 'continue'), child: const Text('Vẫn tạo mục tiêu')),
            ElevatedButton(onPressed: () => Navigator.pop(ctx, 'update'), child: const Text('Cập nhật nhanh trước')),
          ],
        ),
      );
      if (!context.mounted || choice == null) return;
      if (choice == 'update') {
        await openOnboardWizard(context, fullSetup: false);
        return;
      }
    }
    if (!context.mounted) return;
    final created = await showDialog<CreatedGoal>(
      context: context,
      builder: (_) => CreateGoalDialog(controller: controller),
    );
    if (created == null) return;
    if (created.cadenceWarnings.isEmpty) {
      AppToast.success('Đã tạo mục tiêu.');
    } else {
      AppToast.warning(
        'Đã tạo mục tiêu. ${created.cadenceWarnings.map((w) => w.message).join(' ')}',
      );
    }
  }

  Future<void> _complete(GoalNode goal) async {
    final result = await controller.completeGoal(goal.id);
    switch (result) {
      case ApiSuccess():
        AppToast.success('Đã hoàn thành "${goal.title}".');
      case ApiFailure(:final failure):
        AppToast.error(startupOsFailureMessage(failure));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Obx(() {
          final tree = controller.goalTree;
          final error = controller.treeError.value;
          final needingReview = {for (final g in controller.goalsNeedingReview) g.goalId};
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 4,
                alignment: WrapAlignment.spaceBetween,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  const Text('Cây mục tiêu', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  ElevatedButton.icon(
                    key: const Key('add-goal-button'),
                    style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary),
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('Thêm mục tiêu'),
                    onPressed: () => _addGoal(context),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              if (error != null) _SectionError(error, onRetry: controller.loadAll),
              if (tree.isEmpty && error == null)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Text('Chưa có mục tiêu nào. Bắt đầu với một Tầm nhìn hoặc mục tiêu Chiến lược.'),
                ),
              for (final node in tree)
                _GoalNodeTile(
                  node: node,
                  needingReview: needingReview,
                  onComplete: _complete,
                ),
            ],
          );
        }),
      ),
    );
  }
}

class _GoalNodeTile extends StatelessWidget {
  const _GoalNodeTile({required this.node, required this.needingReview, required this.onComplete});

  final GoalNode node;
  final Set<String> needingReview;
  final Future<void> Function(GoalNode) onComplete;

  @override
  Widget build(BuildContext context) {
    final progress = node.rollupProgress;
    final rollup = node.rollup;
    final subtitle = <String>[
      goalTypeLabel(node.goalType),
      if (node.status != 'active') node.status,
      if (node.startDate != null && node.endDate != null) '${node.startDate} → ${node.endDate}',
      '${node.objectiveCount} objective',
    ].join(' · ');

    final header = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: Text(node.title, style: const TextStyle(fontWeight: FontWeight.w600))),
            if (needingReview.contains(node.id))
              const Tooltip(
                message: 'Mục tiêu dựa trên snapshot ngữ cảnh cũ',
                child: Icon(Icons.history_toggle_off, color: AppTheme.warning, size: 18),
              ),
            if (node.isActive)
              IconButton(
                tooltip: 'Hoàn thành',
                icon: const Icon(Icons.check_circle_outline, size: 20),
                onPressed: () => onComplete(node),
              ),
          ],
        ),
        Text(subtitle, style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark)),
        const SizedBox(height: 6),
        if (progress == null)
          const Text('Chưa có Key Result', style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark))
        else
          Row(
            children: [
              Expanded(child: LinearProgressIndicator(value: progress, minHeight: 6)),
              const SizedBox(width: 8),
              Text('${rollup.achieved}/${rollup.total} KR', style: const TextStyle(fontSize: 12)),
            ],
          ),
      ],
    );

    if (node.children.isEmpty) {
      return Padding(
        key: Key('goal-${node.id}'),
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: header,
      );
    }
    return ExpansionTile(
      key: Key('goal-${node.id}'),
      initiallyExpanded: true,
      tilePadding: EdgeInsets.zero,
      childrenPadding: const EdgeInsets.only(left: 16),
      title: header,
      children: [
        for (final child in node.children)
          _GoalNodeTile(node: child, needingReview: needingReview, onComplete: onComplete),
      ],
    );
  }
}

class PendingProjectsCard extends GetView<StartupOsController> {
  const PendingProjectsCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Obx(() {
          final projects = controller.pendingProjects;
          final error = controller.projectsError.value;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Dự án khám phá chờ rà soát cuối chu kỳ',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 8),
              if (error != null) _SectionError(error, onRetry: controller.loadAll),
              if (projects.isNotEmpty)
                ElevatedButton.icon(
                  key: const Key('open-triage-button'),
                  icon: const Icon(Icons.fact_check_outlined, size: 18),
                  label: Text('Rà soát ${projects.length} dự án'),
                  onPressed: () => showDialog<void>(
                    context: context,
                    builder: (_) => ProjectTriageDialog(controller: controller),
                  ),
                ),
            ],
          );
        }),
      ),
    );
  }
}
