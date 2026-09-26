// Task 7 (PHẠM VI MỞ RỘNG 2026-09-14) — UI publish Objective tối giản, đủ để
// mở route `strategy` thật và cho `showOkrWeeklyGeneratorDialog` (Task 7
// Step 2, đã commit ở c6f2df18) một nơi thật để gọi sau khi publish thành
// công. Đây KHÔNG phải thiết kế UI hoàn chỉnh — chỉ ListView Objective với
// title/status/nút Publish, đủ để chứng minh luồng thật.
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/app_toast.dart';
import '../../startup_os/widgets/startup_os_panel.dart';
import '../controllers/strategy_controller.dart';
import '../models/mvp_strategy_models.dart';
import '../widgets/okr_weekly_generator_dialog.dart';

class StrategyView extends GetView<StrategyController> {
  const StrategyView({super.key});

  bool _isDraft(MvpObjective objective) => objective.status.toLowerCase() == 'draft';

  Future<void> _handlePublish(BuildContext context, MvpObjective objective) async {
    try {
      await controller.publish(objective.id);
      if (!context.mounted) return;
      await showOkrWeeklyGeneratorDialog(context, objectiveId: objective.id);
    } catch (e) {
      AppToast.error('Không publish được Objective: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    // Startup OS (plan 2026-09-18 Phase 4): cây mục tiêu + ngữ cảnh 7 chiều là tab
    // đầu; danh sách Objective cũ giữ nguyên ở tab thứ hai.
    return DefaultTabController(
      length: 2,
      child: Column(
        children: [
          const TabBar(
            tabs: [
              Tab(key: Key('strategy-tab-startup-os'), text: 'Mục tiêu & Ngữ cảnh'),
              Tab(key: Key('strategy-tab-objectives'), text: 'Objectives'),
            ],
          ),
          Expanded(
            child: TabBarView(
              children: [
                const StartupOsPanel(),
                _buildObjectives(context),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _openCreateObjectiveDialog(BuildContext context) async {
    final titleCtrl = TextEditingController();
    final whyCtrl = TextEditingController();
    final submitted = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Tạo Objective mới'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              key: const Key('objective-title-field'),
              controller: titleCtrl,
              autofocus: true,
              decoration: const InputDecoration(labelText: 'Mục tiêu (Objective)'),
            ),
            TextField(
              controller: whyCtrl,
              decoration: const InputDecoration(labelText: 'Vì sao quan trọng? (tuỳ chọn)'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Huỷ')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Tạo')),
        ],
      ),
    );
    final title = titleCtrl.text.trim();
    if (submitted != true || title.isEmpty) return;
    try {
      await controller.createObjective(title: title, why: whyCtrl.text);
      AppToast.success('Đã tạo Objective "$title" (bản nháp).');
    } catch (e) {
      AppToast.error('Không tạo được Objective: $e');
    }
  }

  Future<void> _openAddKeyResultDialog(BuildContext context, MvpObjective objective) async {
    final titleCtrl = TextEditingController();
    final targetCtrl = TextEditingController();
    final baselineCtrl = TextEditingController();
    final unitCtrl = TextEditingController();
    final submitted = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Thêm Key Result cho "${objective.title}"'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: 'Kết quả then chốt')),
            TextField(
              controller: targetCtrl,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Chỉ tiêu (target)'),
            ),
            TextField(
              controller: baselineCtrl,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Điểm xuất phát (tuỳ chọn)'),
            ),
            TextField(controller: unitCtrl, decoration: const InputDecoration(labelText: 'Đơn vị (tuỳ chọn)')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Huỷ')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Thêm')),
        ],
      ),
    );
    if (submitted != true) return;
    final title = titleCtrl.text.trim();
    final target = double.tryParse(targetCtrl.text.replaceAll(',', '.'));
    if (title.isEmpty || target == null) {
      AppToast.error('Cần nhập tên Key Result và chỉ tiêu là số.');
      return;
    }
    try {
      await controller.addKeyResult(
        objectiveId: objective.id,
        title: title,
        targetValue: target,
        baselineValue: double.tryParse(baselineCtrl.text.replaceAll(',', '.')),
        unit: unitCtrl.text,
      );
    } catch (e) {
      AppToast.error('Không thêm được Key Result: $e');
    }
  }

  Future<void> _openCheckinDialog(BuildContext context, Map<String, dynamic> kr) async {
    final valueCtrl = TextEditingController(text: kr['currentValue']?.toString() ?? '');
    final submitted = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Cập nhật tiến độ: ${kr['title'] ?? ''}'),
        content: TextField(
          controller: valueCtrl,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Giá trị hiện tại'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Huỷ')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Lưu')),
        ],
      ),
    );
    final value = double.tryParse(valueCtrl.text.replaceAll(',', '.'));
    if (submitted != true || value == null) return;
    try {
      await controller.checkinKeyResult(kr['id'].toString(), value);
    } catch (e) {
      AppToast.error('Không cập nhật được tiến độ: $e');
    }
  }

  Future<void> _confirmDelete(BuildContext context, String label, Future<void> Function() action) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Xác nhận xoá'),
        content: Text('Xoá $label? Hành động này không hoàn tác được.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Huỷ')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Xoá')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await action();
    } catch (e) {
      AppToast.error('Không xoá được: $e');
    }
  }

  Widget _buildObjectives(BuildContext context) {
    return Obx(() {
      if (controller.isLoading.value && controller.objectives.isEmpty) {
        return const Center(child: CircularProgressIndicator());
      }
      final error = controller.errorMessage.value;
      if (error != null && controller.objectives.isEmpty) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(error),
              const SizedBox(height: 12),
              TextButton(
                onPressed: controller.loadObjectives,
                child: const Text('Thử lại'),
              ),
            ],
          ),
        );
      }
      final objectives = controller.objectives;
      final createButton = ElevatedButton.icon(
        key: const Key('create-objective-button'),
        style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary),
        onPressed: () => _openCreateObjectiveDialog(context),
        icon: const Icon(Icons.add),
        label: const Text('Tạo Objective'),
      );
      if (objectives.isEmpty) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Chưa có Objective nào.'),
              const SizedBox(height: 6),
              const Text(
                'Đặt 1-3 mục tiêu cho Project đang chọn, rồi thêm Key Result đo được.',
                style: TextStyle(fontSize: 12, color: Colors.white54),
              ),
              const SizedBox(height: 16),
              createButton,
            ],
          ),
        );
      }
      return RefreshIndicator(
        onRefresh: controller.loadObjectives,
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: objectives.length + 1,
          itemBuilder: (context, index) {
            if (index == 0) {
              return Align(
                alignment: Alignment.centerRight,
                child: Padding(padding: const EdgeInsets.only(bottom: 12), child: createButton),
              );
            }
            final objective = objectives[index - 1];
            final keyResults = controller.keyResultsByObjective[objective.id] ?? const [];
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ListTile(
                      title: Text(objective.title),
                      subtitle: Text(
                        objective.why == null || objective.why!.isEmpty
                            ? objective.status
                            : '${objective.status} · ${objective.why}',
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (_isDraft(objective))
                            ElevatedButton(
                              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary),
                              onPressed: () => _handlePublish(context, objective),
                              child: const Text('Publish'),
                            ),
                          IconButton(
                            tooltip: 'Xoá Objective',
                            icon: const Icon(Icons.delete_outline),
                            onPressed: () => _confirmDelete(
                              context,
                              'Objective "${objective.title}"',
                              () => controller.deleteObjective(objective.id),
                            ),
                          ),
                        ],
                      ),
                    ),
                    for (final kr in keyResults)
                      ListTile(
                        dense: true,
                        contentPadding: const EdgeInsets.only(left: 32, right: 8),
                        leading: const Icon(Icons.trending_up, size: 18),
                        title: Text(kr['title']?.toString() ?? 'Key Result'),
                        subtitle: Text(
                          '${kr['currentValue'] ?? kr['baselineValue'] ?? 0} / ${kr['targetValue'] ?? '?'} ${kr['unit'] ?? ''}',
                        ),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              tooltip: 'Cập nhật tiến độ',
                              icon: const Icon(Icons.edit_note, size: 20),
                              onPressed: () => _openCheckinDialog(context, kr),
                            ),
                            IconButton(
                              tooltip: 'Xoá Key Result',
                              icon: const Icon(Icons.close, size: 18),
                              onPressed: () => _confirmDelete(
                                context,
                                'Key Result "${kr['title'] ?? ''}"',
                                () => controller.deleteKeyResult(kr['id'].toString()),
                              ),
                            ),
                          ],
                        ),
                      ),
                    Padding(
                      padding: const EdgeInsets.only(left: 24, bottom: 4),
                      child: TextButton.icon(
                        onPressed: () => _openAddKeyResultDialog(context, objective),
                        icon: const Icon(Icons.add, size: 18),
                        label: const Text('Thêm Key Result'),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      );
    });
  }
}
