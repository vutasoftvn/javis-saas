import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import 'marketing_common.dart';

export '../dialogs/marketing_campaign_asset_dialogs.dart';
export '../dialogs/marketing_objective_metric_dialogs.dart';
export '../dialogs/marketing_experiment_dialogs.dart';
export '../dialogs/marketing_context_research_dialogs.dart';
export '../dialogs/marketing_governance_decision_dialogs.dart';
export '../dialogs/marketing_assumption_evidence_dialogs.dart';

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
      OutlinedButton(
        onPressed: () => Get.back<void>(),
        style: OutlinedButton.styleFrom(
          foregroundColor: Colors.white70,
          side: BorderSide(color: Colors.white.withValues(alpha: 0.15)),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        child: Text(cancelLabel, style: const TextStyle(fontSize: 13)),
      ),
      const SizedBox(width: 10),
      ElevatedButton(
        onPressed: onSubmit,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppTheme.primary,
          foregroundColor: const Color(0xFF04070E),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        child: Text(submitLabel, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
      ),
    ],
  );
}
