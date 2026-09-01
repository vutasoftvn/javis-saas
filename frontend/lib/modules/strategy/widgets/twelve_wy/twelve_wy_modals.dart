import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/strategy_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../../../core/widgets/app_toast.dart';

class TwelveWyModals {
  static void showCreateWeeklyPlanDialog(BuildContext context, StrategyController controller) {
    final weekNoController = TextEditingController(text: '${controller.weeklyPlans.length + 1}');
    final focusController = TextEditingController();

    AppModalDialog.show(
      context: context,
      title: 'Tạo Kế Hoạch Tuần Thực Thi',
      subtitle: 'Xác định số tuần và trọng tâm chiến lược cốt lõi của tuần',
      icon: Icons.calendar_today_rounded,
      maxWidth: 540,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: weekNoController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Số thứ tự tuần (Week Number)', hintText: '1, 2, 3...'),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: focusController,
            decoration: const InputDecoration(labelText: 'Trọng tâm tuần (Weekly Focus)', hintText: 'Ví dụ: Tối ưu hoá luồng Onboarding'),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Get.back(), child: const Text('Huỷ', style: TextStyle(color: Colors.white60))),
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
          child: const Text('Tạo Kế hoạch Tuần'),
        ),
      ],
    );
  }

  static void showEditWeeklyMissionDialog(BuildContext context, StrategyController controller, dynamic plan) {
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

  static void showCompileCycleDialog(BuildContext context, StrategyController controller) {
    String? currentCycleId;
    if (controller.twelveWeekCycles.isNotEmpty) {
      currentCycleId = controller.twelveWeekCycles.first['id']?.toString();
    }

    if (currentCycleId == null) {
      AppToast.warning('Chưa có chu kỳ 12 tuần nào để biên dịch');
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
                        Text('Điểm Thực thi: ${(execScore * 100).toInt()}%', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white70)),
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
                        Text('Điểm Kết quả: ${(outcomeScore * 100).toInt()}%', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white70)),
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
                decoration: const InputDecoration(labelText: 'Khuyến nghị Hành động'),
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
                decoration: const InputDecoration(labelText: 'Bằng chứng thực tế đã học', hintText: 'Ví dụ: Phỏng vấn 8/10 người dùng...'),
              ),
              const SizedBox(height: 14),
              TextField(
                controller: summaryController,
                maxLines: 2,
                decoration: const InputDecoration(labelText: 'Tóm tắt nhận định & bài học', hintText: 'Ví dụ: Năng lực Founder đạt 38h...'),
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

  static void showWeek13TransitionDialog(BuildContext context, StrategyController controller) {
    String? currentCycleId;
    if (controller.twelveWeekCycles.isNotEmpty) {
      currentCycleId = controller.twelveWeekCycles.first['id']?.toString();
    }

    if (currentCycleId == null) {
      AppToast.warning('Chưa có chu kỳ 12 tuần nào để chuyển dịch');
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
      title: 'Tuần 13 — Chuyển Dịch Chiến Lược & Kỷ Niệm (Week 13 Transition)',
      subtitle: 'Nghỉ ngơi, tôn vinh thành quả 12 tuần, tổng kết bài học và hoạch định chu kỳ kế tiếp',
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
                          'Tiến độ chuẩn bị: Đã hoàn tất $completedReviews/$totalWeeks bản đánh giá tuần. Tuần 13 là bắt buộc để tái tạo năng lượng.',
                          style: const TextStyle(fontSize: 12, color: Colors.white70),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: titleController,
                  decoration: const InputDecoration(labelText: 'Tiêu đề Lễ Kỷ Niệm'),
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
                  decoration: const InputDecoration(labelText: 'Bài học chiến lược cốt lõi', hintText: 'Nhận định lớn nhất...'),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: rewardsController,
                  decoration: const InputDecoration(labelText: 'Phần thưởng & Nghi thức kỷ niệm'),
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
          style: ElevatedButton.styleFrom(backgroundColor: Colors.pinkAccent, foregroundColor: const Color(0xFF04070E), padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12)),
        ),
      ],
    );
  }
}
