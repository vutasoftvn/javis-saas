import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../../../core/widgets/app_toast.dart';
import '../../controllers/marketing_controller.dart';
import '../widgets/marketing_forms.dart';

double _toDouble(TextEditingController c, {double fallback = 0.0}) {
  return double.tryParse(c.text.trim()) ?? fallback;
}

void showObjectiveForm(BuildContext context, MarketingController controller, {Map<String, dynamic>? existing}) {
  final isEdit = existing != null;
  final title = TextEditingController(text: existing?['title']?.toString() ?? '');
  final description = TextEditingController(text: existing?['description']?.toString() ?? '');
  final metric = TextEditingController(text: existing?['target_metric']?.toString() ?? '');
  final target = TextEditingController(text: (existing?['target_value'] ?? '').toString());
  final current = TextEditingController(text: (existing?['current_value'] ?? '0').toString());
  final unit = TextEditingController(text: existing?['unit']?.toString() ?? 'count');

  AppModalDialog.show<void>(
    context: context,
    title: isEdit ? 'Sửa mục tiêu Marketing' : 'Thêm mục tiêu Marketing',
    subtitle: 'Mục tiêu Marketing phải bắt nguồn từ mục tiêu chiến lược của công ty (§5).',
    icon: Icons.flag_outlined,
    maxWidth: 560,
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        marketingTextField(controller: title, label: 'Tên mục tiêu', hint: 'VD: 300 lead đủ điều kiện trong 12 tuần'),
        marketingTextField(controller: description, label: 'Mô tả (tuỳ chọn)', maxLines: 3),
        marketingTextField(controller: metric, label: 'Chỉ số theo dõi (KPI)', hint: 'VD: mql, cac, cvr'),
        Row(
          children: [
            Expanded(child: marketingTextField(controller: target, label: 'Giá trị mục tiêu', numeric: true)),
            const SizedBox(width: 12),
            Expanded(child: marketingTextField(controller: current, label: 'Giá trị hiện tại', numeric: true)),
          ],
        ),
        marketingTextField(controller: unit, label: 'Đơn vị', hint: 'count, currency, percentage'),
      ],
    ),
    actions: [
      marketingDialogActions(
        submitLabel: isEdit ? 'Lưu thay đổi' : 'Tạo mục tiêu',
        onSubmit: () {
          if (title.text.trim().isEmpty || metric.text.trim().isEmpty) {
            AppToast.warning('Cần nhập tên mục tiêu và chỉ số theo dõi', title: 'Thiếu thông tin');
            return;
          }
          final payload = {
            'title': title.text.trim(),
            'description': description.text.trim().isEmpty ? null : description.text.trim(),
            'target_metric': metric.text.trim(),
            'target_value': _toDouble(target),
            'current_value': _toDouble(current),
            'unit': unit.text.trim().isEmpty ? 'count' : unit.text.trim(),
          };
          Get.back<void>();
          if (isEdit) {
            controller.updateObjective(existing['id'].toString(), payload);
          } else {
            controller.createObjective({...payload, 'period_weeks': 12});
          }
        },
      ),
    ],
  );
}

void showMetricForm(BuildContext context, MarketingController controller, {Map<String, dynamic>? existing}) {
  final isEdit = existing != null;
  final code = TextEditingController(text: existing?['code']?.toString() ?? '');
  final name = TextEditingController(text: existing?['name']?.toString() ?? '');
  final target = TextEditingController(text: (existing?['target_value'] ?? '').toString());
  final current = TextEditingController(text: (existing?['current_value'] ?? '0').toString());
  final unit = TextEditingController(text: existing?['unit']?.toString() ?? '');
  final stage = (existing?['funnel_stage']?.toString() ?? 'discover').obs;

  AppModalDialog.show<void>(
    context: context,
    title: isEdit ? 'Sửa chỉ số' : 'Thêm chỉ số theo dõi',
    subtitle: 'Chỉ số đo lường hiệu quả phễu (§8) và tiến độ đạt mục tiêu.',
    icon: Icons.speed_outlined,
    maxWidth: 540,
    content: Obx(
      () => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          marketingTextField(controller: code, label: 'Mã chỉ số', hint: 'VD: mql, cpa, cac, ltv'),
          marketingTextField(controller: name, label: 'Tên hiển thị'),
          marketingDropdown(
            value: stage.value,
            items: kFunnelStages,
            label: 'Bước phễu liên quan',
            onChanged: (v) => stage.value = v,
          ),
          Row(
            children: [
              Expanded(child: marketingTextField(controller: target, label: 'Mục tiêu', numeric: true)),
              const SizedBox(width: 12),
              Expanded(child: marketingTextField(controller: current, label: 'Hiện tại', numeric: true)),
            ],
          ),
          marketingTextField(controller: unit, label: 'Đơn vị', hint: 'VND, %, người, lượt'),
        ],
      ),
    ),
    actions: [
      marketingDialogActions(
        submitLabel: isEdit ? 'Lưu' : 'Thêm chỉ số',
        onSubmit: () {
          if (code.text.trim().isEmpty || name.text.trim().isEmpty) {
            AppToast.warning('Mã và tên chỉ số là bắt buộc', title: 'Thiếu thông tin');
            return;
          }
          final payload = {
            'metric_name': code.text.trim(),
            'name': name.text.trim(),
            'funnel_stage': stage.value,
            'target_value': _toDouble(target),
            'current_value': _toDouble(current),
            'unit': unit.text.trim().isEmpty ? null : unit.text.trim(),
          };
          Get.back<void>();
          controller.upsertMetric(payload);
        },
      ),
    ],
  );
}
