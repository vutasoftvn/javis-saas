import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/finance_controller.dart';
class FinanceBooksTab extends GetView<FinanceController> {
  static final RxInt _expandedBookIndex = (-1).obs;

  const FinanceBooksTab({super.key});

  @override
  Widget build(BuildContext context) => Obx(() {
        final books = controller.books;

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
                          'HỆ THỐNG SỔ KẾ TOÁN THEO THÔNG TƯ 58/2026/TT-BTC',
                          style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Bấm vào từng sổ để xem chi tiết các dòng sổ cái và số dư luỹ kế',
                          style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: () => controller.load(),
                    icon: const Icon(Icons.refresh_rounded, size: 18, color: Color(0xFF94A3B8)),
                    tooltip: 'Làm mới sổ sách',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Content
            if (books.isEmpty)
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
                    Icon(Icons.menu_book_rounded, size: 48, color: Color(0xFF475569)),
                    SizedBox(height: 14),
                    Text(
                      'Chưa có mẫu biểu sổ sách',
                      style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
                    ),
                    SizedBox(height: 6),
                    Text(
                      'Vào tab "Cài đặt" để kích hoạt chế độ kế toán phù hợp.',
                      style: TextStyle(color: Color(0xFF64748B), fontSize: 12),
                    ),
                  ],
                ),
              )
            else
              ...books.asMap().entries.map((entry) {
                final idx = entry.key;
                final bookMap = entry.value is Map<String, dynamic> ? entry.value as Map<String, dynamic> : <String, dynamic>{};
                return _BookAccordionCard(
                  book: bookMap,
                  transactions: controller.transactions,
                  isExpanded: _expandedBookIndex.value == idx,
                  onToggle: () {
                    if (_expandedBookIndex.value == idx) {
                      _expandedBookIndex.value = -1;
                    } else {
                      _expandedBookIndex.value = idx;
                    }
                  },
                );
              }),
          ],
        );
      });
}

class _BookAccordionCard extends StatelessWidget {
  final Map<String, dynamic> book;
  final List<dynamic> transactions;
  final bool isExpanded;
  final VoidCallback onToggle;

  const _BookAccordionCard({
    required this.book,
    required this.transactions,
    required this.isExpanded,
    required this.onToggle,
  });

  String _formatVND(num amount) {
    if (amount >= 1000000000) return '${(amount / 1000000000).toStringAsFixed(1)} tỷ đ';
    if (amount >= 1000000) return '${(amount / 1000000).toStringAsFixed(1)} tr đ';
    if (amount >= 1000) return '${(amount / 1000).toStringAsFixed(0)} k đ';
    return '${amount.toInt()} đ';
  }

  @override
  Widget build(BuildContext context) {
    final code = book['code']?.toString() ?? 'S1-DNSN';
    final name = book['name']?.toString() ?? 'Sổ kế toán';
    final status = book['status']?.toString() ?? 'PRODUCTION_READY';
    final columns = (book['columns'] as List<dynamic>?) ?? [];

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isExpanded ? const Color(0xFF00E5FF).withValues(alpha: 0.4) : const Color(0xFF1E293B),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: onToggle,
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFF00E5FF).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      code,
                      style: const TextStyle(color: Color(0xFF00E5FF), fontWeight: FontWeight.bold, fontSize: 12),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      name,
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      status,
                      style: const TextStyle(color: Color(0xFF10B981), fontSize: 9, fontWeight: FontWeight.bold),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Icon(
                    isExpanded ? Icons.keyboard_arrow_up_rounded : Icons.keyboard_arrow_down_rounded,
                    color: const Color(0xFF64748B),
                  ),
                ],
              ),
            ),
          ),
          if (isExpanded) ...[
            const Divider(height: 1, color: Color(0xFF1E293B)),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'DÒNG SỔ CÁI CHI TIẾT THEO CHỨNG TỪ PHÁT SINH:',
                        style: TextStyle(color: Color(0xFF64748B), fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 0.8),
                      ),
                      Text(
                        'Tổng ${transactions.length} bút toán',
                        style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  if (transactions.isEmpty)
                    Container(
                      padding: const EdgeInsets.all(20),
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: const Color(0xFF131D35),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Text(
                        'Chưa có bút toán nào được ghi vào sổ này.\nHãy tạo chứng từ đầu tiên để cập nhật dòng sổ cái.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Color(0xFF64748B), fontSize: 12),
                      ),
                    )
                  else
                    Table(
                      border: TableBorder.all(color: const Color(0xFF1E293B), width: 1),
                      columnWidths: const {
                        0: FlexColumnWidth(1),
                        1: FlexColumnWidth(3),
                        2: FlexColumnWidth(2),
                        3: FlexColumnWidth(2),
                      },
                      children: [
                        TableRow(
                          decoration: const BoxDecoration(color: Color(0xFF131D35)),
                          children: const [
                            Padding(padding: EdgeInsets.all(8), child: Text('STT', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontWeight: FontWeight.bold))),
                            Padding(padding: EdgeInsets.all(8), child: Text('Diễn giải', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontWeight: FontWeight.bold))),
                            Padding(padding: EdgeInsets.all(8), child: Text('Tiền vào (Thu)', style: TextStyle(color: Color(0xFF10B981), fontSize: 11, fontWeight: FontWeight.bold))),
                            Padding(padding: EdgeInsets.all(8), child: Text('Tiền ra (Chi)', style: TextStyle(color: Color(0xFFEF4444), fontSize: 11, fontWeight: FontWeight.bold))),
                          ],
                        ),
                        ...transactions.asMap().entries.map((entry) {
                          final stt = entry.key + 1;
                          final tx = entry.value as Map<String, dynamic>;
                          final isIncome = tx['direction'] == 'IN';
                          final amt = (tx['amount'] as num?) ?? 0;
                          return TableRow(
                            children: [
                              Padding(padding: const EdgeInsets.all(8), child: Text('$stt', style: const TextStyle(color: Colors.white, fontSize: 11))),
                              Padding(padding: const EdgeInsets.all(8), child: Text(tx['description']?.toString() ?? '', style: const TextStyle(color: Colors.white, fontSize: 11))),
                              Padding(padding: const EdgeInsets.all(8), child: Text(isIncome ? _formatVND(amt) : '-', style: const TextStyle(color: Color(0xFF10B981), fontSize: 11))),
                              Padding(padding: const EdgeInsets.all(8), child: Text(!isIncome ? _formatVND(amt) : '-', style: const TextStyle(color: Color(0xFFEF4444), fontSize: 11))),
                            ],
                          );
                        }),
                      ],
                    ),
                  if (columns.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text('Mẫu biểu TT58 định nghĩa các cột: ${columns.join(', ')}', style: const TextStyle(color: Color(0xFF64748B), fontSize: 10)),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
