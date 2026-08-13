import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/strategy_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/theme/glassmorphism.dart';
import '../../../../core/widgets/app_modal_dialog.dart';

class OkrsTab extends GetView<StrategyController> {
  const OkrsTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      if (controller.isLoading.value) {
        return const Center(
          child: CircularProgressIndicator(color: AppTheme.primaryLight),
        );
      }

      return SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // OKR Section Header
            _buildOkrHeader(context),
            const SizedBox(height: 20),

            // Objectives List
            if (controller.objectives.isEmpty)
              _buildEmptyState(
                icon: Icons.track_changes_rounded,
                title: 'Chưa có Mục tiêu OKR nào',
                description: 'Thiết lập các mục tiêu kinh doanh quan trọng và kết quả then chốt đo lường được.',
                actionText: 'Tạo Mục tiêu OKR',
                onAction: () => _showCreateObjectiveDialog(context),
              )
            else
              Column(
                children: controller.objectives
                    .map((obj) => _buildObjectiveCard(context, obj))
                    .toList(),
              ),

            const SizedBox(height: 48),

            // 12-Week Execution Header
            _buildExecutionHeader(context),
            const SizedBox(height: 20),

            // Weekly Plans & Commitments List
            if (controller.weeklyPlans.isEmpty)
              _buildEmptyState(
                icon: Icons.calendar_month_rounded,
                title: 'Chưa có Kế hoạch tuần',
                description: 'Chia nhỏ mục tiêu lớn thành các kế hoạch thực thi 12 tuần với các cam kết cụ thể.',
                actionText: 'Tạo Kế hoạch Tuần 1',
                onAction: () => _showCreateWeeklyPlanDialog(context),
              )
            else
              Column(
                children: controller.weeklyPlans
                    .map((plan) => _buildPlanCard(context, plan))
                    .toList(),
              ),
          ],
        ),
      );
    });
  }

  Widget _buildOkrHeader(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppTheme.primary.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.flag_rounded, color: AppTheme.primaryLight, size: 22),
            ),
            const SizedBox(width: 14),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Mục tiêu & Kết quả Then chốt (OKR)',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                SizedBox(height: 2),
                Text(
                  'Theo dõi và đo lường tiến độ mục tiêu doanh nghiệp theo thời gian thực',
                  style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                ),
              ],
            ),
          ],
        ),
        Wrap(
          spacing: 12,
          children: [
            OutlinedButton.icon(
              onPressed: () => _showCreateCycleDialog(context),
              icon: const Icon(Icons.cached_rounded, size: 18),
              label: const Text('Chu kỳ OKR'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.white70,
                side: BorderSide(color: Colors.white.withValues(alpha: 0.2)),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
            ),
            OutlinedButton.icon(
              onPressed: controller.isGeneratingAi.value ? null : () => _showAiOkrModal(context),
              icon: controller.isGeneratingAi.value
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(color: AppTheme.primary, strokeWidth: 2),
                    )
                  : const Icon(Icons.auto_awesome_rounded, size: 18, color: AppTheme.primary),
              label: Text(
                controller.isGeneratingAi.value ? 'Đang sinh AI...' : 'Tạo tự động AI',
                style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold),
              ),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppTheme.primary),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
            ),
            ElevatedButton.icon(
              onPressed: () => _showCreateObjectiveDialog(context),
              icon: const Icon(Icons.add_rounded, size: 18),
              label: const Text('Thêm Objective'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: const Color(0xFF04070E),
                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildObjectiveCard(BuildContext context, dynamic obj) {
    final objectiveId = obj['id']?.toString() ?? '';
    final progress = controller.calculateObjectiveProgress(objectiveId);
    final keyResults = controller.getKeyResultsForObjective(objectiveId);
    final status = (obj['status'] ?? 'active').toString();

    return Obx(() {
      final isExpanded = controller.expandedObjectiveId.value == objectiveId;

      return Container(
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isExpanded
                ? AppTheme.primary
                : AppTheme.borderDark,
            width: isExpanded ? 1.5 : 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Objective Header Bar (Ultra Compact, Clickable to Toggle Accordion)
            InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () => controller.toggleObjectiveExpanded(objectiveId),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        // Left: Objective Title
                        Expanded(
                          child: Text(
                            obj['title'] ?? 'Mục tiêu chiến lược',
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                              height: 1.25,
                            ),
                          ),
                        ),
                        const SizedBox(width: 14),

                        // Right: KR Count + Active Status Icon + Expand Arrow + Menu
                        Row(
                          children: [
                            // KR count badge
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.08),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                '${keyResults.length} KR',
                                style: const TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.bold),
                              ),
                            ),
                            const SizedBox(width: 8),

                            // Active Status Icon on the right
                            Tooltip(
                              message: 'Trạng thái: ${status.toUpperCase()}',
                              child: const Icon(
                                Icons.check_circle_rounded,
                                color: Color(0xFF10B981),
                                size: 16,
                              ),
                            ),
                            const SizedBox(width: 8),

                            // Expand Arrow
                            Icon(
                              isExpanded ? Icons.keyboard_arrow_up_rounded : Icons.keyboard_arrow_down_rounded,
                              color: Colors.white70,
                              size: 20,
                            ),
                            const SizedBox(width: 4),

                            // Popup Menu
                            PopupMenuButton<String>(
                              icon: const Icon(Icons.more_vert_rounded, color: Colors.white54, size: 18),
                              color: AppTheme.surfaceDark,
                              itemBuilder: (ctx) => [
                                const PopupMenuItem(
                                  value: 'add_kr',
                                  child: Row(children: [Icon(Icons.add_chart_rounded, size: 16), SizedBox(width: 8), Text('Thêm Key Result')]),
                                ),
                                const PopupMenuItem(
                                  value: 'delete',
                                  child: Row(children: [Icon(Icons.delete_outline_rounded, color: AppTheme.accent, size: 16), SizedBox(width: 8), Text('Xóa Mục tiêu', style: TextStyle(color: AppTheme.accent))]),
                                ),
                              ],
                              onSelected: (val) {
                                if (val == 'add_kr') {
                                  _showCreateKeyResultDialog(context, objectiveId);
                                } else if (val == 'delete') {
                                  controller.deleteObjective(objectiveId);
                                }
                              },
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),

                    // Progress Bar
                    Row(
                      children: [
                        Expanded(
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(6),
                            child: LinearProgressIndicator(
                              value: progress,
                              backgroundColor: Colors.white10,
                              valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF818CF8)),
                              minHeight: 6,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          '${(progress * 100).toInt()}%',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF818CF8)),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),

            // Collapsible Key Results Section (Only visible whenExpanded)
            if (isExpanded) ...[
              const Divider(color: Colors.white12, height: 1),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.checklist_rounded, size: 15, color: Color(0xFF818CF8)),
                            const SizedBox(width: 6),
                            Text(
                              'DANH SÁCH KEY RESULTS (${keyResults.length} KR):',
                              style: const TextStyle(color: Color(0xFF818CF8), fontSize: 11, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                        TextButton.icon(
                          onPressed: () => _showCreateKeyResultDialog(context, objectiveId),
                          icon: const Icon(Icons.add_rounded, size: 14),
                          label: const Text('Thêm KR', style: TextStyle(fontSize: 11)),
                          style: TextButton.styleFrom(
                            foregroundColor: const Color(0xFF818CF8),
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    if (keyResults.isNotEmpty)
                      ...keyResults.map((kr) => _buildKeyResultItem(context, kr))
                    else
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.03),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Text(
                          'Chưa có Key Result nào cho Mục tiêu này. Bấm "+ Thêm KR" để bổ sung.',
                          style: TextStyle(color: Colors.white54, fontSize: 12),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ],
        ),
      );
    });
  }

  Widget _buildKeyResultItem(BuildContext context, dynamic kr) {
    final krId = kr['id']?.toString() ?? '';
    final current = (kr['current_value'] as num?)?.toDouble() ?? 0.0;
    final target = (kr['target_value'] as num?)?.toDouble() ?? 100.0;
    final unit = kr['unit'] ?? '%';
    final ratio = target > 0 ? (current / target).clamp(0.0, 1.0) : 0.0;

    String fmtNum(double val) {
      if (val == val.roundToDouble()) {
        return val.toInt().toString();
      }
      return val.toStringAsFixed(1);
    }

    final krTitle = kr['title'] ?? 'Đạt ${fmtNum(target)} $unit';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
      ),
      child: Row(
        children: [
          // Explicit [KR] Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: const Color(0xFF38BDF8).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.4)),
            ),
            child: const Text(
              'KR',
              style: TextStyle(color: Color(0xFF38BDF8), fontSize: 11, fontWeight: FontWeight.bold),
            ),
          ),
          const SizedBox(width: 12),

          // Key Result Title & Progress Subtext
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  krTitle,
                  style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 2),
                Text(
                  'Tiến độ: ${fmtNum(current)} / ${fmtNum(target)} ${unit.isNotEmpty ? unit : '%'}',
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.6), fontSize: 12),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),

          // Percentage & Progress Bar
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${(ratio * 100).toInt()}%',
                style: const TextStyle(color: AppTheme.secondaryLight, fontWeight: FontWeight.bold, fontSize: 12),
              ),
              const SizedBox(height: 4),
              SizedBox(
                width: 64,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: ratio,
                    backgroundColor: Colors.white10,
                    valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.secondaryLight),
                    minHeight: 5,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(width: 10),

          // Check-in & Delete buttons
          TextButton(
            onPressed: () => _showCheckinKeyResultDialog(context, kr),
            style: TextButton.styleFrom(
              foregroundColor: AppTheme.primaryLight,
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            ),
            child: const Text('Check-in', style: TextStyle(fontSize: 12)),
          ),
          IconButton(
            onPressed: () => controller.deleteKeyResult(krId),
            icon: const Icon(Icons.delete_outline_rounded, size: 16, color: Colors.white38),
            splashRadius: 16,
            tooltip: 'Xóa KR',
          ),
        ],
      ),
    );
  }

  Widget _buildExecutionHeader(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppTheme.secondary.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.calendar_month_rounded, color: AppTheme.secondaryLight, size: 22),
            ),
            const SizedBox(width: 14),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Kế hoạch Thực thi 12 Tuần & Chu kỳ 13 Tuần (mCOSA V12)',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                SizedBox(height: 2),
                Text(
                  'Stage-Gate Governance, Weekly Mission, phân bổ năng lực Founder & AI Delegation',
                  style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
                ),
              ],
            ),
          ],
        ),
        Row(
          children: [
            OutlinedButton.icon(
              onPressed: () => _showWeek13TransitionDialog(context),
              icon: const Icon(Icons.celebration_rounded, size: 16, color: Colors.pinkAccent),
              label: const Text('Tuần 13 & Kỷ Niệm', style: TextStyle(color: Colors.pinkAccent, fontSize: 13)),
              style: OutlinedButton.styleFrom(
                side: BorderSide(color: Colors.pink.withValues(alpha: 0.4)),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              ),
            ),
            const SizedBox(width: 8),
            OutlinedButton.icon(
              onPressed: () => _showCompileCycleDialog(context),
              icon: const Icon(Icons.bolt_rounded, size: 16, color: Colors.amberAccent),
              label: const Text('Compile V10', style: TextStyle(color: Colors.amberAccent, fontSize: 13)),
              style: OutlinedButton.styleFrom(
                side: BorderSide(color: Colors.amber.withValues(alpha: 0.4)),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              ),
            ),
            const SizedBox(width: 8),
            OutlinedButton.icon(
              onPressed: () => _showCycleGovernanceDialog(context),
              icon: const Icon(Icons.shield_outlined, size: 16, color: AppTheme.primaryLight),
              label: const Text('13-Week Stages & Gate', style: TextStyle(color: AppTheme.primaryLight, fontSize: 13)),
              style: OutlinedButton.styleFrom(
                side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.4)),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              ),
            ),
            const SizedBox(width: 10),
            ElevatedButton.icon(
              onPressed: () => _showCreateWeeklyPlanDialog(context),
              icon: const Icon(Icons.add_rounded, size: 18),
              label: const Text('Thêm Tuần mới'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.secondary,
                foregroundColor: const Color(0xFF04070E),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildPlanCard(BuildContext context, dynamic plan) {
    final planId = plan['id']?.toString() ?? '';
    final weekNo = plan['week_no'] ?? plan['week_number'] ?? 1;
    final focus = plan['focus'] ?? plan['theme'] ?? 'Trọng tâm tuần';
    final mission = plan['mission']?.toString();
    final outcomeScore = (plan['outcome_score'] as num?)?.toDouble();
    final commitments = controller.getCommitmentsForPlan(planId);

    return Glassmorphism(
      blur: 12,
      opacity: 0.12,
      color: AppTheme.surfaceDark,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: const Border(
            left: BorderSide(color: AppTheme.accentLight, width: 4),
          ),
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
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppTheme.accent.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text('TUẦN $weekNo', style: const TextStyle(color: AppTheme.accentLight, fontWeight: FontWeight.bold, fontSize: 12)),
                    ),
                    const SizedBox(width: 12),
                    Text(focus, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white)),
                  ],
                ),
                Row(
                  children: [
                    TextButton.icon(
                      onPressed: () => _showWeeklyReviewDialog(context, plan),
                      icon: const Icon(Icons.rate_review_outlined, size: 16, color: Colors.tealAccent),
                      label: const Text('Review', style: TextStyle(color: Colors.tealAccent)),
                    ),
                    const SizedBox(width: 4),
                    TextButton.icon(
                      onPressed: () => controller.compileWeeklyPlan(planId),
                      icon: const Icon(Icons.bolt_rounded, size: 16, color: Colors.amberAccent),
                      label: const Text('Compile', style: TextStyle(color: Colors.amberAccent)),
                    ),
                    const SizedBox(width: 4),
                    TextButton.icon(
                      onPressed: () => _showEditWeeklyMissionDialog(context, plan),
                      icon: const Icon(Icons.flag_circle_rounded, size: 16, color: AppTheme.primaryLight),
                      label: const Text('Mission', style: TextStyle(color: AppTheme.primaryLight)),
                    ),
                    const SizedBox(width: 4),
                    TextButton.icon(
                      onPressed: () => _showCreateCommitmentDialog(context, planId),
                      icon: const Icon(Icons.add_task_rounded, size: 16),
                      label: const Text('Cam kết', style: TextStyle(color: AppTheme.accentLight)),
                      style: TextButton.styleFrom(foregroundColor: AppTheme.accentLight),
                    ),
                  ],
                ),
              ],
            ),



            // Weekly Mission Banner
            if (mission != null && mission.isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.flag_rounded, size: 18, color: AppTheme.primaryLight),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Weekly Mission (Nhiệm vụ trọng điểm):', style: TextStyle(fontSize: 11, color: AppTheme.primaryLight, fontWeight: FontWeight.bold)),
                          const SizedBox(height: 2),
                          Text(mission, style: const TextStyle(fontSize: 13, color: Colors.white)),
                        ],
                      ),
                    ),
                    if (outcomeScore != null)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: (outcomeScore >= 0.7 ? Colors.green : Colors.orange).withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: outcomeScore >= 0.7 ? Colors.greenAccent : Colors.orangeAccent),
                        ),
                        child: Text(
                          'Outcome: ${(outcomeScore * 100).toInt()}%',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: outcomeScore >= 0.7 ? Colors.greenAccent : Colors.orangeAccent),
                        ),
                      ),
                  ],
                ),
              ),
            ],

            if (commitments.isNotEmpty) ...[
              const SizedBox(height: 12),
              ...commitments.map((c) {
                final isDone = c['status'] == 'done';
                final ownerType = c['commitment_owner_type'] ?? 'FOUNDER';
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    children: [
                      Checkbox(
                        value: isDone,
                        activeColor: AppTheme.success,
                        onChanged: (_) => controller.toggleCommitmentStatus(c['id'], c['status'] ?? 'todo'),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        margin: const EdgeInsets.only(right: 8),
                        decoration: BoxDecoration(
                          color: ownerType == 'AI_AGENT' ? Colors.cyan.withValues(alpha: 0.2) : Colors.purple.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: ownerType == 'AI_AGENT' ? Colors.cyanAccent.withValues(alpha: 0.5) : Colors.purpleAccent.withValues(alpha: 0.5)),
                        ),
                        child: Text(
                          ownerType,
                          style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: ownerType == 'AI_AGENT' ? Colors.cyanAccent : Colors.purpleAccent),
                        ),
                      ),
                      Expanded(
                        child: Text(
                          c['title'] ?? '',
                          style: TextStyle(
                            color: isDone ? Colors.white38 : Colors.white,
                            decoration: isDone ? TextDecoration.lineThrough : null,
                            fontSize: 14,
                          ),
                        ),
                      ),
                      IconButton(
                        onPressed: () => controller.deleteWeeklyCommitment(c['id']),
                        icon: const Icon(Icons.close_rounded, size: 16, color: Colors.white24),
                        splashRadius: 14,
                      ),
                    ],
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }


  Widget _buildEmptyState({
    required IconData icon,
    required String title,
    required String description,
    required String actionText,
    required VoidCallback onAction,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(36),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: AppTheme.primaryLight, size: 36),
          ),
          const SizedBox(height: 16),
          Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 6),
          Text(description, textAlign: TextAlign.center, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 14)),
          const SizedBox(height: 20),
          ElevatedButton.icon(
            onPressed: onAction,
            icon: const Icon(Icons.add_rounded, size: 18),
            label: Text(actionText),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primary,
              foregroundColor: const Color(0xFF04070E),
            ),
          ),
        ],
      ),
    );
  }

  // ====================================================================
  // Wide Modals
  // ====================================================================

  void _showCreateObjectiveDialog(BuildContext context) {
    final titleController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Tạo Mục Tiêu (Objective)',
      subtitle: 'Xác định mục tiêu định tính, truyền cảm hứng và rõ ràng cho tổ chức',
      icon: Icons.flag_rounded,
      maxWidth: 600,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: titleController,
            decoration: const InputDecoration(
              labelText: 'Tiêu đề Mục tiêu',
              hintText: 'Ví dụ: Tăng trưởng doanh thu định kỳ MRR vượt mốc 50,000 USD',
              prefixIcon: Icon(Icons.title_rounded, size: 20),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final title = titleController.text.trim();
            if (title.isEmpty) return;
            controller.createObjective(title);
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Tạo Mục tiêu'),
        ),
      ],
    );
  }

  void _showCreateKeyResultDialog(BuildContext context, String objectiveId) {
    final titleController = TextEditingController();
    final currentController = TextEditingController(text: '0');
    final targetController = TextEditingController(text: '100');
    final unitController = TextEditingController(text: '%');

    AppModalDialog.show(
      context: context,
      title: 'Thêm Kết Quả Then Chốt (Key Result)',
      subtitle: 'Xác định phát biểu kết quả đầu ra kèm theo các con số đo lường định lượng',
      icon: Icons.add_chart_rounded,
      maxWidth: 620,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: titleController,
            decoration: const InputDecoration(
              labelText: 'Phát biểu Kết quả (Key Result Statement)',
              hintText: 'Ví dụ: Tự động hóa 70% các tác vụ vận hành nghiệp vụ',
              prefixIcon: Icon(Icons.check_circle_outline_rounded, size: 20),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: currentController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Hiện tại'),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: TextField(
                  controller: targetController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Giá trị mục tiêu'),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: TextField(
                  controller: unitController,
                  decoration: const InputDecoration(labelText: 'Đơn vị', hintText: '%, USD, user...'),
                ),
              ),
            ],
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final title = titleController.text.trim();
            final curr = double.tryParse(currentController.text.trim()) ?? 0.0;
            final target = double.tryParse(targetController.text.trim()) ?? 100.0;
            final unit = unitController.text.trim();
            controller.createKeyResult(
              objectiveId: objectiveId,
              title: title.isNotEmpty ? title : 'Đạt $target ${unit.isNotEmpty ? unit : '%'}',
              baselineValue: 0.0,
              currentValue: curr,
              targetValue: target,
              unit: unit.isNotEmpty ? unit : '%',
            );
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Thêm Key Result'),
        ),
      ],
    );
  }

  void _showCheckinKeyResultDialog(BuildContext context, dynamic kr) {
    final currentVal = (kr['current_value'] as num?)?.toDouble() ?? 0.0;
    final valController = TextEditingController(text: currentVal.toString());

    AppModalDialog.show(
      context: context,
      title: 'Check-in Tiến Độ Key Result',
      subtitle: 'Cập nhật giá trị đo lường thực tế mới nhất',
      icon: Icons.edit_calendar_rounded,
      maxWidth: 520,
      content: TextField(
        controller: valController,
        keyboardType: TextInputType.number,
        decoration: InputDecoration(
          labelText: 'Giá trị hiện tại (${kr['unit'] ?? '%'})',
          prefixIcon: const Icon(Icons.speed_rounded, size: 20),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final newVal = double.tryParse(valController.text.trim());
            if (newVal != null) {
              controller.updateKeyResult(kr['id'], currentValue: newVal);
            }
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.secondary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Cập nhật'),
        ),
      ],
    );
  }

  void _showCreateWeeklyPlanDialog(BuildContext context) {
    final nextWeekNo = controller.weeklyPlans.length + 1;
    final focusController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Tạo Kế Hoạch Tuần $nextWeekNo',
      subtitle: 'Xác định mục tiêu và trọng tâm lớn nhất của tuần này',
      icon: Icons.calendar_month_rounded,
      maxWidth: 580,
      content: TextField(
        controller: focusController,
        decoration: const InputDecoration(
          labelText: 'Trọng tâm tuần (Focus)',
          hintText: 'Ví dụ: Tích hợp API Xác thực & Hoàn thiện luồng thanh toán',
          prefixIcon: Icon(Icons.center_focus_strong_rounded, size: 20),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final focus = focusController.text.trim();
            if (focus.isEmpty) return;
            controller.createWeeklyPlan(nextWeekNo, focus: focus);
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.secondary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Tạo Kế hoạch'),
        ),
      ],
    );
  }

  void _showCreateCommitmentDialog(BuildContext context, String planId) {
    final titleController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Thêm Cam Kết Tuần (Weekly Commitment)',
      subtitle: 'Hành động cụ thể cam kết hoàn thành để đạt trọng tâm tuần',
      icon: Icons.add_task_rounded,
      maxWidth: 560,
      content: TextField(
        controller: titleController,
        decoration: const InputDecoration(
          labelText: 'Nội dung cam kết',
          hintText: 'Ví dụ: Đóng gói và phát hành bản dựng macOS mới',
          prefixIcon: Icon(Icons.check_circle_outline_rounded, size: 20),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final title = titleController.text.trim();
            if (title.isEmpty) return;
            controller.createWeeklyCommitment(planId, title);
            Get.back();
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accent),
          child: const Text('Thêm Cam kết'),
        ),
      ],
    );
  }

  void _showCreateCycleDialog(BuildContext context) {
    final nameController = TextEditingController(text: 'Chu kỳ Thực thi 12 Tuần (Đợt ${DateTime.now().month ~/ 3 + 1})');

    AppModalDialog.show(
      context: context,
      title: 'Thiết Lập Chu Kỳ OKR 12 Tuần',
      subtitle: 'Đặt tên cho khung thời gian thực thi 12 tuần của doanh nghiệp (Mô hình 12-Week Year)',
      icon: Icons.cached_rounded,
      maxWidth: 560,
      content: TextField(
        controller: nameController,
        decoration: const InputDecoration(
          labelText: 'Tên chu kỳ thực thi 12 tuần',
          prefixIcon: Icon(Icons.label_outline_rounded, size: 20),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final name = nameController.text.trim();
            if (name.isEmpty) return;
            controller.createOkrCycle(name);
            Get.back();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
          ),
          child: const Text('Tạo Chu kỳ'),
        ),
      ],
    );
  }

  void _showAiOkrModal(BuildContext context) {
    int objectivesCount = 2;
    int krsPerObjectiveCount = 4;
    String? selectedCycleId;

    if (controller.okrCycles.isNotEmpty) {
      selectedCycleId = controller.okrCycles.first['id']?.toString();
    }

    AppModalDialog.show(
      context: context,
      title: 'Tạo tự động OKRs bằng AI',
      subtitle: 'Phân tích Nền tảng Doanh nghiệp và Chu kỳ để đề xuất các Mục tiêu & Kết quả Then chốt đo lường được.',
      icon: Icons.auto_awesome_rounded,
      maxWidth: 620,
      content: StatefulBuilder(
        builder: (context, setState) {
          final cyclesList = controller.okrCycles;

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 1. Objectives Count Selector (1 - 3 objectives)
                const Text(
                  'Số lượng Mục tiêu (Objectives) cần sinh:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                ),
                const SizedBox(height: 6),
                DropdownButtonFormField<int>(
                  initialValue: objectivesCount,
                  dropdownColor: AppTheme.surfaceDark,
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.format_list_numbered_rounded, size: 18),
                  ),
                  items: const [
                    DropdownMenuItem(value: 1, child: Text('1 Mục tiêu (Tập trung trọng điểm)')),
                    DropdownMenuItem(value: 2, child: Text('2 Mục tiêu (Cân bằng & Tối ưu - Mặc định)')),
                    DropdownMenuItem(value: 3, child: Text('3 Mục tiêu (Chi tiết toàn diện các chiều)')),
                  ],
                  onChanged: (v) {
                    if (v != null) setState(() => objectivesCount = v);
                  },
                ),
                const SizedBox(height: 16),

                // 2. Key Results Count Selector (2 - 5 KRs per objective)
                const Text(
                  'Số lượng Kết quả Then chốt (Key Results) / Mục tiêu:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                ),
                const SizedBox(height: 6),
                DropdownButtonFormField<int>(
                  initialValue: krsPerObjectiveCount,
                  dropdownColor: AppTheme.surfaceDark,
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.checklist_rounded, size: 18),
                  ),
                  items: const [
                    DropdownMenuItem(value: 2, child: Text('2 Key Results / Mục tiêu (Tinh gọn)')),
                    DropdownMenuItem(value: 3, child: Text('3 Key Results / Mục tiêu (Chuẩn OKRs - Mặc định)')),
                    DropdownMenuItem(value: 4, child: Text('4 Key Results / Mục tiêu (Nâng cao)')),
                    DropdownMenuItem(value: 5, child: Text('5 Key Results / Mục tiêu (Tối đa)')),
                  ],
                  onChanged: (v) {
                    if (v != null) setState(() => krsPerObjectiveCount = v);
                  },
                ),
                const SizedBox(height: 16),

                // 3. Cycle Selection (Optional)
                if (cyclesList.isNotEmpty) ...[
                  const Text(
                    'Chu kỳ OKR áp dụng:',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                  ),
                  const SizedBox(height: 6),
                  DropdownButtonFormField<String?>(
                    initialValue: selectedCycleId,
                    dropdownColor: AppTheme.surfaceDark,
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.cached_rounded, size: 18),
                    ),
                    items: cyclesList.map(
                      (c) => DropdownMenuItem<String?>(
                        value: c['id'].toString(),
                        child: Text('${c['name']} (${c['status'] ?? 'active'})'),
                      ),
                    ).toList(),
                    onChanged: (v) => setState(() => selectedCycleId = v),
                  ),
                  const SizedBox(height: 16),
                ],

                // Info hint box
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.lightbulb_outline_rounded, size: 16, color: AppTheme.primary),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Mỗi Mục tiêu sinh ra sẽ tự động kèm theo từ 2 đến 5 Kết quả Then chốt (Key Results) có chỉ số đo lường cụ thể.',
                          style: TextStyle(fontSize: 12, color: Colors.white70),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: const Text('Huỷ', style: TextStyle(color: Colors.white60)),
        ),
        const SizedBox(width: 12),
        ElevatedButton.icon(
          onPressed: () {
            Get.back();
            controller.generateAiOkrs(
              objectivesCount: objectivesCount,
              krsPerObjectiveCount: krsPerObjectiveCount,
              cycleId: selectedCycleId,
            );
          },
          icon: const Icon(Icons.auto_awesome_rounded, size: 16),
          label: const Text('Bắt đầu Sinh OKRs bằng AI'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          ),
        ),
      ],
    );
  }

  // ====================================================================
  // mCOSA V12 Stage-Gate Governance, Contract & Mission Dialogs (Sprint 3)
  // ====================================================================

  void _showCycleGovernanceDialog(BuildContext context) {
    String? currentCycleId;
    if (controller.twelveWeekCycles.isNotEmpty) {
      currentCycleId = controller.twelveWeekCycles.first['id']?.toString();
    }

    if (currentCycleId != null) {
      controller.loadCycleGovernance(currentCycleId);
    }

    AppModalDialog.show(
      context: context,
      title: 'Quản Trị Chu Kỳ 13 Tuần (13-Week Stages & Gate Governance)',
      subtitle: 'Khung kiểm soát giai đoạn thực thi, cổng đánh giá (Gate) và lưu vết bằng chứng',
      icon: Icons.shield_outlined,
      maxWidth: 780,
      content: StatefulBuilder(
        builder: (context, setState) {
          final stages = controller.cycleStages;
          final decisions = controller.gateDecisions;

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Các Giai Đoạn Chu Kỳ (Cycle Stages):', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.white)),
                    Row(
                      children: [
                        if (currentCycleId != null) ...[
                          OutlinedButton.icon(
                            onPressed: () => _showCycleContractDialog(context, currentCycleId!),
                            icon: const Icon(Icons.description_outlined, size: 14, color: AppTheme.secondaryLight),
                            label: const Text('Hợp đồng Chu kỳ', style: TextStyle(fontSize: 12, color: AppTheme.secondaryLight)),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton.icon(
                            onPressed: () async {
                              await controller.generateStandardStages(currentCycleId!);
                              setState(() {});
                            },
                            icon: const Icon(Icons.auto_fix_high_rounded, size: 14),
                            label: const Text('Sinh 5 Giai đoạn Chuẩn (13 Tuần)', style: TextStyle(fontSize: 12)),
                            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: const Color(0xFF04070E)),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (stages.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(12)),
                    child: const Center(child: Text('Chưa có giai đoạn nào. Nhấn "Sinh 5 Giai đoạn Chuẩn" để khởi tạo cấu trúc 13 tuần.', style: TextStyle(color: Colors.white70, fontSize: 13))),
                  )
                else
                  ...stages.map((s) => Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceDark.withValues(alpha: 0.6),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.white10),
                    ),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(color: AppTheme.secondary.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(6)),
                          child: Text('W${s['start_week']}-W${s['end_week']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: AppTheme.secondaryLight)),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(s['name'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white)),
                              if (s['purpose'] != null) Text(s['purpose'], style: const TextStyle(color: Colors.white60, fontSize: 11)),
                            ],
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(color: Colors.white10, borderRadius: BorderRadius.circular(4)),
                          child: Text(s['status'] ?? 'pending', style: const TextStyle(fontSize: 10, color: Colors.white70)),
                        ),
                      ],
                    ),
                  )),

                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Nhật Ký Quyết Định Cổng (Gate Decisions):', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.white)),
                    OutlinedButton.icon(
                      onPressed: () => _showGateDecisionDialog(context),
                      icon: const Icon(Icons.gavel_rounded, size: 14, color: AppTheme.accentLight),
                      label: const Text('Ghi Quyết định Cổng', style: TextStyle(fontSize: 12, color: AppTheme.accentLight)),
                      style: OutlinedButton.styleFrom(side: BorderSide(color: AppTheme.accent.withValues(alpha: 0.4))),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                if (decisions.isEmpty)
                  const Text('Chưa có quyết định cổng nào được ghi nhận trong chu kỳ này.', style: TextStyle(color: Colors.white54, fontSize: 12))
                else
                  ...decisions.take(5).map((d) => Container(
                    margin: const EdgeInsets.only(bottom: 6),
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.04), borderRadius: BorderRadius.circular(8)),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: (d['decision'] == 'GO' ? Colors.green : Colors.orange).withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(d['decision'] ?? '', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: d['decision'] == 'GO' ? Colors.greenAccent : Colors.orangeAccent)),
                            ),
                            const SizedBox(width: 8),
                            Text(d['rationale'] ?? '', style: const TextStyle(color: Colors.white, fontSize: 12)),
                          ],
                        ),
                        Text(d['decided_at']?.toString().split('T')[0] ?? '', style: const TextStyle(color: Colors.white38, fontSize: 11)),
                      ],
                    ),
                  )),
              ],
            ),
          );
        },
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Đóng', style: TextStyle(color: Colors.white60))),
      ],
    );
  }

  void _showGateDecisionDialog(BuildContext context) {
    String? selectedProjectId = controller.projects.isNotEmpty ? controller.projects.first['id']?.toString() : null;
    String decision = 'GO';
    final rationaleController = TextEditingController();
    final nextStepController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Ghi Nhận Quyết Định Cổng (Gate Decision)',
      subtitle: 'Đánh giá điều kiện vượt cổng kiểm soát (Stage-Gate) để tiếp tục, lặp lại hoặc dừng lại',
      icon: Icons.gavel_rounded,
      maxWidth: 640,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (controller.projects.isNotEmpty) ...[
              DropdownButtonFormField<String>(
                initialValue: selectedProjectId,
                dropdownColor: AppTheme.surfaceDark,
                decoration: const InputDecoration(labelText: 'Dự án áp dụng cổng kiểm soát'),
                items: controller.projects.map((p) => DropdownMenuItem(value: p['id'].toString(), child: Text(p['title'] ?? p['name'] ?? ''))).toList(),
                onChanged: (v) => setState(() => selectedProjectId = v),
              ),
              const SizedBox(height: 14),
            ],
            DropdownButtonFormField<String>(
              initialValue: decision,
              dropdownColor: AppTheme.surfaceDark,
              decoration: const InputDecoration(labelText: 'Quyết định Cổng (Decision)'),
              items: const [
                DropdownMenuItem(value: 'GO', child: Text('GO — Tiếp tục sang giai đoạn kế tiếp')),
                DropdownMenuItem(value: 'ITERATE', child: Text('ITERATE — Tái thử nghiệm & bổ sung bằng chứng')),
                DropdownMenuItem(value: 'HOLD', child: Text('HOLD — Tạm hoãn bảo lưu nguồn lực')),
                DropdownMenuItem(value: 'PIVOT', child: Text('PIVOT — Chuyển hướng chiến lược')),
                DropdownMenuItem(value: 'STOP', child: Text('STOP — Dừng dự án & thu hồi ngân sách')),
              ],
              onChanged: (v) => setState(() => decision = v ?? 'GO'),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: rationaleController,
              decoration: const InputDecoration(labelText: 'Lý do & Căn cứ phê duyệt', hintText: 'Đạt 100% mục tiêu đo lường...'),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: nextStepController,
              decoration: const InputDecoration(labelText: 'Chỉ đạo hành động tiếp theo', hintText: 'Tiến hành tuyển dụng 2 kỹ sư...'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            if (selectedProjectId == null || rationaleController.text.trim().isEmpty) return;
            Get.back();
            await controller.recordGateDecision(
              projectId: selectedProjectId!,
              decision: decision,
              rationale: rationaleController.text.trim(),
              nextStepInstructions: nextStepController.text.trim().isNotEmpty ? nextStepController.text.trim() : null,
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Lưu Quyết Định'),
        ),
      ],
    );
  }

  void _showCycleContractDialog(BuildContext context, String cycleId) {
    final defController = TextEditingController(text: 'Hoàn thành các mục tiêu chiến lược và bàn giao MVP đúng tiến độ');
    final capacityController = TextEditingController(text: '40');
    final bufferController = TextEditingController(text: '20');

    AppModalDialog.show(
      context: context,
      title: 'Hợp Đồng Chu Kỳ Thực Thi (Cycle Contract)',
      subtitle: 'Cam kết năng lực lãnh đạo, đệm dự phòng rủi ro và định nghĩa thành công (Success Definition)',
      icon: Icons.handshake_rounded,
      maxWidth: 620,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          children: [
            TextField(
              controller: defController,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Định nghĩa Thành công Chu kỳ (Success Definition)'),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: capacityController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Năng lực Founder (Giờ/tuần)'),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: TextField(
                    controller: bufferController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Đệm dự phòng rủi ro (%)'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () async {
            Get.back();
            await controller.upsertCycleContract(
              cycleId,
              successDefinition: defController.text.trim(),
              founderCapacityPerWeek: double.tryParse(capacityController.text) ?? 40.0,
              reservedBufferPercent: double.tryParse(bufferController.text) ?? 20.0,
              status: 'approved',
            );
          },
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.secondary, foregroundColor: const Color(0xFF04070E)),
          child: const Text('Ký Kết Hợp Đồng'),
        ),
      ],
    );
  }

  void _showEditWeeklyMissionDialog(BuildContext context, dynamic plan) {
    final planId = plan['id']?.toString() ?? '';
    final missionController = TextEditingController(text: plan['mission']?.toString() ?? '');
    double outcomeScore = (plan['outcome_score'] as num?)?.toDouble() ?? 0.8;

    AppModalDialog.show(
      context: context,
      title: 'Thiết Lập Weekly Mission (Tuần ${plan['week_no'] ?? plan['week_number'] ?? 1})',
      subtitle: 'Quy định nhiệm vụ cốt lõi duy nhất và đánh giá điểm số kết quả (Outcome Score)',
      icon: Icons.flag_circle_rounded,
      maxWidth: 580,
      content: StatefulBuilder(
        builder: (context, setState) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: missionController,
              decoration: const InputDecoration(
                labelText: 'Nhiệm vụ trọng điểm tuần (Weekly Mission)',
                hintText: 'Ví dụ: Đạt 10 cuộc phỏng vấn khách hàng tiềm năng và xác thực Pricing',
              ),
            ),
            const SizedBox(height: 18),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Điểm số Outcome (Hoàn thành mục tiêu):', style: TextStyle(color: Colors.white70, fontSize: 13)),
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
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
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
          child: const Text('Lưu Mission'),
        ),
      ],
    );
  }

  void _showCompileCycleDialog(BuildContext context) {
    String? currentCycleId;
    if (controller.twelveWeekCycles.isNotEmpty) {
      currentCycleId = controller.twelveWeekCycles.first['id']?.toString();
    }

    if (currentCycleId == null) {
      Get.snackbar('Thông báo', 'Chưa có chu kỳ 12 tuần nào để biên dịch', snackPosition: SnackPosition.BOTTOM);
      return;
    }

    controller.loadCycleCompilationStatus(currentCycleId);

    AppModalDialog.show(
      context: context,
      title: 'Biên Dịch Chu Kỳ Sang Runtime V10 (Planning Compiler)',
      subtitle: 'Tự động chuyển đổi các cam kết tuần (Weekly Commitments) thành Tác vụ (Tasks) và Milestones thành Mục tiêu (Outcomes)',
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
              child: const Row(
                children: [
                  Icon(Icons.info_outline_rounded, color: Colors.amberAccent, size: 20),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Planning Compiler đảm bảo chỉ biên dịch khi chu kỳ ở trạng thái ACTIVE (được phê duyệt). Quá trình biên dịch có tính Idempotent (không tạo trùng lặp).',
                      style: TextStyle(fontSize: 12, color: Colors.white70),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildStatBox('Tổng cam kết', '$totalCommitments', Colors.cyanAccent),
                _buildStatBox('Đã tạo Task V10', '$compiledTasks', Colors.greenAccent),
                _buildStatBox('Cột mốc Milestone', '$totalMilestones', Colors.purpleAccent),
              ],
            ),
          ],
        );
      }),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton.icon(
          onPressed: () async {
            Get.back();
            await controller.compileCycle(currentCycleId!);
          },

          icon: const Icon(Icons.bolt_rounded, size: 16),
          label: const Text('Bắt Đầu Biên Dịch (Compile)'),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.amber,
            foregroundColor: const Color(0xFF04070E),
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          ),
        ),
      ],
    );
  }

  Widget _buildStatBox(String label, String value, Color color) {
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

  // ====================================================================
  // mCOSA V12 Weekly Review & Week 13 Dialogs (Sprint 5)
  // ====================================================================

  void _showWeeklyReviewDialog(BuildContext context, dynamic plan) {
    final planId = plan['id']?.toString() ?? '';
    final cycleId = plan['cycle_id']?.toString() ?? (controller.twelveWeekCycles.isNotEmpty ? controller.twelveWeekCycles.first['id']?.toString() : null);
    if (cycleId == null) return;

    double execScore = (plan['execution_score'] as num?)?.toDouble() ?? 0.85;
    double outcomeScore = (plan['outcome_score'] as num?)?.toDouble() ?? 0.80;
    String recommendation = 'CONTINUE';
    final evidenceController = TextEditingController();
    final summaryController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Đánh Giá Tuần (Weekly Review — Tuần ${plan['week_no'] ?? plan['week_number'] ?? 1})',
      subtitle: 'Lưu vết bằng chứng đã học, xác thực giả định và đề xuất hướng đi tuần kế tiếp (Spec §17)',
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
                        Text('Điểm Thực thi (Execution): ${(execScore * 100).toInt()}%', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white70)),
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
                        Text('Điểm Kết quả (Outcome): ${(outcomeScore * 100).toInt()}%', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white70)),
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
                decoration: const InputDecoration(labelText: 'Khuyến nghị Hành động (Recommendation)'),
                items: const [
                  DropdownMenuItem(value: 'CONTINUE', child: Text('CONTINUE — Tiếp tục kế hoạch tuần tới theo lộ trình')),
                  DropdownMenuItem(value: 'DOUBLE_DOWN', child: Text('DOUBLE_DOWN — Tăng tốc gấp đôi vào kênh/tính năng hiệu quả')),
                  DropdownMenuItem(value: 'PIVOT_NEXT_WEEK', child: Text('PIVOT_NEXT_WEEK — Chuyển hướng mục tiêu tuần kế tiếp')),
                  DropdownMenuItem(value: 'RECALIBRATE_CAPACITY', child: Text('RECALIBRATE_CAPACITY — Tái cân bằng năng lực sáng lập')),
                ],
                onChanged: (v) => setState(() => recommendation = v ?? 'CONTINUE'),
              ),
              const SizedBox(height: 14),
              TextField(
                controller: evidenceController,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Bằng chứng thực tế đã học (Evidence Learned)',
                  hintText: 'Ví dụ: 8/10 người dùng đánh giá cao tính năng AI assisted import...',
                ),
              ),
              const SizedBox(height: 14),
              TextField(
                controller: summaryController,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Tóm tắt nhận định & bài học (Narrative Summary)',
                  hintText: 'Ví dụ: Năng lực tập trung của Founder đạt 38h, vượt mục tiêu 35h...',
                ),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
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
          child: const Text('Lưu Đánh Giá Tuần'),
        ),
      ],
    );
  }

  void _showWeek13TransitionDialog(BuildContext context) {
    String? currentCycleId;
    if (controller.twelveWeekCycles.isNotEmpty) {
      currentCycleId = controller.twelveWeekCycles.first['id']?.toString();
    }

    if (currentCycleId == null) {
      Get.snackbar('Thông báo', 'Chưa có chu kỳ 12 tuần nào để chuyển dịch', snackPosition: SnackPosition.BOTTOM);
      return;
    }

    controller.loadWeek13Readiness(currentCycleId);

    double overallExec = 0.90;
    double overallOutcome = 0.88;
    double okrRate = 0.85;
    final titleController = TextEditingController(text: 'Lễ Vinh Danh & Chuyển Dịch Chiến Lược Chu Kỳ');
    final learningsController = TextEditingController();
    final rewardsController = TextEditingController(text: 'Team retreat & Trao thưởng thành viên xuất sắc');

    AppModalDialog.show(
      context: context,
      title: 'Tuần 13 — Chuyển Dịch Chiến Lược & Lễ Kỷ Niệm (Week 13 Transition)',
      subtitle: 'Nghỉ ngơi, tôn vinh thành quả 12 tuần, tổng kết bài học và hoạch định chu kỳ kế tiếp (Spec §18–19)',
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
                          'Tiến độ chuẩn bị: Đã hoàn tất $completedReviews/$totalWeeks bản đánh giá tuần. Tuần 13 là bắt buộc để tái tạo năng lượng và cân bằng danh mục.',
                          style: const TextStyle(fontSize: 12, color: Colors.white70),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: titleController,
                  decoration: const InputDecoration(labelText: 'Tiêu đề Lễ Kỷ Niệm (Celebration Title)'),
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Điểm Thực thi Chu kỳ: ${(overallExec * 100).toInt()}%', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white70)),
                          Slider(value: overallExec, min: 0.0, max: 1.0, divisions: 20, activeColor: AppTheme.secondary, onChanged: (v) => setState(() => overallExec = v)),
                        ],
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Điểm Kết quả OKRs: ${(okrRate * 100).toInt()}%', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white70)),
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
                  decoration: const InputDecoration(
                    labelText: 'Bài học chiến lược cốt lõi (Strategic Learnings)',
                    hintText: 'Nhận định lớn nhất rút ra từ chu kỳ 12 tuần vừa qua...',
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: rewardsController,
                  decoration: const InputDecoration(
                    labelText: 'Phần thưởng & Nghi thức kỷ niệm (Rewards & Rituals)',
                  ),
                ),
              ],
            ),
          );
        },
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
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
          label: const Text('Hoàn Tất Chuyển Dịch Tuần 13'),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.pinkAccent,
            foregroundColor: const Color(0xFF04070E),
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          ),
        ),
      ],
    );
  }
}



