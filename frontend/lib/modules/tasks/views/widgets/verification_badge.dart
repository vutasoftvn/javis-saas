import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/localization/app_translations.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/verification_report_model.dart';

/// Huy hiệu kết quả Verifier trên thẻ Kanban. Chạm để xem từng tiêu chí.
/// Chỉ hiển thị mã (id tiêu chí, kết quả, mã lý do) — không diễn giải tự do.
class VerificationBadge extends StatelessWidget {
  final VerificationReportModel report;

  const VerificationBadge({super.key, required this.report});

  static Color colorOf(VerificationVerdict v) => switch (v) {
        VerificationVerdict.pass => const Color(0xFF10B981),
        VerificationVerdict.fail => const Color(0xFFEF4444),
        VerificationVerdict.inconclusive => const Color(0xFFF59E0B),
      };

  static String labelOf(VerificationVerdict v) => switch (v) {
        VerificationVerdict.pass => L10nKey.tasksVerifyPass.tr,
        VerificationVerdict.fail => L10nKey.tasksVerifyFail.tr,
        VerificationVerdict.inconclusive => L10nKey.tasksVerifyInconclusive.tr,
      };

  @override
  Widget build(BuildContext context) {
    final color = colorOf(report.verdict);
    return InkWell(
      borderRadius: BorderRadius.circular(3),
      onTap: () => showModalBottomSheet<void>(
        context: context,
        backgroundColor: AppTheme.surfaceDarkLighter,
        builder: (_) => _VerificationSheet(report: report),
      ),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(3),
        ),
        child: Text(
          labelOf(report.verdict),
          style: TextStyle(fontSize: 9.5, color: color),
        ),
      ),
    );
  }
}

class _VerificationSheet extends StatelessWidget {
  final VerificationReportModel report;

  const _VerificationSheet({required this.report});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    L10nKey.tasksVerifyDetailTitle.tr,
                    style: const TextStyle(
                        fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white),
                  ),
                ),
                VerificationBadge(report: report),
              ],
            ),
            const SizedBox(height: 10),
            if (report.criteria.isEmpty)
              Text(
                L10nKey.tasksVerifyNoCriteria.tr,
                style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
              )
            else
              Flexible(
                child: ListView(
                  shrinkWrap: true,
                  children: [
                    for (final c in report.criteria)
                      ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        title: Text(
                          c.id,
                          style: const TextStyle(fontSize: 12.5, color: Colors.white),
                        ),
                        subtitle: Text(
                          [
                            c.required
                                ? L10nKey.tasksVerifyRequired.tr
                                : L10nKey.tasksVerifyOptional.tr,
                            c.verdict,
                            if (c.reason.isNotEmpty) c.reason,
                          ].join(' · '),
                          style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                        ),
                      ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
