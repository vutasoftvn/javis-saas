import 'package:flutter/material.dart';

class TT58FinancialStatementCard extends StatelessWidget {
  final Map<String, dynamic>? reportB01;
  final Map<String, dynamic>? reportB02;
  final Map<String, dynamic>? reportB03;
  final Map<String, dynamic>? reportF01;

  const TT58FinancialStatementCard({
    super.key,
    this.reportB01,
    this.reportB02,
    this.reportB03,
    this.reportF01,
  });

  String _formatVND(num amount) {
    if (amount >= 1000000000) {
      return '${(amount / 1000000000).toStringAsFixed(1)} tỷ đ';
    } else if (amount >= 1000000) {
      return '${(amount / 1000000).toStringAsFixed(1)} tr đ';
    } else if (amount >= 1000) {
      return '${(amount / 1000).toStringAsFixed(0)} k đ';
    }
    return '${amount.toInt()} đ';
  }

  @override
  Widget build(BuildContext context) {
    final assets = reportB01?['assets'] as Map<String, dynamic>? ?? {};
    final capital = reportB01?['capital_and_liabilities'] as Map<String, dynamic>? ?? {};
    final isBalanced = reportB01?['is_balanced'] as bool? ?? true;

    final itemsB02 = reportB02?['items'] as Map<String, dynamic>? ?? {};
    final isStatutoryRequired = reportB03?['is_statutory_required'] as bool? ?? false;
    final complianceNote = reportB03?['compliance_note']?.toString() ??
        'Chế độ kế toán đang áp dụng theo Thông tư 58/2026/TT-BTC.';
    final policies = reportB03?['accounting_policies'] as Map<String, dynamic>? ?? {};
    final taxes = (reportF01?['taxes'] as List<dynamic>?) ?? [];
    final totalTaxDue = (reportF01?['total_balance_due'] as num?) ?? 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 0. Compliance Banner
        Container(
          padding: const EdgeInsets.all(16),
          margin: const EdgeInsets.only(bottom: 16),
          decoration: BoxDecoration(
            color: isStatutoryRequired
                ? const Color(0xFFF59E0B).withValues(alpha: 0.1)
                : const Color(0xFF10B981).withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: isStatutoryRequired
                  ? const Color(0xFFF59E0B).withValues(alpha: 0.3)
                  : const Color(0xFF10B981).withValues(alpha: 0.3),
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                isStatutoryRequired ? Icons.info_outline_rounded : Icons.check_circle_outline_rounded,
                color: isStatutoryRequired ? const Color(0xFFF59E0B) : const Color(0xFF10B981),
                size: 20,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isStatutoryRequired
                          ? 'QUY ĐỊNH BẮT BUỘC NỘP BÁO CÁO TÀI CHÍNH NĂM (P2 / P4)'
                          : 'ĐƯỢC MIỄN NỘP BÁO CÁO TÀI CHÍNH CHO CƠ QUAN THUẾ (P1 / P3)',
                      style: TextStyle(
                        color: isStatutoryRequired ? const Color(0xFFF59E0B) : const Color(0xFF10B981),
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      complianceNote,
                      style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 11, height: 1.4),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        // 1. B01-DNSN
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'B01-DNSN: BÁO CÁO TÌNH HÌNH TÀI CHÍNH',
                    style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: isBalanced
                          ? const Color(0xFF10B981).withValues(alpha: 0.15)
                          : const Color(0xFFEF4444).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      isBalanced ? 'CÂN ĐỐI 100%' : 'LỆCH CÂN ĐỐI',
                      style: TextStyle(
                        color: isBalanced ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _buildSubBlock(
                      title: 'TỔNG TÀI SẢN',
                      total: _formatVND(assets['total_assets'] as num? ?? 0),
                      color: const Color(0xFF38BDF8),
                      rows: [
                        'Tiền & tương đương tiền: ${_formatVND(assets['cash_and_equivalents'] as num? ?? 0)}',
                        'Phải thu khách hàng: ${_formatVND(assets['accounts_receivable'] as num? ?? 0)}',
                        'Hàng tồn kho: ${_formatVND(assets['inventories'] as num? ?? 0)}',
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildSubBlock(
                      title: 'TỔNG NGUỒN VỐN',
                      total: _formatVND(capital['total_capital'] as num? ?? 0),
                      color: const Color(0xFF10B981),
                      rows: [
                        'Nợ phải trả: ${_formatVND(capital['total_liabilities'] as num? ?? 0)}',
                        'Vốn chủ sở hữu: ${_formatVND(capital['owner_equity'] as num? ?? 0)}',
                      ],
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // 2. B02-DNSN
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'B02-DNSN: BÁO CÁO KẾT QUẢ KINH DOANH',
                style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              _buildB02Row('1. Doanh thu thuần', _formatVND(itemsB02['net_revenue'] as num? ?? 0), isBold: true),
              _buildB02Row('2. Giá vốn hàng bán', _formatVND(itemsB02['cost_of_goods_sold'] as num? ?? 0)),
              _buildB02Row('3. Lợi nhuận gộp', _formatVND(itemsB02['gross_profit'] as num? ?? 0), color: const Color(0xFF38BDF8)),
              _buildB02Row('4. Chi phí hoạt động', _formatVND(itemsB02['operating_expenses'] as num? ?? 0)),
              _buildB02Row('5. Thuế TNDN', _formatVND(itemsB02['corporate_income_tax'] as num? ?? 0)),
              const Divider(color: Color(0xFF1E293B)),
              _buildB02Row('6. Lợi nhuận sau thuế', _formatVND(itemsB02['net_profit_after_tax'] as num? ?? 0), color: const Color(0xFF10B981), isBold: true),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // 3. B03-DNSN: Thuyết minh Báo cáo tài chính
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'B03-DNSN: BẢN THUYẾT MINH BÁO CÁO TÀI CHÍNH',
                    style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFF00E5FF).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Text('CHÍNH SÁCH KẾ TOÁN', style: TextStyle(color: Color(0xFF00E5FF), fontSize: 9, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              _buildB02Row('• Đơn vị tiền tệ:', policies['currency']?.toString() ?? 'VND'),
              _buildB02Row('• Tính giá tồn kho:', policies['inventory_valuation']?.toString() ?? 'Bình quân gia quyền'),
              _buildB02Row('• Khấu hao TSCĐ:', policies['depreciation_method']?.toString() ?? 'Đường thẳng'),
              _buildB02Row('• Ghi nhận doanh thu:', policies['revenue_recognition']?.toString() ?? 'Khi chuyển giao dịch vụ'),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // 4. F01-DNSN: Báo cáo thực hiện nghĩa vụ với Ngân sách Nhà nước
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'F01-DNSN: BÁO CÁO THỰC HIỆN NGHĨA VỤ THUẾ & NSNN',
                    style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
                  ),
                  Text(
                    'Tổng nghĩa vụ: ${_formatVND(totalTaxDue)}',
                    style: const TextStyle(color: Color(0xFFF59E0B), fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (taxes.isEmpty)
                const Text('Chưa phát sinh nghĩa vụ thuế trong kỳ.', style: TextStyle(color: Color(0xFF64748B), fontSize: 12))
              else
                Table(
                  border: TableBorder.all(color: const Color(0xFF1E293B), width: 1),
                  columnWidths: const {
                    0: FlexColumnWidth(3),
                    1: FlexColumnWidth(2),
                    2: FlexColumnWidth(2),
                    3: FlexColumnWidth(2),
                  },
                  children: [
                    TableRow(
                      decoration: const BoxDecoration(color: Color(0xFF131D35)),
                      children: const [
                        Padding(padding: EdgeInsets.all(8), child: Text('Sắc thuế', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontWeight: FontWeight.bold))),
                        Padding(padding: EdgeInsets.all(8), child: Text('Phát sinh', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontWeight: FontWeight.bold))),
                        Padding(padding: EdgeInsets.all(8), child: Text('Đã nộp', style: TextStyle(color: Color(0xFF10B981), fontSize: 11, fontWeight: FontWeight.bold))),
                        Padding(padding: EdgeInsets.all(8), child: Text('Còn phải nộp', style: TextStyle(color: Color(0xFFF59E0B), fontSize: 11, fontWeight: FontWeight.bold))),
                      ],
                    ),
                    ...taxes.map((t) {
                      final taxMap = t is Map<String, dynamic> ? t : <String, dynamic>{};
                      final name = taxMap['tax_name']?.toString() ?? '';
                      final incurred = (taxMap['incurred'] as num?) ?? 0;
                      final paid = (taxMap['paid'] as num?) ?? 0;
                      final debt = (taxMap['closing_debt'] as num?) ?? 0;

                      return TableRow(
                        children: [
                          Padding(padding: const EdgeInsets.all(8), child: Text(name, style: const TextStyle(color: Colors.white, fontSize: 11))),
                          Padding(padding: const EdgeInsets.all(8), child: Text(_formatVND(incurred), style: const TextStyle(color: Colors.white, fontSize: 11))),
                          Padding(padding: const EdgeInsets.all(8), child: Text(_formatVND(paid), style: const TextStyle(color: Color(0xFF10B981), fontSize: 11))),
                          Padding(padding: const EdgeInsets.all(8), child: Text(_formatVND(debt), style: const TextStyle(color: Color(0xFFF59E0B), fontSize: 11))),
                        ],
                      );
                    }),
                  ],
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSubBlock({
    required String title,
    required String total,
    required Color color,
    required List<String> rows,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF131D35),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(title, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontWeight: FontWeight.bold)),
              Text(total, style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 8),
          ...rows.map((r) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(r, style: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 11)),
              )),
        ],
      ),
    );
  }

  Widget _buildB02Row(String label, String value, {Color? color, bool isBold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: const Color(0xFF94A3B8), fontSize: 12, fontWeight: isBold ? FontWeight.bold : FontWeight.normal)),
          Text(value, style: TextStyle(color: color ?? Colors.white, fontSize: 12, fontWeight: isBold ? FontWeight.bold : FontWeight.normal)),
        ],
      ),
    );
  }
}
