import 'package:flutter/material.dart';

class HubChatEmptyState extends StatelessWidget {
  final ValueChanged<String> onSelectPrompt;

  const HubChatEmptyState({super.key, required this.onSelectPrompt});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 4),
          const Text(
            'GỢI Ý LỆNH NHANH',
            style: TextStyle(
              color: Color(0xFF64748B),
              fontSize: 14,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 10),
          _buildPromptChip(
            icon: Icons.dashboard_outlined,
            label: 'Tổng quan vận hành hôm nay',
            prompt: 'Tóm tắt tổng quan công việc, OKRs và tình hình vận hành hôm nay.',
          ),
          const SizedBox(height: 8),
          _buildPromptChip(
            icon: Icons.track_changes_outlined,
            label: 'Kiểm tra tiến độ OKRs',
            prompt: 'Báo cáo tình hình thực thi các mục tiêu OKRs quan trọng quý này.',
          ),
          const SizedBox(height: 8),
          _buildPromptChip(
            icon: Icons.checklist_rtl_rounded,
            label: 'Nhiệm vụ cần ưu tiên giải quyết',
            prompt: 'Liệt kê danh sách các công việc và quyết định quan trọng cần Founder xử lý.',
          ),
          const SizedBox(height: 8),
          _buildPromptChip(
            icon: Icons.analytics_outlined,
            label: 'Báo cáo tóm tắt tài chính',
            prompt: 'Tạo báo cáo tóm tắt tài chính và các chỉ số vận hành gần nhất.',
          ),
          const SizedBox(height: 8),
          _buildPromptChip(
            icon: Icons.auto_graph_rounded,
            label: 'Lập chu kỳ chiến lược N tuần',
            prompt: 'Lập chu kỳ 6 tuần kiểm chứng PMF cho Dự án',
          ),
        ],
      ),
    );
  }

  Widget _buildPromptChip({
    required IconData icon,
    required String label,
    required String prompt,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () => onSelectPrompt(prompt),
        hoverColor: const Color(0xFF14B8A6).withValues(alpha: 0.08),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
          decoration: BoxDecoration(
            color: Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: const Color(0xFF334155).withValues(alpha: 0.6),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              Icon(icon, size: 15, color: const Color(0xFF38BDF8)),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    color: Color(0xFFCBD5E1),
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const Icon(Icons.arrow_forward_ios_rounded, size: 11, color: Color(0xFF64748B)),
            ],
          ),
        ),
      ),
    );
  }
}
