import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/strategy_controller.dart';
import '../../../../core/localization/app_translations.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../../../core/widgets/app_toast.dart';

class TwelveWyModals {
  static void showCreateWeeklyPlanDialog(BuildContext context, StrategyController controller) {
    final weekNoController = TextEditingController(text: '${controller.weeklyPlans.length + 1}');
    final focusController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: L10nKey.twelveWyCreatePlanTitle.tr,
      subtitle: L10nKey.twelveWyCreatePlanSubtitle.tr,
      icon: Icons.calendar_today_rounded,
      maxWidth: 540,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: weekNoController,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(
              labelText: L10nKey.twelveWyCreatePlanWeekNo.tr,
              hintText: '1, 2, 3...',
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: focusController,
            decoration: InputDecoration(
              labelText: L10nKey.twelveWyCreatePlanFocus.tr,
              hintText: L10nKey.twelveWyCreatePlanFocusHint.tr,
            ),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: Text(L10nKey.twelveWyCreatePlanCancel.tr, style: const TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final wNo = int.tryParse(weekNoController.text.trim()) ?? (controller.weeklyPlans.length + 1);
            final focus = focusController.text.trim();
            if (focus.isEmpty) return;
            controller.createWeeklyPlan(wNo, focus);
            Get.back();
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.secondary, foregroundColor: const Color(0xFF04070E)),
          child: Text(L10nKey.twelveWyCreatePlanSubmit.tr),
        ),
      ],
    );
  }

  static void showEditWeeklyMissionDialog(BuildContext context, StrategyController controller, dynamic plan) {
    final planId = plan['id']?.toString() ?? '';
    final missionController = TextEditingController(text: plan['mission']?.toString() ?? '');
    double outcomeScore = (plan['outcome_score'] as num?)?.toDouble() ?? 0.8;
    final weekNo = plan['week_no'] ?? plan['week_number'] ?? 1;

    AppModalDialog.show(
      context: context,
      title: '${L10nKey.twelveWyEditMissionTitle.tr} (${Get.locale?.languageCode == 'en' ? 'Week' : 'Tuần'} $weekNo)',
      subtitle: L10nKey.twelveWyEditMissionSubtitle.tr,
      icon: Icons.flag_circle_rounded,
      maxWidth: 580,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: missionController,
              decoration: InputDecoration(
                labelText: L10nKey.twelveWyEditMissionLabel.tr,
                hintText: L10nKey.twelveWyEditMissionHint.tr,
              ),
            ),
            const SizedBox(height: 18),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  L10nKey.twelveWyEditMissionOutcome.tr,
                  style: const TextStyle(color: Colors.white70, fontSize: 13),
                ),
                Text('${(outcomeScore * 100).toInt()}%', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.primaryLight)),
              ],
            ),
            Slider(
              value: outcomeScore,
              min: 0.0,
              max: 1.0,
              divisions: 20,
              activeColor: AppTheme.primary,
              onChanged: (v) => setState(() => outcomeScore = v),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: Text(L10nKey.twelveWyEditMissionCancel.tr, style: const TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            Get.back();
            await controller.updateWeeklyMission(
              planId,
              mission: missionController.text.trim(),
              outcomeScore: outcomeScore,
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: const Color(0xFF04070E)),
          child: Text(L10nKey.twelveWyEditMissionSave.tr),
        ),
      ],
    );
  }

  static void showCompileCycleDialog(BuildContext context, StrategyController controller) {
    String? currentCycleId;
    if (controller.twelveWeekCycles.isNotEmpty) {
      currentCycleId = controller.twelveWeekCycles.first['id']?.toString();
    }

    if (currentCycleId == null) {
      AppToast.warning(L10nKey.twelveWyCompileNoCycle.tr);
      return;
    }

    controller.loadCycleCompilationStatus(currentCycleId);

    AppModalDialog.show(
      context: context,
      title: L10nKey.twelveWyCompileTitle.tr,
      subtitle: L10nKey.twelveWyCompileSubtitle.tr,
      icon: Icons.bolt_rounded,
      maxWidth: 600,
      content: Obx(() {
        final status = controller.cycleCompilationStatus.value;
        final totalCommitments = status?['total_commitments'] ?? 0;
        final compiledTasks = status?['compiled_tasks_count'] ?? 0;
        final totalMilestones = status?['total_milestones'] ?? 0;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.amber.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.amber.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline_rounded, color: Colors.amberAccent, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      L10nKey.twelveWyCompileNote.tr,
                      style: const TextStyle(fontSize: 12, color: Colors.white70),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildStatBox(L10nKey.twelveWyCompileStatCommit.tr, '$totalCommitments', Colors.cyanAccent),
                _buildStatBox(L10nKey.twelveWyCompileStatTasks.tr, '$compiledTasks', Colors.greenAccent),
                _buildStatBox(L10nKey.twelveWyCompileStatMilestone.tr, '$totalMilestones', Colors.purpleAccent),
              ],
            ),
          ],
        );
      }),
      actions: [
        TextButton(onPressed: () => Get.back(), child: Text(L10nKey.twelveWyCompileCancel.tr, style: const TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton.icon(
          onPressed: () async {
            Get.back();
            await controller.compileCycle(currentCycleId!);
          },
          icon: const Icon(Icons.bolt_rounded, size: 16),
          label: Text(L10nKey.twelveWyCompileStart.tr),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.amber,
            foregroundColor: const Color(0xFF04070E),
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          ),
        ),
      ],
    );
  }

  static Widget _buildStatBox(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        children: [
          Text(value, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: color)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 11, color: Colors.white60)),
        ],
      ),
    );
  }

  static void showWeeklyReviewDialog(BuildContext context, StrategyController controller, dynamic plan) {
    final planId = plan['id']?.toString() ?? '';
    final cycleId = plan['cycle_id']?.toString() ?? (controller.twelveWeekCycles.isNotEmpty ? controller.twelveWeekCycles.first['id']?.toString() : null);
    if (cycleId == null) return;
    final weekNo = plan['week_no'] ?? plan['week_number'] ?? 1;

    double execScore = (plan['execution_score'] as num?)?.toDouble() ?? 0.85;
    double outcomeScore = (plan['outcome_score'] as num?)?.toDouble() ?? 0.80;
    String recommendation = 'CONTINUE';
    final evidenceController = TextEditingController();
    final summaryController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: '${L10nKey.twelveWyReviewTitle.tr} — ${Get.locale?.languageCode == 'en' ? 'Week' : 'Tuần'} $weekNo',
      subtitle: L10nKey.twelveWyReviewSubtitle.tr,
      icon: Icons.rate_review_rounded,
      maxWidth: 680,
      content: StatefulBuilder(
        builder: (context, setState) => SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${L10nKey.twelveWyReviewExecScore.tr} ${(execScore * 100).toInt()}%', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white70)),
                        Slider(
                          value: execScore,
                          min: 0.0,
                          max: 1.0,
                          divisions: 20,
                          activeColor: AppTheme.secondary,
                          onChanged: (v) => setState(() => execScore = v),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${L10nKey.twelveWyReviewOutcomeScore.tr} ${(outcomeScore * 100).toInt()}%', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white70)),
                        Slider(
                          value: outcomeScore,
                          min: 0.0,
                          max: 1.0,
                          divisions: 20,
                          activeColor: AppTheme.primary,
                          onChanged: (v) => setState(() => outcomeScore = v),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: recommendation,
                dropdownColor: AppTheme.surfaceDark,
                decoration: InputDecoration(labelText: L10nKey.twelveWyReviewRecommend.tr),
                items: const [
                  DropdownMenuItem(value: 'CONTINUE', child: Text('CONTINUE — Tiếp tục kế hoạch theo lộ trình')),
                  DropdownMenuItem(value: 'DOUBLE_DOWN', child: Text('DOUBLE_DOWN — Tăng tốc gấp đôi')),
                  DropdownMenuItem(value: 'PIVOT_NEXT_WEEK', child: Text('PIVOT_NEXT_WEEK — Chuyển hướng tuần tới')),
                  DropdownMenuItem(value: 'RECALIBRATE_CAPACITY', child: Text('RECALIBRATE_CAPACITY — Tái cân bằng năng lực')),
                ],
                onChanged: (v) => setState(() => recommendation = v ?? 'CONTINUE'),
              ),
              const SizedBox(height: 14),
              TextField(
                controller: evidenceController,
                maxLines: 2,
                decoration: InputDecoration(
                  labelText: L10nKey.twelveWyReviewEvidence.tr,
                  hintText: L10nKey.twelveWyReviewEvidenceHint.tr,
                ),
              ),
              const SizedBox(height: 14),
              TextField(
                controller: summaryController,
                maxLines: 2,
                decoration: InputDecoration(
                  labelText: L10nKey.twelveWyReviewSummary.tr,
                  hintText: L10nKey.twelveWyReviewSummaryHint.tr,
                ),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: Text(L10nKey.twelveWyReviewCancel.tr, style: const TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            Get.back();
            await controller.createWeeklyReview(
              cycleId,
              weeklyPlanId: planId,
              executionScore: execScore,
              outcomeScore: outcomeScore,
              evidenceLearned: evidenceController.text.trim().isNotEmpty ? evidenceController.text.trim() : null,
              narrativeSummary: summaryController.text.trim().isNotEmpty ? summaryController.text.trim() : null,
              recommendation: recommendation,
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.secondary, foregroundColor: const Color(0xFF04070E)),
          child: Text(L10nKey.twelveWyReviewSave.tr),
        ),
      ],
    );
  }

  static void showWeek13TransitionDialog(BuildContext context, StrategyController controller) {
    String? currentCycleId;
    if (controller.twelveWeekCycles.isNotEmpty) {
      currentCycleId = controller.twelveWeekCycles.first['id']?.toString();
    }

    if (currentCycleId == null) {
      AppToast.warning(L10nKey.twelveWyTransitionNoCycle.tr);
      return;
    }

    controller.loadWeek13Readiness(currentCycleId);

    double overallExec = 0.90;
    double overallOutcome = 0.88;
    double okrRate = 0.85;
    final titleController = TextEditingController(text: L10nKey.twelveWyTransitionCelebTitleDefault.tr);
    final learningsController = TextEditingController();
    final rewardsController = TextEditingController(text: L10nKey.twelveWyTransitionRewardsDefault.tr);

    AppModalDialog.show(
      context: context,
      title: L10nKey.twelveWyTransitionTitle.tr,
      subtitle: L10nKey.twelveWyTransitionSubtitle.tr,
      icon: Icons.celebration_rounded,
      maxWidth: 720,
      content: StatefulBuilder(
        builder: (context, setState) {
          final readiness = controller.week13Readiness.value;
          final completedReviews = readiness?['completed_weekly_reviews'] ?? 0;
          final totalWeeks = readiness?['total_weeks'] ?? 12;

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: Colors.pink.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.pink.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.info_outline_rounded, color: Colors.pinkAccent, size: 20),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          L10nKey.twelveWyTransitionReadiness.tr
                              .replaceAll('@count', '$completedReviews')
                              .replaceAll('@total', '$totalWeeks'),
                          style: const TextStyle(fontSize: 12, color: Colors.white70),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: titleController,
                  decoration: InputDecoration(labelText: L10nKey.twelveWyTransitionCelebTitle.tr),
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${L10nKey.twelveWyTransitionExecScore.tr} ${(overallExec * 100).toInt()}%', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white70)),
                          Slider(value: overallExec, min: 0.0, max: 1.0, divisions: 20, activeColor: AppTheme.secondary, onChanged: (v) => setState(() => overallExec = v)),
                        ],
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${L10nKey.twelveWyTransitionOkrScore.tr} ${(okrRate * 100).toInt()}%', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white70)),
                          Slider(value: okrRate, min: 0.0, max: 1.0, divisions: 20, activeColor: AppTheme.primary, onChanged: (v) => setState(() => okrRate = v)),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: learningsController,
                  maxLines: 2,
                  decoration: InputDecoration(
                    labelText: L10nKey.twelveWyTransitionLearnings.tr,
                    hintText: L10nKey.twelveWyTransitionLearningsHint.tr,
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: rewardsController,
                  decoration: InputDecoration(labelText: L10nKey.twelveWyTransitionRewards.tr),
                ),
              ],
            ),
          );
        },
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: Text(L10nKey.twelveWyTransitionCancel.tr, style: const TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton.icon(
          onPressed: () async {
            Get.back();
            await controller.finalizeWeek13(
              currentCycleId!,
              overallExecutionScore: overallExec,
              overallOutcomeScore: overallOutcome,
              okrAchievementRate: okrRate,
              celebrationTitle: titleController.text.trim(),
              strategicLearnings: learningsController.text.trim().isNotEmpty ? learningsController.text.trim() : null,
              rewardsOrRituals: rewardsController.text.trim().isNotEmpty ? rewardsController.text.trim() : null,
            );
          },
          icon: const Icon(Icons.celebration_rounded, size: 16),
          label: Text(L10nKey.twelveWyTransitionFinalize.tr),
          style: ElevatedButton.styleFrom(backgroundColor: Colors.pinkAccent, foregroundColor: const Color(0xFF04070E), padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12)),
        ),
      ],
    );
  }
}
