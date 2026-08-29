import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class FundingMatchesTabContent extends StatelessWidget {
  final Map<String, dynamic> overviewData;
  final Function(int, String) onCreate12wyTask;

  const FundingMatchesTabContent({
    super.key,
    required this.overviewData,
    required this.onCreate12wyTask,
  });

  @override
  Widget build(BuildContext context) {
    final readinessAvg = (overviewData['readiness_score_avg'] as num?)?.toDouble() ?? 0.0;
    final trlCurrent = (overviewData['trl_current'] as num?)?.toInt() ?? 3;
    final companyType = overviewData['company_type'] ?? 'STARTUP';
    final projectStage = overviewData['project_stage'] ?? 'MVP';
    final topMatches = (overviewData['top_matches'] as List<dynamic>?) ?? [];
    final missingReqs = (overviewData['missing_requirements'] as List<dynamic>?) ?? [];
    final urgentAlerts = (overviewData['urgent_alerts'] as List<dynamic>?) ?? [];

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (urgentAlerts.isNotEmpty)
            Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.error.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.error.withValues(alpha: 0.4)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: const [
                      Icon(Icons.notification_important_rounded, color: AppTheme.error, size: 18),
                      SizedBox(width: 8),
                      Text('CẢNH BÁO TIÊU ĐIỂM & RỦI RO', style: TextStyle(color: AppTheme.error, fontWeight: FontWeight.bold, fontSize: 13)),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ...urgentAlerts.map((a) => Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text('• $a', style: const TextStyle(color: Colors.white70, fontSize: 13)),
                      )),
                ],
              ),
            ),
          Row(
            children: [
              Expanded(
                flex: 2,
                child: _buildMetricCard(
                  title: 'Mức sẵn sàng hồ sơ',
                  value: '${readinessAvg.toStringAsFixed(0)}/100',
                  subtitle: readinessAvg >= 70 ? 'Sẵn sàng nộp hồ sơ' : 'Cần bổ sung thêm minh chứng',
                  icon: Icons.fact_check_outlined,
                  color: readinessAvg >= 70 ? AppTheme.success : AppTheme.accent,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: _buildMetricCard(
                  title: 'Mức sẵn sàng công nghệ',
                  value: 'TRL $trlCurrent',
                  subtitle: _getTrlName(trlCurrent.toInt()),
                  icon: Icons.memory_rounded,
                  color: AppTheme.primary,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 3,
                child: _buildMetricCard(
                  title: 'Phân loại & Giai đoạn',
                  value: _getCompanyTypeName(companyType.toString()),
                  subtitle: 'Giai đoạn: ${_getStageName(projectStage.toString())}',
                  icon: Icons.business_outlined,
                  color: AppTheme.primaryLight,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Section 1: Matched Opportunities
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'CƠ HỘI NGUỒN LỰC PHÙ HỢP (TOP OPPORTUNITIES)',
                style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 0.5),
              ),
              Text(
                '${topMatches.length} chương trình',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (topMatches.isEmpty)
            _buildEmptySection('Chưa có chương trình nào khớp. Nhấn "Khớp nối cơ hội" để AI phân tích.')
          else
            ...topMatches.map((m) => _buildOpportunityCard(m as Map<String, dynamic>)),

          const SizedBox(height: 24),

          // Section 2: Missing Requirements
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'ĐIỀU KIỆN CÒN THIẾU & HÀNH ĐỘNG (GAP ANALYSIS → 12WY)',
                style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 0.5),
              ),
              Text(
                '${missingReqs.length} hạng mục',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (missingReqs.isEmpty)
            _buildEmptySection('Hồ sơ dự án đã đáp ứng đầy đủ các điều kiện cơ bản.')
          else
            ...missingReqs.map((r) => _buildMissingReqCard(r as Map<String, dynamic>)),

          const SizedBox(height: 24),
          _buildFundingStackCard(),
        ],
      ),
    );
  }

  Widget _buildMetricCard({
    required String title,
    required String value,
    required String subtitle,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                const SizedBox(height: 4),
                Text(value, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 2),
                Text(subtitle, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w500), maxLines: 1, overflow: TextOverflow.ellipsis),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOpportunityCard(Map<String, dynamic> match) {
    final progName = match['program_name'] ?? 'Chương trình hỗ trợ';
    final progAuthority = match['program_authority'] ?? 'Cơ quan quản lý';
    final matchScore = ((match['match_score'] ?? 0.0) as num).toDouble();
    final readinessScore = ((match['readiness_score'] ?? 0.0) as num).toDouble();
    final eligibility = match['eligibility_status'] ?? 'POTENTIALLY_ELIGIBLE';
    final summary = match['ai_summary'] ?? '';

    Color statusColor = eligibility == 'ELIGIBLE' ? AppTheme.success : (eligibility == 'INELIGIBLE' ? AppTheme.error : AppTheme.accent);
    String statusText = eligibility == 'ELIGIBLE' ? 'ĐỦ ĐIỀU KIỆN' : (eligibility == 'INELIGIBLE' ? 'CHƯA ĐẠT ĐIỀU KIỆN CỨNG' : 'CÓ KHẢ NĂNG PHÙ HỢP');

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(progName, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 2),
                    Text(progAuthority, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(100),
                  border: Border.all(color: statusColor.withValues(alpha: 0.4)),
                ),
                child: Text(statusText, style: TextStyle(color: statusColor, fontSize: 11, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              _buildPill('Điểm phù hợp: ${matchScore.toStringAsFixed(0)}%', AppTheme.primary),
              const SizedBox(width: 8),
              _buildPill('Sẵn sàng hồ sơ: ${readinessScore.toStringAsFixed(0)}%', AppTheme.primaryLight),
            ],
          ),
          if (summary.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(summary, style: const TextStyle(color: Colors.white70, fontSize: 13)),
          ],
        ],
      ),
    );
  }

  Widget _buildMissingReqCard(Map<String, dynamic> req) {
    final title = req['title'] ?? 'Minh chứng';
    final desc = req['description'] ?? '';
    final reqId = req['id'] as int? ?? 0;
    final isResolved = req['is_resolved'] == true;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Row(
        children: [
          Icon(
            isResolved ? Icons.check_circle_rounded : Icons.pending_actions_rounded,
            color: isResolved ? AppTheme.success : AppTheme.accent,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                if (desc.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(desc, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                ],
              ],
            ),
          ),
          OutlinedButton.icon(
            onPressed: isResolved ? null : () => onCreate12wyTask(reqId, title),
            icon: const Icon(Icons.add_task_rounded, size: 14),
            label: const Text('Thêm vào 12WY', style: TextStyle(fontSize: 12)),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppTheme.primary,
              side: const BorderSide(color: AppTheme.primary),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFundingStackCard() {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(14), border: Border.all(color: AppTheme.borderDark)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.pie_chart_outline_rounded, color: AppTheme.primary, size: 20),
              SizedBox(width: 8),
              Text('CƠ CẤU NGUỒN LỰC ĐỀ XUẤT (FUNDING STACK)', style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 12),
          const Text('Kết hợp đa nguồn lực giúp tối ưu chi phí và mở rộng quy mô mà không làm loãng vốn cổ phần.', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildPill(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(100)),
      child: Text(text, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }

  Widget _buildEmptySection(String msg) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: AppTheme.surfaceDark, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppTheme.borderDark)),
      child: Center(child: Text(msg, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13))),
    );
  }

  String _getCompanyTypeName(String type) => type == 'STARTUP' ? 'Startup khởi nghiệp sáng tạo' : 'Doanh nghiệp khởi nghiệp';
  String _getStageName(String stage) => stage == 'MVP' ? 'Sản phẩm khả dụng tối thiểu (MVP)' : stage;
  String _getTrlName(int trl) => 'TRL $trl — Mức thử nghiệm thực tế';
}
