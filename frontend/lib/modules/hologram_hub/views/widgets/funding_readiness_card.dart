import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/routing/module_routes.dart';
import '../../presentation/widgets/glass_card.dart';

class FundingReadinessCard extends StatelessWidget {
  final Map<String, dynamic>? fundingData;

  const FundingReadinessCard({super.key, this.fundingData});

  @override
  Widget build(BuildContext context) {
    // Chỉ coi là đã có dữ liệu đánh giá nếu fundingData có điểm thực tế
    final bool hasEvaluation = fundingData != null &&
        fundingData?['readiness_score_avg'] != null &&
        (fundingData?['readiness_score_avg'] as num) > 0;

    if (!hasEvaluation) {
      return const SizedBox.shrink();
    }

    final readinessScore = (fundingData!['readiness_score_avg'] as num).toDouble();
    final topMatches = (fundingData?['top_matches'] as List?) ?? [];
    final missingCount = (fundingData?['missing_requirements'] as List?)?.length ?? 0;

    return GlassCard(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      borderRadius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF38BDF8).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.account_balance_outlined,
                      color: Color(0xFF38BDF8),
                      size: 18,
                    ),
                  ),
                  const SizedBox(width: 10),
                  const Text(
                    'Mức sẵn sàng nguồn lực',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.3,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: hasEvaluation
                      ? const Color(0xFF10B981).withValues(alpha: 0.15)
                      : const Color(0xFF64748B).withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(100),
                ),
                child: Text(
                  '${readinessScore.toStringAsFixed(0)}/100',
                  style: const TextStyle(
                    color: Color(0xFF10B981),
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Summary Text / Empty State Description
          if (!hasEvaluation) ...[
            const Text(
              'Chưa có dự án nào được phân tích nguồn lực.',
              style: TextStyle(color: Colors.white70, fontSize: 12),
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFF38BDF8).withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.25)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.rocket_launch_outlined, color: Color(0xFF38BDF8), size: 14),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Tạo dự án để COSA AI tự động matching quỹ tài trợ, ưu đãi thuế & credit đám mây.',
                      style: TextStyle(color: Color(0xFFE2E8F0), fontSize: 11, height: 1.3),
                    ),
                  ),
                ],
              ),
            ),
          ] else ...[
            Text(
              topMatches.isNotEmpty
                  ? 'Có ${topMatches.length} cơ hội hỗ trợ phù hợp cao (NATIF, AWS Activate...)'
                  : 'Đã hoàn tất đánh giá sơ bộ cho dự án hiện tại.',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
            const SizedBox(height: 8),
            if (missingCount > 0)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0xFFF59E0B).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline_rounded, color: Color(0xFFF59E0B), size: 14),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'Còn $missingCount minh chứng cần hoàn tất trước hạn nộp hồ sơ',
                        style: const TextStyle(color: Color(0xFFF59E0B), fontSize: 11, fontWeight: FontWeight.w500),
                      ),
                    ),
                  ],
                ),
              ),
          ],
          const SizedBox(height: 12),

          // Action Button
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () {
                // Nếu chưa có dự án thì chuyển sang module Dự án, ngược lại
                // sang module Nguồn lực & Chính sách (Project Funding).
                // Điều hướng route canonical trực tiếp — không còn cần qua
                // `DashboardController.changePage`/`AppRoutes.dashboard` vì
                // `/dashboard` giờ chỉ redirect vào `/hub`, không đọc
                // `currentIndex` nữa (xem module_routes.dart).
                final targetModule = hasEvaluation
                    ? WorkspaceModule.projectFunding
                    : WorkspaceModule.projectRoadmap;
                Get.toNamed(targetModule.path);
              },
              icon: Icon(
                hasEvaluation ? Icons.arrow_forward_rounded : Icons.add_circle_outline_rounded,
                size: 14,
              ),
              label: Text(
                hasEvaluation ? 'Xem phân tích chi tiết & hồ sơ' : 'Khởi tạo dự án & Đánh giá nguồn lực',
                style: const TextStyle(fontSize: 12),
              ),
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF38BDF8),
                side: BorderSide(color: const Color(0xFF38BDF8).withValues(alpha: 0.4)),
                padding: const EdgeInsets.symmetric(vertical: 8),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
