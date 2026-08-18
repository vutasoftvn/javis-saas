import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:get/get.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../controllers/marketing_controller.dart';
import 'marketing_common.dart';

/// Danh sách 8 bước phễu theo §8 - nhãn hiển thị lấy từ backend khi có, đây là bản dự
/// phòng để form vẫn dùng được khi chưa nạp xong dữ liệu phễu.
const List<MapEntry<String, String>> kFunnelStages = [
  MapEntry('discover', 'Khám phá'),
  MapEntry('engage', 'Tương tác'),
  MapEntry('consider', 'Cân nhắc'),
  MapEntry('convert', 'Chuyển đổi'),
  MapEntry('activate', 'Kích hoạt'),
  MapEntry('retain', 'Giữ chân'),
  MapEntry('expand', 'Mở rộng'),
  MapEntry('advocate', 'Lan toả'),
];

const List<String> kChannelOptions = [
  'SEO',
  'AEO',
  'Nội dung',
  'Email',
  'Mạng xã hội',
  'Google Ads',
  'Meta Ads',
  'Đối tác',
];

InputDecoration marketingInputDecoration(String label, {String? hint}) {
  return InputDecoration(
    labelText: label,
    hintText: hint,
    labelStyle: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
    hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.25), fontSize: 12.5),
    filled: true,
    fillColor: Colors.white.withValues(alpha: 0.04),
    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.08)),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: AppTheme.primary),
    ),
    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
  );
}

Widget marketingTextField({
  required TextEditingController controller,
  required String label,
  String? hint,
  int maxLines = 1,
  bool numeric = false,
}) {
  return Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: TextField(
      controller: controller,
      maxLines: maxLines,
      style: const TextStyle(color: Colors.white, fontSize: 13.5),
      keyboardType: numeric ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.multiline,
      inputFormatters: numeric ? [FilteringTextInputFormatter.allow(RegExp(r'[0-9.\-]'))] : null,
      decoration: marketingInputDecoration(label, hint: hint),
    ),
  );
}

Widget marketingDropdown({
  required String value,
  required List<MapEntry<String, String>> items,
  required String label,
  required ValueChanged<String> onChanged,
}) {
  return Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: DropdownButtonFormField<String>(
      initialValue: value,
      dropdownColor: kMarketingCardColor,
      style: const TextStyle(color: Colors.white, fontSize: 13.5),
      decoration: marketingInputDecoration(label),
      items: items
          .map((e) => DropdownMenuItem<String>(value: e.key, child: Text(e.value)))
          .toList(),
      onChanged: (v) {
        if (v != null) onChanged(v);
      },
    ),
  );
}

Widget marketingDialogActions({
  required String submitLabel,
  required VoidCallback onSubmit,
  String cancelLabel = 'Huỷ',
}) {
  return Row(
    mainAxisAlignment: MainAxisAlignment.end,
    children: [
      TextButton(
        onPressed: () => Get.back<void>(),
        child: Text(cancelLabel, style: const TextStyle(color: AppTheme.textMutedDark)),
      ),
      const SizedBox(width: 8),
      ElevatedButton(
        onPressed: onSubmit,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppTheme.primary,
          foregroundColor: const Color(0xFF04070E),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        ),
        child: Text(submitLabel),
      ),
    ],
  );
}

double _toDouble(TextEditingController c) => double.tryParse(c.text.trim().replaceAll(',', '.')) ?? 0.0;

int _toInt(TextEditingController c) => int.tryParse(c.text.trim()) ?? 0;

// ==========================================
// Mục tiêu Marketing
// ==========================================

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
            Get.snackbar('Thiếu thông tin', 'Cần nhập tên mục tiêu và chỉ số theo dõi',
                snackPosition: SnackPosition.BOTTOM);
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

// ==========================================
// Chiến dịch
// ==========================================

void showCampaignForm(BuildContext context, MarketingController controller, {Map<String, dynamic>? existing}) {
  final isEdit = existing != null;
  final name = TextEditingController(text: existing?['name']?.toString() ?? '');
  final budget = TextEditingController(text: (existing?['budget'] ?? '0').toString());
  final owner = TextEditingController(text: existing?['owner']?.toString() ?? '');
  final stage = (existing?['funnel_stage']?.toString() ?? 'discover').obs;
  final selectedChannels = <String>{
    ...((existing?['channels'] as List<dynamic>?) ?? const []).map((e) => e.toString()),
  }.obs;

  AppModalDialog.show<void>(
    context: context,
    title: isEdit ? 'Sửa chiến dịch' : 'Tạo chiến dịch mới',
    subtitle: 'Chiến dịch mới luôn bắt đầu ở trạng thái Nháp; kích hoạt cần người phê duyệt.',
    icon: Icons.campaign_outlined,
    maxWidth: 620,
    content: Obx(
      () => Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          marketingTextField(controller: name, label: 'Tên chiến dịch', hint: 'VD: Ra mắt COSA Marketing OS'),
          marketingDropdown(
            value: stage.value,
            items: kFunnelStages,
            label: 'Bước phễu',
            onChanged: (v) => stage.value = v,
          ),
          Row(
            children: [
              Expanded(child: marketingTextField(controller: budget, label: 'Ngân sách', numeric: true)),
              const SizedBox(width: 12),
              Expanded(child: marketingTextField(controller: owner, label: 'Người phụ trách')),
            ],
          ),
          const Text('Kênh triển khai',
              style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTheme.primaryLight)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: kChannelOptions.map((channel) {
              final selected = selectedChannels.contains(channel);
              return FilterChip(
                label: Text(channel, style: const TextStyle(fontSize: 12)),
                selected: selected,
                onSelected: (v) => v ? selectedChannels.add(channel) : selectedChannels.remove(channel),
                backgroundColor: Colors.white.withValues(alpha: 0.05),
                selectedColor: AppTheme.primary.withValues(alpha: 0.3),
                checkmarkColor: Colors.white,
                labelStyle: TextStyle(color: selected ? Colors.white : AppTheme.textMutedDark),
                side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
              );
            }).toList(),
          ),
        ],
      ),
    ),
    actions: [
      marketingDialogActions(
        submitLabel: isEdit ? 'Lưu thay đổi' : 'Tạo chiến dịch',
        onSubmit: () {
          if (name.text.trim().isEmpty) {
            Get.snackbar('Thiếu thông tin', 'Cần nhập tên chiến dịch', snackPosition: SnackPosition.BOTTOM);
            return;
          }
          final payload = {
            'name': name.text.trim(),
            'funnel_stage': stage.value,
            'budget': _toDouble(budget),
            'owner': owner.text.trim().isEmpty ? null : owner.text.trim(),
            'channels': selectedChannels.toList(),
          };
          Get.back<void>();
          if (isEdit) {
            controller.updateCampaign(existing['id'].toString(), payload);
          } else {
            controller.createCampaign(payload);
          }
        },
      ),
    ],
  );
}

// ==========================================
// Nội dung chiến dịch (asset)
// ==========================================

void showAssetForm(BuildContext context, MarketingController controller, String campaignId) {
  final title = TextEditingController();
  final content = TextEditingController();
  final type = 'copy'.obs;

  AppModalDialog.show<void>(
    context: context,
    title: 'Thêm nội dung cho chiến dịch',
    subtitle: 'Nội dung được lưu ở trạng thái Nháp. Việc xuất bản ra ngoài luôn cần người duyệt.',
    icon: Icons.description_outlined,
    maxWidth: 620,
    content: Obx(
      () => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          marketingDropdown(
            value: type.value,
            items: MarketingLabels.assetType.entries.toList(),
            label: 'Loại nội dung',
            onChanged: (v) => type.value = v,
          ),
          marketingTextField(controller: title, label: 'Tiêu đề'),
          marketingTextField(controller: content, label: 'Nội dung', maxLines: 8),
        ],
      ),
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Lưu nháp',
        onSubmit: () {
          if (title.text.trim().isEmpty || content.text.trim().isEmpty) {
            Get.snackbar('Thiếu thông tin', 'Cần nhập tiêu đề và nội dung', snackPosition: SnackPosition.BOTTOM);
            return;
          }
          Get.back<void>();
          controller.createAsset(campaignId, {
            'asset_type': type.value,
            'title': title.text.trim(),
            'content': content.text.trim(),
          });
        },
      ),
    ],
  );
}

// ==========================================
// Thử nghiệm
// ==========================================

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

// ==========================================
// Bài học
// ==========================================

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
          marketingTextField(
            controller: rule,
            label: 'Luật tái sử dụng (tuỳ chọn)',
            hint: 'VD: Khi CPA tăng quá 20% trong 7 ngày thì giảm ngân sách 30%',
            maxLines: 2,
          ),
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
            Get.snackbar('Thiếu thông tin', 'Cần nhập ít nhất quan sát và bài học',
                snackPosition: SnackPosition.BOTTOM);
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

// ==========================================
// Chỉ số
// ==========================================

void showMetricForm(BuildContext context, MarketingController controller, {Map<String, dynamic>? existing}) {
  final name = TextEditingController(text: existing?['metric_name']?.toString() ?? '');
  final value = TextEditingController(text: (existing?['current_value'] ?? '').toString());
  final unit = TextEditingController(text: existing?['unit']?.toString() ?? 'number');
  final category = (existing?['category']?.toString() ?? 'acquisition').obs;

  AppModalDialog.show<void>(
    context: context,
    title: existing == null ? 'Ghi nhận chỉ số' : 'Cập nhật chỉ số',
    subtitle: 'Giá trị cũ được lưu làm mốc so sánh để phát hiện bất thường.',
    icon: Icons.insights_outlined,
    maxWidth: 560,
    content: Obx(
      () => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          marketingTextField(
            controller: name,
            label: 'Mã chỉ số',
            hint: 'ad_spend, revenue, new_customers, active_customers, churn_rate...',
          ),
          marketingTextField(controller: value, label: 'Giá trị', numeric: true),
          marketingDropdown(
            value: category.value,
            items: MarketingLabels.metricCategory.entries.toList(),
            label: 'Nhóm chỉ số',
            onChanged: (v) => category.value = v,
          ),
          marketingTextField(controller: unit, label: 'Đơn vị', hint: 'number, currency, percentage'),
        ],
      ),
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Lưu chỉ số',
        onSubmit: () {
          if (name.text.trim().isEmpty) {
            Get.snackbar('Thiếu thông tin', 'Cần nhập mã chỉ số', snackPosition: SnackPosition.BOTTOM);
            return;
          }
          Get.back<void>();
          controller.upsertMetric({
            'metric_name': name.text.trim(),
            'value': _toDouble(value),
            'category': category.value,
            'unit': unit.text.trim().isEmpty ? 'number' : unit.text.trim(),
          });
        },
      ),
    ],
  );
}

// ==========================================
// Bối cảnh Marketing
// ==========================================

void showContextForm(BuildContext context, MarketingController controller) {
  final ctx = controller.marketingContext;
  String textOf(String key) {
    final value = ctx[key];
    if (value == null) return '';
    if (value is Map && value['summary'] != null) return value['summary'].toString();
    if (value is Map || value is List) return '';
    return value.toString();
  }

  final icp = TextEditingController(text: textOf('icp'));
  final positioning = TextEditingController(text: textOf('positioning'));
  final valueProp = TextEditingController(text: textOf('value_proposition'));
  final brandVoice = TextEditingController(text: textOf('brand_voice'));
  final pricing = TextEditingController(text: textOf('pricing'));
  final constraints = TextEditingController(
    text: ((ctx['constraints'] as List<dynamic>?) ?? const []).join('\n'),
  );

  AppModalDialog.show<void>(
    context: context,
    title: 'Cập nhật bối cảnh Marketing',
    subtitle: 'Javis là nguồn sự thật duy nhất về bối cảnh; skill bên ngoài chỉ nhận gói tối thiểu.',
    icon: Icons.hub_outlined,
    maxWidth: 640,
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        marketingTextField(
          controller: icp,
          label: 'Chân dung khách hàng lý tưởng (ICP)',
          maxLines: 3,
        ),
        marketingTextField(controller: positioning, label: 'Tuyên bố định vị', maxLines: 3),
        marketingTextField(controller: valueProp, label: 'Tuyên ngôn giá trị', maxLines: 3),
        marketingTextField(controller: brandVoice, label: 'Giọng điệu thương hiệu', maxLines: 2),
        marketingTextField(controller: pricing, label: 'Chính sách giá', maxLines: 2),
        marketingTextField(
          controller: constraints,
          label: 'Ràng buộc (mỗi dòng một mục)',
          hint: 'VD: công ty một người\nngân sách hạn chế',
          maxLines: 3,
        ),
      ],
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Lưu bối cảnh',
        onSubmit: () {
          Map<String, dynamic>? wrap(TextEditingController c) =>
              c.text.trim().isEmpty ? null : {'summary': c.text.trim()};

          Get.back<void>();
          controller.saveContext({
            'icp': wrap(icp),
            'positioning': wrap(positioning),
            'value_proposition': wrap(valueProp),
            'brand_voice': wrap(brandVoice),
            'pricing': wrap(pricing),
            'constraints': constraints.text.trim().isEmpty
                ? null
                : constraints.text.trim().split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
          });
        },
      ),
    ],
  );
}

// ==========================================
// Phê duyệt
// ==========================================

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
              MarketingKeyValue(
                label: 'Do agent đề xuất',
                value: approval['requested_by_agent']?.toString() ?? '—',
              ),
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

// ==========================================
// Customer Research Form (§10)
// ==========================================

void showCustomerResearchForm(BuildContext context, MarketingController controller) {
  final current = controller.customerResearch;
  final segments = TextEditingController(text: (current['segments'] is List) ? (current['segments'] as List).join('\n') : (current['segments']?.toString() ?? ''));
  final jtbd = TextEditingController(text: (current['jtbd'] is List) ? (current['jtbd'] as List).join('\n') : (current['jtbd']?.toString() ?? ''));
  final pains = TextEditingController(text: (current['pains'] is List) ? (current['pains'] as List).join('\n') : (current['pains']?.toString() ?? ''));
  final facts = TextEditingController(text: (current['facts'] is List) ? (current['facts'] as List).join('\n') : (current['facts']?.toString() ?? ''));
  final hypotheses = TextEditingController(text: (current['hypotheses'] is List) ? (current['hypotheses'] as List).join('\n') : (current['hypotheses']?.toString() ?? ''));

  AppModalDialog.show<void>(
    context: context,
    title: 'Nghiên cứu Khách hàng (Customer Research)',
    subtitle: 'Phân loại kết luận theo FACT (sự thật kiểm chứng) và HYPOTHESIS (giả thuyết cần kiểm định) (§10).',
    icon: Icons.person_search_outlined,
    maxWidth: 620,
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        marketingTextField(controller: segments, label: 'Phân khúc khách hàng mục tiêu (mỗi dòng 1 phân khúc)', maxLines: 3),
        marketingTextField(controller: jtbd, label: 'Việc cần làm (Jobs-to-be-Done)', maxLines: 3),
        marketingTextField(controller: pains, label: 'Nỗi đau & Rào cản mua hàng (Pains & Objections)', maxLines: 3),
        marketingTextField(controller: facts, label: 'Sự thật đã kiểm chứng (FACTS)', maxLines: 3),
        marketingTextField(controller: hypotheses, label: 'Giả thuyết đang cần kiểm định (HYPOTHESES)', maxLines: 3),
      ],
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Lưu nghiên cứu',
        onSubmit: () {
          List<String> toLines(TextEditingController c) =>
              c.text.trim().split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();

          Get.back<void>();
          controller.saveCustomerResearch({
            'segments': toLines(segments),
            'jtbd': toLines(jtbd),
            'pains': toLines(pains),
            'facts': toLines(facts),
            'hypotheses': toLines(hypotheses),
          });
        },
      ),
    ],
  );
}

// ==========================================
// Product Marketing & Positioning Form (§11)
// ==========================================

void showProductMarketingForm(BuildContext context, MarketingController controller) {
  final current = controller.productMarketing;
  final category = TextEditingController(text: current['category']?.toString() ?? '');
  final alternatives = TextEditingController(text: (current['alternatives'] is List) ? (current['alternatives'] as List).join('\n') : (current['alternatives']?.toString() ?? ''));
  final differentiators = TextEditingController(text: (current['differentiators'] is List) ? (current['differentiators'] as List).join('\n') : (current['differentiators']?.toString() ?? ''));
  final positioningStatement = TextEditingController(text: current['positioning_statement']?.toString() ?? '');

  AppModalDialog.show<void>(
    context: context,
    title: 'Product Marketing & Định vị (§11)',
    subtitle: 'Xác định rõ Category, giải pháp thay thế, điểm khác biệt độc bản và thông điệp.',
    icon: Icons.rocket_launch_outlined,
    maxWidth: 620,
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        marketingTextField(controller: category, label: 'Ngành hàng / Category', hint: 'VD: AI Marketing Operating System'),
        marketingTextField(controller: alternatives, label: 'Các giải pháp thay thế mà khách hàng đang dùng', maxLines: 3),
        marketingTextField(controller: differentiators, label: 'Điểm khác biệt độc bản (Differentiators)', maxLines: 3),
        marketingTextField(controller: positioningStatement, label: 'Tuyên bố định vị cốt lõi (Positioning Statement)', maxLines: 3),
      ],
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Lưu định vị',
        onSubmit: () {
          List<String> toLines(TextEditingController c) =>
              c.text.trim().split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();

          Get.back<void>();
          controller.saveProductMarketing({
            'category': category.text.trim(),
            'alternatives': toLines(alternatives),
            'differentiators': toLines(differentiators),
            'positioning_statement': positioningStatement.text.trim(),
          });
        },
      ),
    ],
  );
}

// ==========================================
// Offer Architecture Form (§12)
// ==========================================

void showOfferArchitectureForm(BuildContext context, MarketingController controller) {
  final current = controller.offerArchitecture;
  final coreOffer = TextEditingController(text: current['core_offer']?.toString() ?? '');
  final value = TextEditingController(text: current['value']?.toString() ?? '');
  final proof = TextEditingController(text: current['proof']?.toString() ?? '');
  final bonus = TextEditingController(text: current['bonus']?.toString() ?? '');
  final guarantee = TextEditingController(text: current['guarantee']?.toString() ?? '');
  final urgency = TextEditingController(text: current['urgency']?.toString() ?? '');
  final cta = TextEditingController(text: current['cta']?.toString() ?? '');

  AppModalDialog.show<void>(
    context: context,
    title: 'Kiến trúc Ưu đãi (Offer Architecture §12)',
    subtitle: 'Thiết kế gói ưu đãi không thể từ chối: Core Offer + Value + Proof + Bonus + Guarantee + Urgency + CTA.',
    icon: Icons.local_offer_outlined,
    maxWidth: 620,
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        marketingTextField(controller: coreOffer, label: 'Ưu đãi cốt lõi (Core Offer)', hint: 'VD: 14 ngày dùng thử miễn phí đầy đủ tính năng'),
        marketingTextField(controller: value, label: 'Giá trị mang lại (Value)', maxLines: 2),
        marketingTextField(controller: proof, label: 'Bảo chứng & Bằng chứng (Proof)', maxLines: 2),
        marketingTextField(controller: bonus, label: 'Quà tặng kèm (Bonus / Add-ons)', maxLines: 2),
        marketingTextField(controller: guarantee, label: 'Cam kết đảo ngược rủi ro (Risk Reversal / Guarantee)', hint: 'VD: Hoàn tiền 100% trong 30 ngày nếu không hài lòng'),
        marketingTextField(controller: urgency, label: 'Yếu tố thúc đẩy / Khan hiếm (Urgency / Scarcity)', hint: 'VD: Dành cho 50 tài khoản đăng ký sớm'),
        marketingTextField(controller: cta, label: 'Lời kêu gọi hành động (Call to Action)', hint: 'VD: Bắt đầu dùng thử miễn phí ngay'),
      ],
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Lưu kiến trúc ưu đãi',
        onSubmit: () {
          Get.back<void>();
          controller.saveOfferArchitecture({
            'core_offer': coreOffer.text.trim(),
            'value': value.text.trim(),
            'proof': proof.text.trim(),
            'bonus': bonus.text.trim(),
            'guarantee': guarantee.text.trim(),
            'urgency': urgency.text.trim(),
            'cta': cta.text.trim(),
          });
        },
      ),
    ],
  );
}

// ==========================================
// Marketing Loop Form (§18)
// ==========================================

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

// ==========================================
// Decision Journal Form (§53)
// ==========================================

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

// ==========================================
// Multi-touch Attribution Dialog (§28)
// ==========================================

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

// ==========================================
// Market Validation Dialogs (§16 - §48)
// ==========================================

void showExtractAssumptionsDialog(BuildContext context, MarketingController controller) {
  final textCtrl = TextEditingController();
  bool saveToDb = true;

  AppModalDialog.show<void>(
    context: context,
    title: 'AI Trích xuất Giả định (§18)',
    subtitle: 'COSA Business Assumption Analyst phân tích và xếp hạng điểm rủi ro Criticality (1-25).',
    icon: Icons.auto_awesome_rounded,
    maxWidth: 600,
    content: StatefulBuilder(
      builder: (context, setState) {
        return Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            marketingTextField(
              controller: textCtrl,
              label: 'Văn bản / Ý tưởng / Mô tả sản phẩm',
              hint: 'Dán mô tả dự án, kế hoạch hoặc giả định vào đây để AI phân tích...',
              maxLines: 6,
            ),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Tự động lưu giả định vào cơ sở dữ liệu', style: TextStyle(fontSize: 12)),
              value: saveToDb,
              onChanged: (v) => setState(() => saveToDb = v ?? true),
              controlAffinity: ListTileControlAffinity.leading,
            ),
          ],
        );
      },
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Trích xuất Giả định',
        onSubmit: () {
          if (textCtrl.text.trim().isEmpty) return;
          Get.back<void>();
          controller.extractAssumptionsAI(textCtrl.text.trim(), saveToDb: saveToDb);
        },
      ),
    ],
  );
}

void showCreateAssumptionDialog(BuildContext context, MarketingController controller, {Map<String, dynamic>? existing}) {
  final isEditing = existing != null;
  final statementCtrl = TextEditingController(text: existing?['statement']?.toString() ?? '');
  final rationaleCtrl = TextEditingController(text: existing?['rationale']?.toString() ?? '');
  String category = existing?['category']?.toString() ?? 'customer';
  int impact = (existing?['impact'] is num) ? (existing?['impact'] as num).toInt() : 4;
  int uncertainty = (existing?['uncertainty'] is num) ? (existing?['uncertainty'] as num).toInt() : 4;

  const categoryOptions = [
    MapEntry('customer', 'Khách hàng mục tiêu (Customer)'),
    MapEntry('problem', 'Nỗi đau / Vấn đề (Problem)'),
    MapEntry('value_proposition', 'Đề xuất giá trị (Value Proposition)'),
    MapEntry('positioning', 'Định vị (Positioning)'),
    MapEntry('pricing', 'Định giá (Pricing)'),
    MapEntry('channel', 'Kênh phân phối (Channel)'),
    MapEntry('offer', 'Cấu trúc Offer (Offer)'),
  ];

  AppModalDialog.show<void>(
    context: context,
    title: isEditing ? 'Chỉnh sửa Giả định' : 'Thêm Giả định mới (§16)',
    subtitle: 'Đánh giá mức độ Tác động (1-5) và Độ bất định (1-5) để tính điểm Criticality.',
    icon: Icons.lightbulb_outline_rounded,
    maxWidth: 580,
    content: StatefulBuilder(
      builder: (context, setState) {
        final criticality = impact * uncertainty;
        return Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            marketingDropdown(
              value: category,
              items: categoryOptions,
              label: 'Phân loại (Category)',
              onChanged: (v) => setState(() => category = v),
            ),
            marketingTextField(
              controller: statementCtrl,
              label: 'Nội dung Giả định (Statement)',
              hint: 'Ví dụ: Khách hàng sẵn sàng trả 500k/tháng...',
              maxLines: 2,
            ),
            marketingTextField(
              controller: rationaleCtrl,
              label: 'Lý do / Căn cứ ban đầu (Rationale)',
              hint: 'Lý do chúng ta tin điều này đúng...',
              maxLines: 2,
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Tác động (Impact: $impact/5)', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                      Slider(
                        value: impact.toDouble(),
                        min: 1,
                        max: 5,
                        divisions: 4,
                        label: '$impact',
                        activeColor: AppTheme.primaryLight,
                        onChanged: (v) => setState(() => impact = v.toInt()),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Độ bất định (Uncertainty: $uncertainty/5)', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                      Slider(
                        value: uncertainty.toDouble(),
                        min: 1,
                        max: 5,
                        divisions: 4,
                        label: '$uncertainty',
                        activeColor: Colors.amberAccent,
                        onChanged: (v) => setState(() => uncertainty = v.toInt()),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: (criticality >= 15 ? AppTheme.error : (criticality >= 7 ? Colors.amber : AppTheme.success)).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(
                    criticality >= 15 ? Icons.warning_amber_rounded : Icons.info_outline_rounded,
                    size: 16,
                    color: criticality >= 15 ? AppTheme.error : Colors.amberAccent,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Điểm rủi ro (Criticality): $criticality/25 · ${criticality >= 15 ? 'Critical (Cần thử nghiệm gấp)' : (criticality >= 7 ? 'Moderate' : 'Low')}',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: criticality >= 15 ? AppTheme.error : Colors.amberAccent,
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    ),
    actions: [
      marketingDialogActions(
        submitLabel: isEditing ? 'Cập nhật' : 'Tạo Giả định',
        onSubmit: () {
          if (statementCtrl.text.trim().isEmpty) return;
          Get.back<void>();
          final payload = {
            'statement': statementCtrl.text.trim(),
            'category': category,
            'impact': impact,
            'uncertainty': uncertainty,
            'rationale': rationaleCtrl.text.trim(),
          };
          if (isEditing) {
            controller.updateAssumption(existing['id'].toString(), payload);
          } else {
            controller.createAssumption(payload);
          }
        },
      ),
    ],
  );
}

void showAddEvidenceDialog(BuildContext context, MarketingController controller, String assumptionId) {
  final statementCtrl = TextEditingController();
  String strength = 'medium';
  bool isSupporting = true;

  const strengthOptions = [
    MapEntry('strong', 'Mạnh (Dữ liệu giao dịch, phỏng vấn sâu)'),
    MapEntry('medium', 'Trung bình (Click test, survey nhỏ)'),
    MapEntry('weak', 'Yếu (Nhận định cá nhân, phản hồi đơn lẻ)'),
  ];

  AppModalDialog.show<void>(
    context: context,
    title: 'Ghi nhận Bằng chứng (Evidence)',
    subtitle: 'Liên kết bằng chứng thị trường để cập nhật trạng thái giả định (§33, §34).',
    icon: Icons.verified_rounded,
    maxWidth: 560,
    content: StatefulBuilder(
      builder: (context, setState) {
        return Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: ChoiceChip(
                    label: const Center(child: Text('✅ Bằng chứng Xác nhận (Support)')),
                    selected: isSupporting,
                    selectedColor: AppTheme.success.withValues(alpha: 0.25),
                    onSelected: (v) => setState(() => isSupporting = true),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ChoiceChip(
                    label: const Center(child: Text('❌ Bằng chứng Bác bỏ (Contradict)')),
                    selected: !isSupporting,
                    selectedColor: AppTheme.error.withValues(alpha: 0.25),
                    onSelected: (v) => setState(() => isSupporting = false),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            marketingDropdown(
              value: strength,
              items: strengthOptions,
              label: 'Độ mạnh bằng chứng (Strength)',
              onChanged: (v) => setState(() => strength = v),
            ),
            marketingTextField(
              controller: statementCtrl,
              label: 'Nội dung bằng chứng thực tế',
              hint: 'Ví dụ: 8/10 khách hàng phỏng vấn xác nhận tính năng này là bắt buộc...',
              maxLines: 3,
            ),
          ],
        );
      },
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Lưu Bằng chứng',
        onSubmit: () async {
          if (statementCtrl.text.trim().isEmpty) return;
          Get.back<void>();
          final payload = {
            'statement': statementCtrl.text.trim(),
            'source_type': 'founder_observation',
            'strength': strength,
            'supports_assumption_ids': isSupporting ? [assumptionId] : [],
            'contradicts_assumption_ids': !isSupporting ? [assumptionId] : [],
            if (controller.selectedProjectId.value != null)
              'project_id': int.tryParse(controller.selectedProjectId.value!),
          };
          await controller.createEvidence(payload);
        },
      ),
    ],
  );
}


