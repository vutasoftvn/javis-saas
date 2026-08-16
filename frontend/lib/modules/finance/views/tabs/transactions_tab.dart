import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/finance_controller.dart';
class FinanceTransactionsTab extends GetView<FinanceController> {
  const FinanceTransactionsTab({super.key});

  String _formatVND(num amount) {
    if (amount >= 1000000000) return '${(amount / 1000000000).toStringAsFixed(1)} tỷ đ';
    if (amount >= 1000000) return '${(amount / 1000000).toStringAsFixed(1)} tr đ';
    if (amount >= 1000) return '${(amount / 1000).toStringAsFixed(0)} k đ';
    return '${amount.toInt()} đ';
  }

  @override
  Widget build(BuildContext context) => Obx(() {
        final txs = controller.transactions;

        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            // Header Bar
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFF1E293B)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text(
                          'SỔ NHẬT KÝ GIAO DỊCH TIỀN MẶT & NGÂN HÀNG',
                          style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Ghi nhận dòng tiền thu/chi thực tế phát sinh trong doanh nghiệp',
                          style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: () => controller.load(),
                    icon: const Icon(Icons.refresh_rounded, size: 18, color: Color(0xFF94A3B8)),
                    tooltip: 'Làm mới sổ nhật ký',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Content
            if (txs.isEmpty)
              Container(
                padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFF1E293B)),
                ),
                child: Column(
                  children: const [
                    Icon(Icons.receipt_long_rounded, size: 48, color: Color(0xFF475569)),
                    SizedBox(height: 14),
                    Text(
                      'Chưa có giao dịch phát sinh',
                      style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
                    ),
                    SizedBox(height: 6),
                    Text(
                      'Sổ nhật ký sẽ tự động ghi nhận khi bạn lập & ghi sổ chứng từ tại tab "Chứng từ".',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Color(0xFF64748B), fontSize: 12),
                    ),
                  ],
                ),
              )
            else
              ...txs.map((tx) {
                final txMap = tx is Map<String, dynamic> ? tx : <String, dynamic>{};
                final desc = txMap['description']?.toString() ?? 'Giao dịch';
                final amount = (txMap['amount'] as num?) ?? 0;
                final direction = txMap['direction']?.toString() ?? 'IN';
                final isIncome = direction == 'IN';
                final cat = txMap['category']?.toString() ?? 'DOANH_THU';

                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: (isIncome ? const Color(0xFF10B981) : const Color(0xFFEF4444)).withValues(alpha: 0.15),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          isIncome ? Icons.arrow_downward_rounded : Icons.arrow_upward_rounded,
                          color: isIncome ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                          size: 16,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(desc, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500)),
                            const SizedBox(height: 2),
                            Text('Danh mục: $cat', style: const TextStyle(color: Color(0xFF64748B), fontSize: 10)),
                          ],
                        ),
                      ),
                      Text(
                        '${isIncome ? '+' : '-'}${_formatVND(amount)}',
                        style: TextStyle(
                          color: isIncome ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                );
              }),
          ],
        );
      });
}
