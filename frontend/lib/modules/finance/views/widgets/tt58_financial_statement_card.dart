import 'package:flutter/material.dart';

class TT58FinancialStatementCard extends StatelessWidget {
  final Map<String, dynamic>? reportB01;
  final Map<String, dynamic>? reportB02;
  final Map<String, dynamic>? reportB03;
  final Map<String, dynamic>? reportF01;
  final bool showBanner;

  const TT58FinancialStatementCard({
    super.key,
    this.reportB01,
    this.reportB02,
    this.reportB03,
    this.reportF01,
    this.showBanner = true,
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
        // ── Compliance Banner (chỉ hiện ở tab Báo cáo) ─────────────────────
        if (showBanner)
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          margin: const EdgeInsets.only(bottom: 14),
          decoration: BoxDecoration(
            color: isStatutoryRequired
                ? const Color(0xFFF59E0B).withValues(alpha: 0.1)
                : const Color(0xFF10B981).withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
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
                isStatutoryRequired
                    ? Icons.info_outline_rounded
                    : Icons.check_circle_outline_rounded,
                color: isStatutoryRequired
                    ? const Color(0xFFF59E0B)
                    : const Color(0xFF10B981),
                size: 18,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isStatutoryRequired
                          ? 'QUY ĐỊNH BẮT BUỘC NỘP BÁO CÁO TÀI CHÍNH NĂM (P2 / P4)'
                          : 'ĐƯỢC MIỄN NỘP BÁO CÁO TÀI CHÍNH CHO CƠ QUAN THUẾ (P1 / P3)',
                      style: TextStyle(
                        color: isStatutoryRequired
                            ? const Color(0xFFF59E0B)
                            : const Color(0xFF10B981),
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      complianceNote,
                      style: const TextStyle(
                          color: Color(0xFFCBD5E1), fontSize: 12, height: 1.4),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        // ── Hàng 1: B01 + B02 ────────────────────────────────────────────
        IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // B01 – Tình hình Tài chính
              Expanded(
                child: _SectionCard(
                  title: 'B01-DNSN: TÌNH HÌNH TÀI CHÍNH',
                  badge: isBalanced ? 'CÂN ĐỐI 100%' : 'LỆCH CÂN ĐỐI',
                  badgeColor: isBalanced
                      ? const Color(0xFF10B981)
                      : const Color(0xFFEF4444),
                  child: Column(
                    children: [
                      _buildSubBlock(
                        title: 'TỔNG TÀI SẢN',
                        total: _formatVND(
                            assets['total_assets'] as num? ?? 0),
                        color: const Color(0xFF38BDF8),
                        rows: [
                          _RowItem('Tiền & tương đương tiền',
                              _formatVND(assets['cash_and_equivalents'] as num? ?? 0)),
                          _RowItem('Phải thu khách hàng',
                              _formatVND(assets['accounts_receivable'] as num? ?? 0)),
                          _RowItem('Hàng tồn kho',
                              _formatVND(assets['inventories'] as num? ?? 0)),
                        ],
                      ),
                      const SizedBox(height: 10),
                      _buildSubBlock(
                        title: 'TỔNG NGUỒN VỐN',
                        total: _formatVND(
                            capital['total_capital'] as num? ?? 0),
                        color: const Color(0xFF10B981),
                        rows: [
                          _RowItem('Nợ phải trả',
                              _formatVND(capital['total_liabilities'] as num? ?? 0)),
                          _RowItem('Vốn chủ sở hữu',
                              _formatVND(capital['owner_equity'] as num? ?? 0)),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 14),

              // B02 – Kết quả Kinh doanh
              Expanded(
                child: _SectionCard(
                  title: 'B02-DNSN: KẾT QUẢ KINH DOANH',
                  child: Column(
                    children: [
                      _buildB02Row('1. Doanh thu thuần',
                          _formatVND(itemsB02['net_revenue'] as num? ?? 0),
                          isBold: true),
                      _buildB02Row('2. Giá vốn hàng bán',
                          _formatVND(itemsB02['cost_of_goods_sold'] as num? ?? 0)),
                      _buildB02Row('3. Lợi nhuận gộp',
                          _formatVND(itemsB02['gross_profit'] as num? ?? 0),
                          color: const Color(0xFF38BDF8)),
                      _buildB02Row('4. Chi phí hoạt động',
                          _formatVND(itemsB02['operating_expenses'] as num? ?? 0)),
                      _buildB02Row('5. Thuế TNDN',
                          _formatVND(itemsB02['corporate_income_tax'] as num? ?? 0)),
                      const Divider(color: Color(0xFF1E293B), height: 20),
                      _buildB02Row('6. Lợi nhuận sau thuế',
                          _formatVND(itemsB02['net_profit_after_tax'] as num? ?? 0),
                          color: const Color(0xFF10B981),
                          isBold: true),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),

        // ── Hàng 2: B03 + F01 ────────────────────────────────────────────
        IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // B03 – Thuyết minh
              Expanded(
                child: _SectionCard(
                  title: 'B03-DNSN: THUYẾT MINH BÁO CÁO',
                  badge: 'CHÍNH SÁCH KẾ TOÁN',
                  badgeColor: const Color(0xFF00E5FF),
                  child: Column(
                    children: [
                      _buildB02Row('• Đơn vị tiền tệ:',
                          policies['currency']?.toString() ?? 'VND (Đồng Việt Nam)'),
                      _buildB02Row('• Tính giá tồn kho:',
                          policies['inventory_valuation']?.toString() ??
                              'Phương pháp bình quân gia quyền cả kỳ (Weighted Average Cost)'),
                      _buildB02Row('• Khấu hao TSCĐ:',
                          policies['depreciation_method']?.toString() ??
                              'Phương pháp khấu hao đường thẳng'),
                      _buildB02Row('• Ghi nhận doanh thu:',
                          policies['revenue_recognition']?.toString() ??
                              'Ghi nhận khi hoàn thành chuyển giao dịch vụ/hàng hóa'),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 14),

              // F01 – Nghĩa vụ thuế
              Expanded(
                child: _SectionCard(
                  title: 'F01-DNSN: NGHĨA VỤ THUẾ & NSNN',
                  badge: 'Tổng: ${_formatVND(totalTaxDue)}',
                  badgeColor: const Color(0xFFF59E0B),
                  child: taxes.isEmpty
                      ? const Text(
                          'Chưa phát sinh nghĩa vụ thuế trong kỳ.',
                          style: TextStyle(
                              color: Color(0xFF64748B), fontSize: 13),
                        )
                      : Table(
                          border: TableBorder.all(
                              color: const Color(0xFF1E293B), width: 1),
                          columnWidths: const {
                            0: FlexColumnWidth(3),
                            1: FlexColumnWidth(2),
                            2: FlexColumnWidth(2),
                            3: FlexColumnWidth(2),
                          },
                          children: [
                            TableRow(
                              decoration: const BoxDecoration(
                                  color: Color(0xFF131D35)),
                              children: const [
                                Padding(
                                  padding: EdgeInsets.all(8),
                                  child: Text('Sắc thuế',
                                      style: TextStyle(
                                          color: Color(0xFF94A3B8),
                                          fontSize: 12,
                                          fontWeight: FontWeight.bold)),
                                ),
                                Padding(
                                  padding: EdgeInsets.all(8),
                                  child: Text('Phát sinh',
                                      style: TextStyle(
                                          color: Color(0xFF94A3B8),
                                          fontSize: 12,
                                          fontWeight: FontWeight.bold)),
                                ),
                                Padding(
                                  padding: EdgeInsets.all(8),
                                  child: Text('Đã nộp',
                                      style: TextStyle(
                                          color: Color(0xFF10B981),
                                          fontSize: 12,
                                          fontWeight: FontWeight.bold)),
                                ),
                                Padding(
                                  padding: EdgeInsets.all(8),
                                  child: Text('Còn phải nộp',
                                      style: TextStyle(
                                          color: Color(0xFFF59E0B),
                                          fontSize: 12,
                                          fontWeight: FontWeight.bold)),
                                ),
                              ],
                            ),
                            ...taxes.map((t) {
                              final taxMap = t is Map<String, dynamic>
                                  ? t
                                  : <String, dynamic>{};
                              final name =
                                  taxMap['tax_name']?.toString() ?? '';
                              final incurred =
                                  (taxMap['incurred'] as num?) ?? 0;
                              final paid = (taxMap['paid'] as num?) ?? 0;
                              final debt =
                                  (taxMap['closing_debt'] as num?) ?? 0;
                              return TableRow(
                                children: [
                                  Padding(
                                    padding: const EdgeInsets.all(8),
                                    child: Text(name,
                                        style: const TextStyle(
                                            color: Colors.white,
                                            fontSize: 12)),
                                  ),
                                  Padding(
                                    padding: const EdgeInsets.all(8),
                                    child: Text(_formatVND(incurred),
                                        style: const TextStyle(
                                            color: Colors.white,
                                            fontSize: 12)),
                                  ),
                                  Padding(
                                    padding: const EdgeInsets.all(8),
                                    child: Text(_formatVND(paid),
                                        style: const TextStyle(
                                            color: Color(0xFF10B981),
                                            fontSize: 12)),
                                  ),
                                  Padding(
                                    padding: const EdgeInsets.all(8),
                                    child: Text(_formatVND(debt),
                                        style: const TextStyle(
                                            color: Color(0xFFF59E0B),
                                            fontSize: 12)),
                                  ),
                                ],
                              );
                            }),
                          ],
                        ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ── Sub-block: Tài sản / Nguồn vốn ────────────────────────────────────
  Widget _buildSubBlock({
    required String title,
    required String total,
    required Color color,
    required List<_RowItem> rows,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF131D35),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(title,
                  style: const TextStyle(
                      color: Color(0xFF94A3B8),
                      fontSize: 12,
                      fontWeight: FontWeight.bold)),
              Text(total,
                  style: TextStyle(
                      color: color,
                      fontSize: 14,
                      fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 8),
          ...rows.map((r) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2.5),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(r.label,
                        style: const TextStyle(
                            color: Color(0xFFCBD5E1), fontSize: 12)),
                    Text(r.value,
                        style: const TextStyle(
                            color: Color(0xFFCBD5E1), fontSize: 12)),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  // ── Row 2 cột label / value (B02, B03) ────────────────────────────────
  Widget _buildB02Row(String label, String value,
      {Color? color, bool isBold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(label,
                style: TextStyle(
                    color: const Color(0xFF94A3B8),
                    fontSize: 13,
                    fontWeight:
                        isBold ? FontWeight.bold : FontWeight.normal)),
          ),
          const SizedBox(width: 8),
          Text(value,
              style: TextStyle(
                  color: color ?? Colors.white,
                  fontSize: 13,
                  fontWeight:
                      isBold ? FontWeight.bold : FontWeight.normal)),
        ],
      ),
    );
  }
}

// ── Section card wrapper ───────────────────────────────────────────────────
class _SectionCard extends StatelessWidget {
  final String title;
  final String? badge;
  final Color? badgeColor;
  final Widget child;

  const _SectionCard({
    required this.title,
    required this.child,
    this.badge,
    this.badgeColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.2,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (badge != null) ...[
                const SizedBox(width: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: badgeColor!.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    badge!,
                    style: TextStyle(
                      color: badgeColor,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

// Helper value object
class _RowItem {
  final String label;
  final String value;
  const _RowItem(this.label, this.value);
}
