import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/strategy_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/glassmorphism.dart';
import '../../../core/widgets/app_modal_dialog.dart';
import '../../../core/widgets/floating_app_bar.dart';

class TwelveWeekYearView extends GetView<StrategyController> {
  const TwelveWeekYearView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<StrategyController>()) {
      Get.put(StrategyController());
    }

    return Container(
      color: Colors.transparent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Top Floating AppBar Card
          JavisFloatingAppBar(
            title: 'Kế hoạch Thực thi 12 Tuần (12WY)',
            subtitle: 'Stage-Gate Governance, Weekly Mission, phân bổ năng lực Founder & AI Delegation theo mô hình 12 Week Year.',
            actions: [
              OutlinedButton.icon(
                onPressed: () => _showWeek13TransitionDialog(context),
                icon: const Icon(Icons.celebration_rounded, size: 16, color: Colors.pinkAccent),
                label: const Text('Tuần 13 & Kỷ Niệm', style: TextStyle(color: Colors.pinkAccent, fontSize: 13)),
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: Colors.pink.withValues(alpha: 0.4)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                onPressed: () => _showCompileCycleDialog(context),
                icon: const Icon(Icons.bolt_rounded, size: 16, color: Colors.amberAccent),
                label: const Text('Compile V10', style: TextStyle(color: Colors.amberAccent, fontSize: 13)),
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: Colors.amber.withValues(alpha: 0.4)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                onPressed: () => _showCycleGovernanceDialog(context),
                icon: const Icon(Icons.shield_outlined, size: 16, color: AppTheme.primaryLight),
                label: const Text('13-Week Stages & Gate', style: TextStyle(color: AppTheme.primaryLight, fontSize: 13)),
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.4)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: () => _showCreateWeeklyPlanDialog(context),
                icon: const Icon(Icons.add_rounded, size: 16),
                label: const Text('Thêm Tuần mới'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.secondary,
                  foregroundColor: const Color(0xFF04070E),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
            ],
          ),

          // 2. 12WY Content Body
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value) {
                return const Center(
                  child: CircularProgressIndicator(color: AppTheme.secondaryLight),
                );
              }

              final activeCycle = controller.twelveWeekCycles.isNotEmpty
                  ? controller.twelveWeekCycles.first as Map<String, dynamic>
                  : null;

              return SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Active Cycle Banner
                    if (activeCycle != null)
                      _buildCycleHeader(context, activeCycle),

                    // Weekly Plans & Commitments List
                    if (controller.weeklyPlans.isEmpty)
                      _buildEmptyState(context)
                    else
                      Column(
                        children: controller.weeklyPlans
                            .map((plan) => _buildPlanCard(context, plan))
                            .toList(),
                      ),
                  ],
                ),
              );
            }),
          ),
        ],
      ),
    );
  }

  Widget _buildCycleHeader(BuildContext context, Map<String, dynamic> cycle) {
    final theme = cycle['theme']?.toString() ?? 'Chu kỳ thực thi 12 tuần';
    final durationWeeks = cycle['duration_weeks'] ?? 12;
    final startDateStr = cycle['start_date']?.toString();
    final endDateStr = cycle['end_date']?.toString();

    String dateRange = '';
    if (startDateStr != null && startDateStr.isNotEmpty) {
      try {
        final startDt = DateTime.parse(startDateStr);
        final startFmt = '${startDt.day.toString().padLeft(2, '0')}/${startDt.month.toString().padLeft(2, '0')}/${startDt.year}';
        if (endDateStr != null && endDateStr.isNotEmpty) {
          final endDt = DateTime.parse(endDateStr);
          final endFmt = '${endDt.day.toString().padLeft(2, '0')}/${endDt.month.toString().padLeft(2, '0')}/${endDt.year}';
          dateRange = 'Thứ 2, $startFmt – CN, $endFmt ($durationWeeks tuần)';
        } else {
          dateRange = 'Từ Thứ 2, $startFmt ($durationWeeks tuần)';
        }
      } catch (_) {}
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.25)),
        gradient: LinearGradient(
          colors: [
            AppTheme.primary.withValues(alpha: 0.08),
            AppTheme.surfaceDark,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.rocket_launch_rounded, color: AppTheme.primary, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        theme,
                        style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.greenAccent.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: Colors.greenAccent.withValues(alpha: 0.3)),
                      ),
                      child: const Text('Đang thực thi', style: TextStyle(color: Colors.greenAccent, fontSize: 11, fontWeight: FontWeight.w600)),
                    ),
                  ],
                ),
                if (dateRange.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.calendar_month_outlined, size: 13, color: AppTheme.textMutedDark),
                      const SizedBox(width: 6),
                      Text(dateRange, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12.5)),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 40),
        padding: const EdgeInsets.all(32),
        constraints: const BoxConstraints(maxWidth: 520),
        decoration: BoxDecoration(
          color: AppTheme.surfaceDark,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.borderDark),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.secondary.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.calendar_month_rounded, size: 36, color: AppTheme.secondary),
            ),
            const SizedBox(height: 16),
            const Text(
              'Chưa có Kế hoạch Tuần nào',
              style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Bạn có thể kích hoạt từ Lộ trình MVP để tự động phân bổ kế hoạch các tuần, hoặc tạo tuần thực thi đầu tiên (mặc định bắt đầu từ Thứ Hai).',
              style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13, height: 1.4),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: () => _showCreateWeeklyPlanDialog(context),
              icon: const Icon(Icons.add_rounded, size: 16),
              label: const Text('Tạo Kế hoạch Tuần 1'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.secondary,
                foregroundColor: const Color(0xFF04070E),
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlanCard(BuildContext context, dynamic plan) {
    final planId = plan['id']?.toString() ?? '';
    final weekNo = plan['week_no'] ?? plan['week_number'] ?? 1;
    final focus = plan['focus'] ?? plan['theme'] ?? 'Trọng tâm tuần';
    final mission = plan['mission']?.toString();
    final outcomeScore = (plan['outcome_score'] as num?)?.toDouble();
    final commitments = controller.getCommitmentsForPlan(planId);

    final startDateStr = plan['start_date']?.toString();
    final endDateStr = plan['end_date']?.toString();

    String? dateRangeText;
    if (startDateStr != null && startDateStr.isNotEmpty) {
      try {
        final startDt = DateTime.parse(startDateStr);
        final endDt = (endDateStr != null && endDateStr.isNotEmpty)
            ? DateTime.parse(endDateStr)
            : startDt.add(const Duration(days: 6));
        final startFmt = '${startDt.day.toString().padLeft(2, '0')}/${startDt.month.toString().padLeft(2, '0')}';
        final endFmt = '${endDt.day.toString().padLeft(2, '0')}/${endDt.month.toString().padLeft(2, '0')}/${endDt.year}';
        dateRangeText = 'Thứ 2, $startFmt – CN, $endFmt';
      } catch (_) {}
    }

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
                Expanded(
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppTheme.accent.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text('TUẦN $weekNo', style: const TextStyle(color: AppTheme.accentLight, fontWeight: FontWeight.bold, fontSize: 12)),
                      ),
                      if (dateRangeText != null) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.05),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.calendar_today_outlined, size: 11, color: AppTheme.textMutedDark),
                              const SizedBox(width: 4),
                              Text(
                                dateRangeText,
                                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 11, fontWeight: FontWeight.w500),
                              ),
                            ],
                          ),
                        ),
                      ],
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          focus,
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
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



  void _showCreateWeeklyPlanDialog(BuildContext context) {
    final nextWeekNo = controller.weeklyPlans.length + 1;
    final focusController = TextEditingController();

    // Default start date: calculate Monday for this week number
    final now = DateTime.now();
    DateTime startDate = DateTime(now.year, now.month, now.day)
        .subtract(Duration(days: now.weekday - 1))
        .add(Duration(days: (nextWeekNo - 1) * 7));
    DateTime endDate = startDate.add(const Duration(days: 6));

    AppModalDialog.show(
      context: context,
      title: 'Tạo Kế Hoạch Tuần $nextWeekNo',
      subtitle: 'Xác định mục tiêu và thời gian thực thi (mặc định từ Thứ Hai đến Chủ Nhật)',
      icon: Icons.calendar_month_rounded,
      maxWidth: 580,
      content: StatefulBuilder(
        builder: (context, setModalState) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                controller: focusController,
                autofocus: true,
                style: const TextStyle(color: AppTheme.textDark),
                decoration: const InputDecoration(
                  labelText: 'Trọng tâm tuần (Focus)',
                  hintText: 'Ví dụ: Tích hợp API Xác thực & Hoàn thiện luồng thanh toán',
                  prefixIcon: Icon(Icons.center_focus_strong_rounded, size: 20),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Bắt đầu (Thứ Hai)', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12.5)),
                        const SizedBox(height: 6),
                        InkWell(
                          onTap: () async {
                            final picked = await showDatePicker(
                              context: context,
                              initialDate: startDate,
                              firstDate: DateTime(2020),
                              lastDate: DateTime(2035),
                            );
                            if (picked != null) {
                              final pickedMonday = picked.subtract(Duration(days: picked.weekday - 1));
                              setModalState(() {
                                startDate = pickedMonday;
                                endDate = startDate.add(const Duration(days: 6));
                              });
                            }
                          },
                          borderRadius: BorderRadius.circular(10),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                            decoration: BoxDecoration(
                              color: AppTheme.surfaceDarkLighter,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: AppTheme.borderDark),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.calendar_today_rounded, size: 15, color: AppTheme.secondary),
                                const SizedBox(width: 8),
                                Text(
                                  '${startDate.day.toString().padLeft(2, '0')}/${startDate.month.toString().padLeft(2, '0')}/${startDate.year}',
                                  style: const TextStyle(color: AppTheme.textDark, fontSize: 13, fontWeight: FontWeight.w500),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Kết thúc (Chủ Nhật)', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12.5)),
                        const SizedBox(height: 6),
                        InkWell(
                          onTap: () async {
                            final picked = await showDatePicker(
                              context: context,
                              initialDate: endDate,
                              firstDate: startDate,
                              lastDate: DateTime(2035),
                            );
                            if (picked != null) {
                              final pickedSunday = picked.add(Duration(days: 7 - picked.weekday));
                              setModalState(() {
                                endDate = pickedSunday;
                              });
                            }
                          },
                          borderRadius: BorderRadius.circular(10),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                            decoration: BoxDecoration(
                              color: AppTheme.surfaceDarkLighter,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: AppTheme.borderDark),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.event_available_rounded, size: 15, color: AppTheme.secondaryLight),
                                const SizedBox(width: 8),
                                Text(
                                  '${endDate.day.toString().padLeft(2, '0')}/${endDate.month.toString().padLeft(2, '0')}/${endDate.year}',
                                  style: const TextStyle(color: AppTheme.textDark, fontSize: 13, fontWeight: FontWeight.w500),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ],
          );
        },
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: () {
            final focus = focusController.text.trim();
            if (focus.isEmpty) return;
            controller.createWeeklyPlan(
              nextWeekNo,
              focus: focus,
              startDate: startDate,
              endDate: endDate,
            );
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
