import 'package:flutter/material.dart';
import '../../../../data/models/stage_model.dart';

class ActivationStep4Diagnostics extends StatelessWidget {
  final ProjectStage selectedStage;
  final String companyName;
  final String projectTitle;
  final String selectedIndustry;

  const ActivationStep4Diagnostics({
    super.key,
    required this.selectedStage,
    required this.companyName,
    required this.projectTitle,
    required this.selectedIndustry,
  });

  @override
  Widget build(BuildContext context) {
    final isFastSprint = selectedStage.index <= ProjectStage.p2SolutionValidation.index;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: (isFastSprint ? const Color(0xFF38BDF8) : const Color(0xFF10B981)).withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.auto_awesome,
                color: isFastSprint ? const Color(0xFF38BDF8) : const Color(0xFF10B981),
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                'BƯỚC 4: AI CHẨN ĐOÁN & ĐỊNH HÌNH LỘ TRÌNH TỐC ĐỘ CAO',
                style: TextStyle(
                  color: isFastSprint ? const Color(0xFF38BDF8) : const Color(0xFF10B981),
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            isFastSprint
                ? '⚡ LỘ TRÌNH ĐƯỢC CHỌN: AI FAST VALIDATION SPRINT (1-2 TUẦN)\n'
                  'Dự án đang ở giai đoạn xác thực (${selectedStage.displayNameVi}). Hệ thống sẽ KHÔNG ép chu kỳ 12 tuần cồng kềnh, '
                  'mà kích hoạt Sprint siêu tốc: AI tự tạo kịch bản phỏng vấn ICP, phân tích rủi ro Solution Bias và chuẩn bị bài đo Willingness-to-pay.'
                : '🎯 LỘ TRÌNH ĐƯỢC CHỌN: 12-WEEK GROWTH CYCLE (12 TUẦN QUẢN TRỊ)\n'
                  'Dự án đã có sản phẩm/khách hàng (${selectedStage.displayNameVi}). Hệ thống sẽ kích hoạt Chu kỳ 12 tuần với bảng OKRs, '
                  'theo dõi chỉ số tài chính, phễu bán hàng và vận hành tự động hoá.',
            style: const TextStyle(color: Colors.white, fontSize: 12.5, height: 1.5),
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.black26,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              children: [
                const Icon(Icons.check_circle_outline, color: Color(0xFF10B981), size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Doanh nghiệp: ${companyName.isEmpty ? "Doanh nghiệp mới" : companyName} • '
                    'Dự án: ${projectTitle.isEmpty ? "Dự án #1" : projectTitle} • '
                    'Ngành: $selectedIndustry',
                    style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
