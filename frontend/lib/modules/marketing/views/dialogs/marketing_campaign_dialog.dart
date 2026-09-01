import 'package:flutter/material.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../../../core/widgets/app_toast.dart';
import '../../controllers/marketing_controller.dart';
import '../widgets/marketing_forms.dart';

void showCreateCampaignDialog(BuildContext context, MarketingController controller) {
  final nameController = TextEditingController();
  final budgetController = TextEditingController(text: '0');
  final ownerController = TextEditingController();
  String stage = kFunnelStages.first.key;
  final selectedChannels = <String>{'SEO', 'Nội dung'};

  AppModalDialog.show(
    context: context,
    title: 'Tạo chiến dịch marketing mới',
    subtitle: 'Mỗi chiến dịch thuộc đúng 1 bước phễu khách hàng',
    icon: Icons.campaign_outlined,
    maxWidth: 580,
    content: StatefulBuilder(
      builder: (ctx, setState) {
        return Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            marketingTextField(controller: nameController, label: 'Tên chiến dịch *', hint: 'VD: Khởi động kênh AEO quý 3'),
            marketingDropdown(
              value: stage,
              items: kFunnelStages,
              label: 'Bước phễu chiến dịch nhắm vào *',
              onChanged: (v) => setState(() => stage = v),
            ),
            marketingTextField(controller: budgetController, label: 'Ngân sách (VNĐ hoặc USD)', numeric: true),
            marketingTextField(controller: ownerController, label: 'Người phụ trách', hint: 'VD: Trưởng nhóm tăng trưởng'),
            const Padding(
              padding: EdgeInsets.only(bottom: 6),
              child: Text('Kênh triển khai:', style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w600)),
            ),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: kChannelOptions.map((ch) {
                final selected = selectedChannels.contains(ch);
                return FilterChip(
                  label: Text(ch, style: TextStyle(color: selected ? Colors.white : Colors.white70, fontSize: 12)),
                  selected: selected,
                  selectedColor: const Color(0xFF4F46E5),
                  backgroundColor: Colors.white.withValues(alpha: 0.05),
                  onSelected: (val) {
                    setState(() {
                      if (val) {
                        selectedChannels.add(ch);
                      } else {
                        selectedChannels.remove(ch);
                      }
                    });
                  },
                );
              }).toList(),
            ),
          ],
        );
      },
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Tạo chiến dịch',
        onSubmit: () {
          final name = nameController.text.trim();
          if (name.isEmpty) {
            AppToast.warning('Vui lòng nhập tên chiến dịch', title: 'Thiếu thông tin');
            return;
          }
          final budget = double.tryParse(budgetController.text.trim()) ?? 0.0;
          final owner = ownerController.text.trim();
          controller.createCampaign({
            'name': name,
            'funnel_stage': stage,
            'channels': selectedChannels.toList(),
            'budget': budget,
            'owner': owner.isEmpty ? null : owner,
          });
          Navigator.of(context).pop();
        },
      ),
    ],
  );
}
