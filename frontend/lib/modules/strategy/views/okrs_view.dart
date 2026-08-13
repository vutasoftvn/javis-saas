import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/strategy_controller.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/app_modal_dialog.dart';
import '../../../core/widgets/floating_app_bar.dart';

class OkrsView extends GetView<StrategyController> {
  const OkrsView({super.key});

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
            title: 'Mục tiêu & Kết quả Then chốt (OKRs)',
            subtitle: 'Theo dõi và đo lường tiến độ mục tiêu doanh nghiệp theo thời gian thực.',
            actions: [
              OutlinedButton.icon(
                onPressed: () => _showCreateCycleDialog(context),
                icon: const Icon(Icons.cached_rounded, size: 16),
                label: const Text('Chu kỳ OKR'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white70,
                  side: BorderSide(color: Colors.white.withValues(alpha: 0.2)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
              const SizedBox(width: 8),
              Obx(() => OutlinedButton.icon(
                onPressed: controller.isGeneratingAi.value ? null : () => _showAiOkrModal(context),
                icon: controller.isGeneratingAi.value
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(color: AppTheme.primary, strokeWidth: 2),
                      )
                    : const Icon(Icons.auto_awesome_rounded, size: 16, color: AppTheme.primary),
                label: Text(
                  controller.isGeneratingAi.value ? 'Đang sinh AI...' : 'Tạo tự động AI',
                  style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold, fontSize: 13),
                ),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppTheme.primary),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              )),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: () => _showCreateObjectiveDialog(context),
                icon: const Icon(Icons.add_rounded, size: 16),
                label: const Text('Thêm Objective'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: const Color(0xFF04070E),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
            ],
          ),

          // 2. OKR Content Body
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value) {
                return const Center(
                  child: CircularProgressIndicator(color: AppTheme.primaryLight),
                );
              }

              return SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
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
                  ],
                ),
              );
            }),
          ),
        ],
      ),
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
            // Objective Header Bar
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

                            // Active Status Icon
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

            // Collapsible Key Results Section
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
}
