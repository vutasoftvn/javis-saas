import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../controllers/marketing_controller.dart';
import '../widgets/marketing_forms.dart';

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
