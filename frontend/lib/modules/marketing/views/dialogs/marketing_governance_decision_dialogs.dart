import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../controllers/marketing_controller.dart';
import '../widgets/marketing_common.dart';
import '../widgets/marketing_forms.dart';

void showApprovalReviewDialog(
  BuildContext context,
  MarketingController controller,
  Map<String, dynamic> approval, {
  required bool approve,
}) {
  final notes = TextEditingController();

  AppModalDialog.show<void>(
    context: context,
    title: approve ? 'Phê duyệt hành động' : 'Từ chối hành động',
    subtitle: approval['title']?.toString(),
    icon: approve ? Icons.verified_outlined : Icons.block_outlined,
    iconColor: approve ? AppTheme.success : AppTheme.accent,
    maxWidth: 560,
    content: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        MarketingCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              MarketingKeyValue(label: 'Loại hành động', value: approval['action_type']?.toString() ?? '—'),
              MarketingKeyValue(label: 'Do agent đề xuất', value: approval['requested_by_agent']?.toString() ?? '—'),
              MarketingKeyValue(label: 'Chi tiết', value: approval['details']?.toString() ?? '—'),
            ],
          ),
        ),
        const SizedBox(height: 14),
        marketingTextField(controller: notes, label: 'Ghi chú của người duyệt', maxLines: 3),
        Text(
          approve
              ? 'Sau khi phê duyệt, hành động sẽ được thực thi ngay.'
              : 'Từ chối sẽ khôi phục trạng thái trước đó của đối tượng liên quan.',
          style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark, height: 1.45),
        ),
      ],
    ),
    actions: [
      marketingDialogActions(
        submitLabel: approve ? 'Phê duyệt' : 'Từ chối',
        onSubmit: () {
          Get.back<void>();
          controller.reviewApproval(
            approval['id'].toString(),
            approve,
            notes.text.trim().isEmpty ? null : notes.text.trim(),
          );
        },
      ),
    ],
  );
}

void showLearningForm(BuildContext context, MarketingController controller) {
  final observation = TextEditingController();
  final hypothesis = TextEditingController();
  final action = TextEditingController();
  final result = TextEditingController();
  final learning = TextEditingController();
  final rule = TextEditingController();
  final confidence = 'medium'.obs;

  AppModalDialog.show<void>(
    context: context,
    title: 'Ghi bài học Marketing',
    subtitle: 'Quan sát → giả thuyết → hành động → kết quả → bài học (§16).',
    icon: Icons.psychology_outlined,
    maxWidth: 620,
    content: Obx(
      () => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          marketingTextField(controller: observation, label: 'Quan sát', maxLines: 2),
          marketingTextField(controller: hypothesis, label: 'Giả thuyết', maxLines: 2),
          marketingTextField(controller: action, label: 'Hành động đã làm', maxLines: 2),
          marketingTextField(controller: result, label: 'Kết quả đo được', maxLines: 2),
          marketingTextField(controller: learning, label: 'Bài học', maxLines: 3),
          marketingTextField(controller: rule, label: 'Luật tái sử dụng (tuỳ chọn)', hint: 'VD: Khi CPA tăng quá 20% trong 7 ngày thì giảm ngân sách 30%', maxLines: 2),
          marketingDropdown(
            value: confidence.value,
            items: const [
              MapEntry('high', 'Cao'),
              MapEntry('medium', 'Trung bình'),
              MapEntry('low', 'Thấp'),
            ],
            label: 'Độ tin cậy',
            onChanged: (v) => confidence.value = v,
          ),
        ],
      ),
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Lưu bài học',
        onSubmit: () {
          if (observation.text.trim().isEmpty || learning.text.trim().isEmpty) {
            Get.snackbar('Thiếu thông tin', 'Cần nhập ít nhất quan sát và bài học', snackPosition: SnackPosition.BOTTOM);
            return;
          }
          Get.back<void>();
          controller.createLearning({
            'observation': observation.text.trim(),
            'hypothesis': hypothesis.text.trim(),
            'action': action.text.trim(),
            'result': result.text.trim(),
            'learning': learning.text.trim(),
            'reusable_rule': rule.text.trim().isEmpty ? null : rule.text.trim(),
            'confidence': confidence.value,
          });
        },
      ),
    ],
  );
}

void showLoopForm(BuildContext context, MarketingController controller, {Map<String, dynamic>? existing}) {
  final isEdit = existing != null;
  String loopType = existing?['loop_type']?.toString() ?? 'content';
  final name = TextEditingController(text: existing?['name']?.toString() ?? '');
  final description = TextEditingController(text: existing?['description']?.toString() ?? '');
  final frequency = TextEditingController(text: existing?['loop_config']?['frequency']?.toString() ?? 'Hàng tuần');

  const loopOptions = [
    MapEntry('content', 'Content Loop (Nội dung & Tái phân phối)'),
    MapEntry('paid_ads', 'Paid Ads Loop (Quảng cáo & Sáng tạo)'),
    MapEntry('conversion', 'Conversion Loop (CRO & Trang đích)'),
    MapEntry('retention', 'Retention Loop (Giữ chân & Tương tác)'),
  ];

  AppModalDialog.show<void>(
    context: context,
    title: isEdit ? 'Cập nhật Vòng lặp Tăng trưởng' : 'Tạo Vòng lặp Tăng trưởng (§18)',
    subtitle: 'Vòng lặp khép kín: Tín hiệu → Hành động → Đo lường → Tối ưu hoá liên tục.',
    icon: Icons.loop_rounded,
    maxWidth: 580,
    content: StatefulBuilder(
      builder: (context, setState) {
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (!isEdit)
              marketingDropdown(
                value: loopType,
                items: loopOptions,
                label: 'Loại vòng lặp',
                onChanged: (v) => setState(() => loopType = v),
              ),
            marketingTextField(controller: name, label: 'Tên vòng lặp', hint: 'VD: Vòng lặp Sáng tạo Nội dung Hàng tuần'),
            marketingTextField(controller: description, label: 'Mô tả chu kỳ hoạt động', maxLines: 3),
            marketingTextField(controller: frequency, label: 'Tần suất lặp', hint: 'VD: Hàng ngày / Hàng tuần / Theo sự kiện'),
          ],
        );
      },
    ),
    actions: [
      marketingDialogActions(
        submitLabel: isEdit ? 'Lưu' : 'Tạo vòng lặp',
        onSubmit: () {
          if (name.text.trim().isEmpty) return;
          Get.back<void>();
          if (isEdit) {
            controller.updateLoop(existing['id'].toString(), {
              'name': name.text.trim(),
              'description': description.text.trim(),
              'loop_config': {'frequency': frequency.text.trim()},
            });
          } else {
            controller.createLoop({
              'loop_type': loopType,
              'name': name.text.trim(),
              'description': description.text.trim(),
              'loop_config': {'frequency': frequency.text.trim()},
            });
          }
        },
      ),
    ],
  );
}

void showDecisionForm(BuildContext context, MarketingController controller) {
  final title = TextEditingController();
  final contextSummary = TextEditingController();
  final decision = TextEditingController();
  final reason = TextEditingController();
  final expectedOutcome = TextEditingController();

  AppModalDialog.show<void>(
    context: context,
    title: 'Ghi nhận Quyết định Marketing (Decision Journal §53)',
    subtitle: 'Lưu trữ ngữ cảnh, lý do và kết quả kỳ vọng để đối chiếu và rút ra bài học sau này.',
    icon: Icons.history_edu_outlined,
    maxWidth: 600,
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        marketingTextField(controller: title, label: 'Tiêu đề quyết định', hint: 'VD: Dịch chuyển 40% ngân sách sang Google Search'),
        marketingTextField(controller: contextSummary, label: 'Bối cảnh trước khi ra quyết định', maxLines: 2),
        marketingTextField(controller: decision, label: 'Nội dung quyết định cụ thể', maxLines: 3),
        marketingTextField(controller: reason, label: 'Lý do & Căn cứ lựa chọn', maxLines: 2),
        marketingTextField(controller: expectedOutcome, label: 'Kết quả kỳ vọng (Expected Outcome)', maxLines: 2),
      ],
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Ghi nhận quyết định',
        onSubmit: () {
          if (title.text.trim().isEmpty || decision.text.trim().isEmpty) return;
          Get.back<void>();
          controller.createDecision({
            'title': title.text.trim(),
            'context_summary': contextSummary.text.trim(),
            'decision': decision.text.trim(),
            'reason': reason.text.trim(),
            'expected_outcome': expectedOutcome.text.trim(),
          });
        },
      ),
    ],
  );
}

void showAttributionDialog(BuildContext context, MarketingController controller) {
  String modelType = 'last_touch';
  final convValue = TextEditingController(text: '100.0');
  final touchpointsText = TextEditingController(text: 'Google Ads (Search)\nMeta Ads (Retargeting)\nEmail Onboarding');

  const modelOptions = [
    MapEntry('first_touch', 'First Touch (100% chạm đầu)'),
    MapEntry('last_touch', 'Last Touch (100% chạm cuối)'),
    MapEntry('linear', 'Linear (Chia đều 1/N)'),
    MapEntry('position_based', 'Position-based (40% đầu - 40% cuối - 20% giữa)'),
    MapEntry('time_decay', 'Time Decay (Phân rã luỹ thừa)'),
  ];

  AppModalDialog.show<void>(
    context: context,
    title: 'Mô hình Phân bổ Chuyển đổi (§28)',
    subtitle: 'Đo lường đa chạm bằng Python Analytics Engine để đánh giá đúng đóng góp từng kênh.',
    icon: Icons.pie_chart_outline_rounded,
    maxWidth: 600,
    content: StatefulBuilder(
      builder: (context, setState) {
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            marketingDropdown(
              value: modelType,
              items: modelOptions,
              label: 'Mô hình phân bổ',
              onChanged: (v) => setState(() => modelType = v),
            ),
            marketingTextField(controller: convValue, label: 'Giá trị chuyển đổi / Doanh thu (\$)', numeric: true),
            marketingTextField(controller: touchpointsText, label: 'Các điểm chạm trong hành trình (mỗi dòng 1 kênh/chiến dịch)', maxLines: 4),
          ],
        );
      },
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Tính toán phân bổ',
        onSubmit: () {
          final lines = touchpointsText.text.trim().split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
          final touchpoints = lines.map((l) => {'channel': l, 'campaign': l}).toList();
          final val = double.tryParse(convValue.text.trim()) ?? 100.0;
          Get.back<void>();
          controller.runAttributionAnalysis(touchpoints, modelType, val);
        },
      ),
    ],
  );
}
