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
            // Objectives List
            if (controller.objectives.isEmpty)
              const SizedBox.shrink()
            else
              Column(
                children: controller.objectives
                    .map((obj) => _buildObjectiveCard(context, obj))
                    .toList(),
              ),

            if (controller.objectives.isNotEmpty && controller.weeklyPlans.isNotEmpty)
              const SizedBox(height: 48),

            // Weekly Plans & Commitments List
            if (controller.weeklyPlans.isEmpty)
              const SizedBox.shrink()
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




  // ====================================================================
  // Wide Modals
  // ====================================================================

  static void showCreateObjectiveDialog(BuildContext context, StrategyController controller) {
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
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
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
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
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

  static void showCreateCycleDialog(BuildContext context, StrategyController controller) {
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

  static void showAiOkrModal(BuildContext context, StrategyController controller) {
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
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
          ),
        ),
      ],
    );
  }

  // ====================================================================
  // mCOSA V12 Weekly Review & Week 13 Dialogs (Sprint 5)
  // ====================================================================

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
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primary,
            foregroundColor: const Color(0xFF04070E),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
          ),
          child: const Text('Lưu Mission'),
        ),
      ],
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
}



