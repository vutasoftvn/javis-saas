import 'package:flutter/material.dart';

class LeadScoringList extends StatelessWidget {
  final List<dynamic> leads;
  final Function(String leadId)? onScoreLead;
  final Function(String leadId, String name, String company)? onComposeOutreach;
  final Function(String leadId, String name, String company)? onConvertToDeal;

  const LeadScoringList({
    super.key,
    required this.leads,
    this.onScoreLead,
    this.onComposeOutreach,
    this.onConvertToDeal,
  });

  @override
  Widget build(BuildContext context) {
    if (leads.isEmpty) {
      return Container(
        height: 250,
        alignment: Alignment.center,
        child: const Text(
          'Chưa có khách hàng tiềm năng nào trong danh sách.',
          style: TextStyle(color: Color(0xFF64748B), fontSize: 14),
        ),
      );
    }

    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: leads.length,
      separatorBuilder: (context, index) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final lead = leads[index] as Map<String, dynamic>;
        return _buildLeadItem(context, lead);
      },
    );
  }

  Widget _buildLeadItem(BuildContext context, Map<String, dynamic> lead) {
    final leadId = lead['id']?.toString() ?? '';
    final name = lead['name']?.toString() ?? 'Khách hàng';
    final company = lead['company']?.toString() ?? 'Doanh nghiệp';
    final email = lead['email']?.toString() ?? '';
    final phone = lead['phone']?.toString() ?? '';
    final fitScore = (lead['fit_score'] as num?)?.toDouble() ?? 50.0;
    final status = lead['qualification_status']?.toString() ?? 'NURTURE';
    final source = lead['source']?.toString() ?? 'Landing Page';

    Color scoreColor;
    if (fitScore >= 80) {
      scoreColor = const Color(0xFF10B981);
    } else if (fitScore >= 60) {
      scoreColor = const Color(0xFFF59E0B);
    } else {
      scoreColor = const Color(0xFFEF4444);
    }

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Row(
        children: [
          // Fit Score Circle
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: scoreColor.withValues(alpha: 0.12),
              shape: BoxShape.circle,
              border: Border.all(color: scoreColor.withValues(alpha: 0.4)),
            ),
            alignment: Alignment.center,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  '${fitScore.toInt()}',
                  style: TextStyle(
                    color: scoreColor,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                Text(
                  'FIT',
                  style: TextStyle(
                    color: scoreColor,
                    fontSize: 8,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          // Info Column
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      name,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        company,
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    if (email.isNotEmpty) ...[
                      const Icon(Icons.email_outlined, size: 12, color: Color(0xFF64748B)),
                      const SizedBox(width: 4),
                      Text(email, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                      const SizedBox(width: 10),
                    ],
                    if (phone.isNotEmpty) ...[
                      const Icon(Icons.phone_outlined, size: 12, color: Color(0xFF64748B)),
                      const SizedBox(width: 4),
                      Text(phone, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                    ],
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        source,
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 9,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: status == 'QUALIFIED'
                            ? const Color(0xFF10B981).withValues(alpha: 0.15)
                            : const Color(0xFF38BDF8).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        status,
                        style: TextStyle(
                          color: status == 'QUALIFIED' ? const Color(0xFF10B981) : const Color(0xFF38BDF8),
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          // Actions
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              IconButton(
                icon: const Icon(Icons.auto_awesome_rounded, size: 18, color: Color(0xFF38BDF8)),
                tooltip: 'AI Chấm điểm lại',
                onPressed: () => onScoreLead?.call(leadId),
              ),
              IconButton(
                icon: const Icon(Icons.send_rounded, size: 18, color: Color(0xFF00E5FF)),
                tooltip: 'Soạn thư tiếp cận AI',
                onPressed: () => onComposeOutreach?.call(leadId, name, company),
              ),
              IconButton(
                icon: const Icon(Icons.add_shopping_cart_rounded, size: 18, color: Color(0xFF10B981)),
                tooltip: 'Chuyển thành Deal',
                onPressed: () => onConvertToDeal?.call(leadId, name, company),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
