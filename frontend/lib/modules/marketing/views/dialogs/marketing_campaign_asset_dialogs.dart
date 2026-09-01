import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../../../core/widgets/app_toast.dart';
import '../../controllers/marketing_controller.dart';
import '../widgets/marketing_common.dart';
import '../widgets/marketing_forms.dart';

double _toDouble(TextEditingController c, {double fallback = 0.0}) {
  return double.tryParse(c.text.trim()) ?? fallback;
}

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
            AppToast.warning('Cần nhập tên chiến dịch', title: 'Thiếu thông tin');
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
            AppToast.warning('Cần nhập tiêu đề và nội dung', title: 'Thiếu thông tin');
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
