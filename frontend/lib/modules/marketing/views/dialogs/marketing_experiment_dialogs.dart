import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../controllers/marketing_controller.dart';
import '../widgets/marketing_common.dart';
import '../widgets/marketing_forms.dart';

double _toDouble(TextEditingController c, {double fallback = 0.0}) {
  return double.tryParse(c.text.trim()) ?? fallback;
}

int _toInt(TextEditingController c, {int fallback = 0}) {
  return int.tryParse(c.text.trim()) ?? fallback;
}

void showExperimentForm(BuildContext context, MarketingController controller) {
  final hypothesis = TextEditingController();
  final metric = TextEditingController();
  final baseline = TextEditingController(text: '0');
  final target = TextEditingController(text: '0');
  final variantA = TextEditingController();
  final variantB = TextEditingController();
  final sample = TextEditingController(text: '0');
  final campaignId = ''.obs;

  final campaignItems = <MapEntry<String, String>>[
    const MapEntry('', 'Không gắn chiến dịch'),
    ...controller.campaigns.map(
      (c) => MapEntry(c['id'].toString(), c['name']?.toString() ?? 'Chiến dịch'),
    ),
  ];

  AppModalDialog.show<void>(
    context: context,
    title: 'Tạo thử nghiệm A/B',
    subtitle: 'Giả thuyết → đo lường → quyết định. Kết quả thống kê do Python tính, không do AI ước lượng.',
    icon: Icons.science_outlined,
    maxWidth: 640,
    content: Obx(
      () => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          marketingTextField(
            controller: hypothesis,
            label: 'Giả thuyết',
            hint: 'VD: Tiêu đề ngắn gọn hơn sẽ tăng tỷ lệ chuyển đổi trang đích',
            maxLines: 2,
          ),
          marketingDropdown(
            value: campaignId.value,
            items: campaignItems,
            label: 'Chiến dịch liên quan',
            onChanged: (v) => campaignId.value = v,
          ),
          marketingTextField(controller: metric, label: 'Chỉ số đo lường', hint: 'VD: cvr'),
          Row(
            children: [
              Expanded(child: marketingTextField(controller: baseline, label: 'Giá trị nền', numeric: true)),
              const SizedBox(width: 12),
              Expanded(child: marketingTextField(controller: target, label: 'Giá trị kỳ vọng', numeric: true)),
            ],
          ),
          marketingTextField(controller: variantA, label: 'Phương án A (đối chứng)'),
          marketingTextField(controller: variantB, label: 'Phương án B (thử nghiệm)'),
          marketingTextField(controller: sample, label: 'Cỡ mẫu dự kiến', numeric: true),
        ],
      ),
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Tạo thử nghiệm',
        onSubmit: () {
          if (hypothesis.text.trim().isEmpty || metric.text.trim().isEmpty ||
              variantA.text.trim().isEmpty || variantB.text.trim().isEmpty) {
            Get.snackbar('Thiếu thông tin', 'Cần nhập giả thuyết, chỉ số và hai phương án',
                snackPosition: SnackPosition.BOTTOM);
            return;
          }
          Get.back<void>();
          controller.createExperiment({
            'hypothesis': hypothesis.text.trim(),
            'metric': metric.text.trim(),
            'baseline_value': _toDouble(baseline),
            'target_value': _toDouble(target),
            'variant_a': variantA.text.trim(),
            'variant_b': variantB.text.trim(),
            'sample_size': _toInt(sample),
            'campaign_id': campaignId.value.isEmpty ? null : campaignId.value,
          });
        },
      ),
    ],
  );
}

void showExperimentEvaluateForm(BuildContext context, MarketingController controller, Map<String, dynamic> experiment) {
  final baselineCvr = TextEditingController(text: (experiment['baseline_value'] ?? 0).toString());
  final variantCvr = TextEditingController();
  final baselineSample = TextEditingController();
  final variantSample = TextEditingController();

  AppModalDialog.show<void>(
    context: context,
    title: 'Đánh giá thử nghiệm',
    subtitle: 'Nhập số liệu thực đo. Hệ thống chạy kiểm định Z cho tỷ lệ, không suy đoán.',
    icon: Icons.calculate_outlined,
    maxWidth: 560,
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Expanded(child: marketingTextField(controller: baselineCvr, label: 'Tỷ lệ CV nhóm A (%)', numeric: true)),
            const SizedBox(width: 12),
            Expanded(child: marketingTextField(controller: variantCvr, label: 'Tỷ lệ CV nhóm B (%)', numeric: true)),
          ],
        ),
        Row(
          children: [
            Expanded(child: marketingTextField(controller: baselineSample, label: 'Cỡ mẫu A', numeric: true)),
            const SizedBox(width: 12),
            Expanded(child: marketingTextField(controller: variantSample, label: 'Cỡ mẫu B', numeric: true)),
          ],
        ),
        const Text(
          'Mỗi nhóm cần tối thiểu 30 quan sát, nếu không kết quả sẽ được ghi là "Chưa kết luận".',
          style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark, height: 1.45),
        ),
      ],
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Chạy đánh giá',
        onSubmit: () async {
          Get.back<void>();
          final result = await controller.evaluateExperiment(experiment['id'].toString(), {
            'baseline_cvr': _toDouble(baselineCvr),
            'variant_cvr': _toDouble(variantCvr),
            'baseline_sample': _toInt(baselineSample),
            'variant_sample': _toInt(variantSample),
          });
          final evaluation = result['evaluation'];
          if (evaluation is Map) {
            Get.snackbar(
              'Kết quả: ${MarketingLabels.experiment(evaluation['decision']?.toString().toLowerCase())}',
              'Chênh lệch ${evaluation['uplift_pct']}% · z = ${evaluation['z_score']} · p = ${evaluation['p_value']}',
              snackPosition: SnackPosition.BOTTOM,
              duration: const Duration(seconds: 5),
            );
          }
        },
      ),
    ],
  );
}

void showExperimentDecisionForm(BuildContext context, MarketingController controller, Map<String, dynamic> experiment) {
  final learning = TextEditingController(text: experiment['learning']?.toString() ?? '');
  final decision = 'WIN'.obs;

  AppModalDialog.show<void>(
    context: context,
    title: 'Chốt quyết định',
    subtitle: 'Kết quả thống kê là đầu vào; quyết định cuối cùng thuộc về con người.',
    icon: Icons.gavel_outlined,
    maxWidth: 560,
    content: Obx(
      () => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          marketingDropdown(
            value: decision.value,
            items: const [
              MapEntry('WIN', 'Thắng - triển khai rộng'),
              MapEntry('LOSE', 'Thua - giữ phương án cũ'),
              MapEntry('INCONCLUSIVE', 'Chưa kết luận'),
              MapEntry('ITERATE', 'Cần lặp lại thử nghiệm'),
            ],
            label: 'Quyết định',
            onChanged: (v) => decision.value = v,
          ),
          marketingTextField(
            controller: learning,
            label: 'Bài học rút ra',
            hint: 'Điều gì đúng/sai và vì sao? Bài học sẽ được lưu vào bộ nhớ Marketing.',
            maxLines: 4,
          ),
        ],
      ),
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Ghi nhận',
        onSubmit: () {
          Get.back<void>();
          controller.decideExperiment(
            experiment['id'].toString(),
            decision.value,
            learning.text.trim().isEmpty ? null : learning.text.trim(),
          );
        },
      ),
    ],
  );
}
