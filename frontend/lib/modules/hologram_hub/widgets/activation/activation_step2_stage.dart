import 'package:flutter/material.dart';
import '../../../../data/models/stage_model.dart';

class ActivationStep2Stage extends StatelessWidget {
  final TextEditingController projectTitleController;
  final ProjectStage selectedStage;
  final ValueChanged<ProjectStage> onStageChanged;

  const ActivationStep2Stage({
    super.key,
    required this.projectTitleController,
    required this.selectedStage,
    required this.onStageChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'BƯỚC 2: ĐỊNH VỊ DỰ ÁN & GIAI ĐOẠN (STAGE POSITIONING)',
          style: TextStyle(
            color: Color(0xFF38BDF8),
            fontSize: 13,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 14),
        _buildTextField(
          label: 'Tên Dự Án / Dòng Sản Phẩm Cốt Lõi Đầu Tiên *',
          hint: 'Ví dụ: Nền tảng Voice Agent AI, Phần mềm Quản lý F&B...',
          controller: projectTitleController,
          icon: Icons.lightbulb_outline,
        ),
        const SizedBox(height: 16),
        const Text(
          'Chọn Giai đoạn thực tế của Dự án:',
          style: TextStyle(color: Colors.white70, fontSize: 12.5, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            _buildStageChoiceCard(
              stage: ProjectStage.s0Explore,
              title: 'S0. Khám Phá Giả Định',
              subtitle: 'Chưa có ý tưởng rõ ràng, cần quét cơ hội thị trường.',
              track: '⚡ Validation Sprint (1-2 tuần)',
              trackColor: const Color(0xFF38BDF8),
            ),
            const SizedBox(width: 12),
            _buildStageChoiceCard(
              stage: ProjectStage.s1ProblemValidation,
              title: 'S1. Xác Thực Bài Toán',
              subtitle: 'Đang khảo sát nỗi đau khách hàng & JTBD thực tế.',
              track: '⚡ Validation Sprint (1-2 tuần)',
              trackColor: const Color(0xFF38BDF8),
            ),
            const SizedBox(width: 12),
            _buildStageChoiceCard(
              stage: ProjectStage.s2SolutionValidation,
              title: 'S2. Xác Thực Giải Pháp',
              subtitle: 'Đã có MVP/Nguyên mẫu, đang đo lường trả phí (WTP).',
              track: '⚡ Validation Sprint (1-2 tuần)',
              trackColor: const Color(0xFF38BDF8),
            ),
            const SizedBox(width: 12),
            _buildStageChoiceCard(
              stage: ProjectStage.s4GoToMarket,
              title: 'S3-S5. Tăng Trưởng & Vận Hành',
              subtitle: 'Đã có khách hàng trả tiền, cần mở rộng doanh thu.',
              track: '🎯 12-Week Growth Cycle',
              trackColor: const Color(0xFF10B981),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildStageChoiceCard({
    required ProjectStage stage,
    required String title,
    required String subtitle,
    required String track,
    required Color trackColor,
  }) {
    final isSelected = selectedStage == stage;
    return Expanded(
      child: InkWell(
        onTap: () => onStageChanged(stage),
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: isSelected
                ? stage.primaryColor.withValues(alpha: 0.15)
                : const Color(0xFF0F172A).withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected ? stage.primaryColor : Colors.white12,
              width: isSelected ? 1.5 : 1.0,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: TextStyle(
                        color: isSelected ? Colors.white : const Color(0xFFCBD5E1),
                        fontSize: 12.0,
                        fontWeight: FontWeight.bold,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (isSelected) ...[
                    const SizedBox(width: 4),
                    Icon(Icons.check_circle_rounded, color: stage.primaryColor, size: 16),
                  ],
                ],
              ),
              const SizedBox(height: 6),
              Text(
                subtitle,
                style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11, height: 1.3),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: trackColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  track,
                  style: TextStyle(color: trackColor, fontSize: 9.5, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTextField({
    required String label,
    required String hint,
    required TextEditingController controller,
    IconData? icon,
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
          maxLines: 1,
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
}
