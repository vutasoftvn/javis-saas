import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class FundingCatalogTabContent extends StatelessWidget {
  final List<dynamic> currentBenefits;
  final bool isLoading;
  final Function(Map<String, dynamic>) onVerifyProgram;

  const FundingCatalogTabContent({
    super.key,
    required this.currentBenefits,
    required this.isLoading,
    required this.onVerifyProgram,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.accent.withValues(alpha: 0.4)),
            ),
            child: Row(
              children: const [
                Icon(Icons.warning_amber_rounded, color: AppTheme.accent, size: 22),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Dữ liệu khởi tạo từ tài liệu Founders’ Meetup #1 — Chưa xác minh chính thức. '
                    'Founder cần kiểm chứng văn bản/cổng chính thức trước khi sử dụng. Hệ số điểm matching mặc định 0.6 sẽ được tăng lên 1.0 sau khi xác minh.',
                    style: TextStyle(color: Colors.white, fontSize: 13, height: 1.4),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'DANH MỤC 23 QUYỀN LỢI HIỆN HÀNH (6 NHÓM)',
                style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 0.5),
              ),
              Text(
                '${currentBenefits.length} quyền lợi',
                style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (isLoading)
            const Center(child: Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator(color: AppTheme.primary)))
          else if (currentBenefits.isEmpty)
            Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text('Không tìm thấy quyền lợi nào phù hợp.', style: const TextStyle(color: Colors.white54)),
              ),
            )
          else
            ...currentBenefits.map((p) => _buildCatalogBenefitCard(p as Map<String, dynamic>)),
        ],
      ),
    );
  }

  Widget _buildCatalogBenefitCard(Map<String, dynamic> program) {
    final name = program['name'] ?? 'Quyền lợi';
    final authority = program['authority'] ?? 'Cơ quan quản lý';
    final pType = program['program_type'] ?? 'GRANT';
    final summary = program['summary'] ?? '';
    final sourceClaim = program['source_claim'] ?? '';
    final vStatus = program['verification_status'] ?? 'PENDING_FOUNDER_VERIFICATION';
    final fundingMax = (program['funding_max'] as num?)?.toDouble() ?? 0.0;
    final claims = program['claims'] as List<dynamic>? ?? [];

    Color badgeColor;
    String badgeText;
    if (vStatus == 'VERIFIED_ACTIVE') {
      badgeColor = AppTheme.success;
      badgeText = 'ĐÃ XÁC MINH HIỆU LỰC';
    } else if (vStatus == 'VERIFIED_ENACTED') {
      badgeColor = AppTheme.primary;
      badgeText = 'ĐÃ XÁC MINH CĂN CỨ';
    } else {
      badgeColor = AppTheme.accent;
      badgeText = 'CHƯA XÁC MINH CHÍNH THỨC';
    }

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
                    Text(name, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 2),
                    Text(authority, style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12)),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: badgeColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(100),
                  border: Border.all(color: badgeColor.withValues(alpha: 0.4)),
                ),
                child: Text(badgeText, style: TextStyle(color: badgeColor, fontSize: 11, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              _buildPill(pType, AppTheme.primary),
              const SizedBox(width: 8),
              if (fundingMax > 0) ...[
                _buildPill('Hỗ trợ tối đa: ${_formatVnd(fundingMax)}', AppTheme.primaryLight),
                const SizedBox(width: 8),
              ],
              if (claims.isNotEmpty) _buildPill('${claims.length} mệnh đề claim', Colors.white70),
            ],
          ),
          if (summary.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(summary, style: const TextStyle(color: Colors.white70, fontSize: 13)),
          ],
          if (sourceClaim.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text('Nguồn: $sourceClaim', style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12, fontStyle: FontStyle.italic)),
          ],
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              ElevatedButton.icon(
                onPressed: () => onVerifyProgram(program),
                icon: const Icon(Icons.fact_check_outlined, size: 14),
                label: const Text('Kiểm chứng (Founder Verify)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: const Color(0xFF04070E),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPill(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(label, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
    );
  }

  String _formatVnd(double amount) {
    if (amount >= 1000000000) {
      return '${(amount / 1000000000).toStringAsFixed(1)} Tỷ VND';
    } else if (amount >= 1000000) {
      return '${(amount / 1000000).toStringAsFixed(0)} Triệu VND';
    }
    return '${amount.toStringAsFixed(0)} VND';
  }
}
