import 'package:flutter/material.dart';

class ActivationStep1Profile extends StatelessWidget {
  final TextEditingController companyNameController;
  final String selectedIndustry;
  final List<String> industries;
  final ValueChanged<String> onIndustryChanged;
  final String selectedBusinessModel;
  final List<String> businessModels;
  final ValueChanged<String> onBusinessModelChanged;
  final TextEditingController visionController;
  final TextEditingController missionController;
  final VoidCallback onSuggestAiFoundation;

  const ActivationStep1Profile({
    super.key,
    required this.companyNameController,
    required this.selectedIndustry,
    required this.industries,
    required this.onIndustryChanged,
    required this.selectedBusinessModel,
    required this.businessModels,
    required this.onBusinessModelChanged,
    required this.visionController,
    required this.missionController,
    required this.onSuggestAiFoundation,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'BƯỚC 1: HỒ SƠ & BẢN SẮC DOANH NGHIỆP',
          style: TextStyle(
            color: Color(0xFF38BDF8),
            fontSize: 13,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 14),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 3,
              child: _buildTextField(
                label: 'Tên Doanh Nghiệp / Công ty *',
                hint: 'Ví dụ: Miva Corp, TechFlow SaaS...',
                controller: companyNameController,
                icon: Icons.business_rounded,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              flex: 3,
              child: _buildDropdown(
                label: 'Lĩnh vực / Ngành nghề',
                value: selectedIndustry,
                items: industries,
                onChanged: (v) => onIndustryChanged(v!),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              flex: 3,
              child: _buildDropdown(
                label: 'Mô hình kinh doanh',
                value: selectedBusinessModel,
                items: businessModels,
                onChanged: (v) => onBusinessModelChanged(v!),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Tầm nhìn & Sứ mệnh cốt lõi',
              style: TextStyle(color: Colors.white70, fontSize: 12.5, fontWeight: FontWeight.w600),
            ),
            TextButton.icon(
              onPressed: onSuggestAiFoundation,
              icon: const Icon(Icons.auto_awesome, size: 14, color: Color(0xFF38BDF8)),
              label: const Text(
                'AI Tự Động Gợi Ý',
                style: TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Row(
          children: [
            Expanded(
              child: _buildTextField(
                label: 'Tầm nhìn (Vision)',
                hint: 'Đích đến trong 3-5 năm tới...',
                controller: visionController,
                maxLines: 2,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: _buildTextField(
                label: 'Sứ mệnh (Mission)',
                hint: 'Giá trị đem lại cho khách hàng hàng ngày...',
                controller: missionController,
                maxLines: 2,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildTextField({
    required String label,
    required String hint,
    required TextEditingController controller,
    IconData? icon,
    int maxLines = 1,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: Color(0xFF94A3B8),
            fontSize: 11.5,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          maxLines: maxLines,
          style: const TextStyle(color: Colors.white, fontSize: 13),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: const TextStyle(color: Colors.white24, fontSize: 12.5),
            prefixIcon: icon != null ? Icon(icon, color: const Color(0xFF38BDF8), size: 18) : null,
            filled: true,
            fillColor: const Color(0xFF0F172A).withValues(alpha: 0.6),
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: Colors.white12),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: Colors.white12),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: Color(0xFF0EA5E9), width: 1.2),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDropdown({
    required String label,
    required String value,
    required List<String> items,
    required ValueChanged<String?> onChanged,
  }) {
    final effectiveValue = items.contains(value) ? value : (items.isNotEmpty ? items.first : null);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: Color(0xFF94A3B8),
            fontSize: 11.5,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A).withValues(alpha: 0.6),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: Colors.white12),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: effectiveValue,
              isExpanded: true,
              dropdownColor: const Color(0xFF1E293B),
              style: const TextStyle(color: Colors.white, fontSize: 13),
              icon: const Icon(Icons.keyboard_arrow_down, color: Color(0xFF94A3B8), size: 18),
              items: items.map((item) {
                return DropdownMenuItem<String>(
                  value: item,
                  child: Text(item, overflow: TextOverflow.ellipsis),
                );
              }).toList(),
              onChanged: onChanged,
            ),
          ),
        ),
      ],
    );
  }
}
