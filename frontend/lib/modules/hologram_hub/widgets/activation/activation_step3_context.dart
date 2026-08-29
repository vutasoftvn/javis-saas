import 'package:flutter/material.dart';

class ActivationStep3Context extends StatelessWidget {
  final TextEditingController problemController;
  final TextEditingController jtbdController;
  final TextEditingController currentAlternativeController;
  final VoidCallback onSuggestAiProblemContext;

  const ActivationStep3Context({
    super.key,
    required this.problemController,
    required this.jtbdController,
    required this.currentAlternativeController,
    required this.onSuggestAiProblemContext,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'BƯỚC 3: NẠP TRI THỨC & BÀI TOÁN KHÁCH HÀNG (PROBLEM-FIRST CONTEXT)',
              style: TextStyle(
                color: Color(0xFF38BDF8),
                fontSize: 13,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
              ),
            ),
            TextButton.icon(
              onPressed: onSuggestAiProblemContext,
              icon: const Icon(Icons.auto_awesome, size: 14, color: Color(0xFF38BDF8)),
              label: const Text(
                'AI Tự Động Gợi Ý',
                style: TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: _buildTextField(
                label: 'Nỗi đau / Bài toán cốt lõi (Problem Statement) *',
                hint: 'Mô tả vấn đề nghiêm trọng mà khách hàng đang chịu đựng...',
                controller: problemController,
                maxLines: 3,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: _buildTextField(
                label: 'Việc cần làm của khách hàng (Job-to-be-Done)',
                hint: 'Khách hàng muốn đạt được kết quả gì khi dùng sản phẩm...',
                controller: jtbdController,
                maxLines: 3,
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        _buildTextField(
          label: 'Giải pháp thay thế hiện tại (Current Alternative)',
          hint: 'Khách hàng đang giải quyết vấn đề bằng cách nào (Excel, làm thủ công, đối thủ...)?',
          controller: currentAlternativeController,
          maxLines: 2,
        ),
      ],
    );
  }

  Widget _buildTextField({
    required String label,
    required String hint,
    required TextEditingController controller,
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
}
