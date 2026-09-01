import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/legal_controller.dart';
import 'widgets/contract_risk_analyzer_dialog.dart';
import 'widgets/compliance_center_panel.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/floating_app_bar.dart';


class LegalView extends StatelessWidget {
  const LegalView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<LegalController>()) {
      Get.put(LegalController());
    }
    final c = Get.find<LegalController>();

    void openContractReviewDialog() {
      showDialog(
        context: context,
        builder: (_) => ContractRiskAnalyzerDialog(
          onAnalyze: c.analyzeContract,
        ),
      );
    }

    void openAddChecklistDialog() {
      final textCtrl = TextEditingController();
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Text('Thêm Hạng Mục Kiểm Tra Pháp Lý', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
          content: TextField(
            controller: textCtrl,
            style: const TextStyle(color: Colors.white, fontSize: 14),
            decoration: InputDecoration(
              hintText: 'Ví dụ: Đăng ký bảo hộ nhãn hiệu, Đăng ký website Bộ Công Thương...',
              hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
              filled: true,
              fillColor: const Color(0xFF131D35),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Hủy', style: TextStyle(color: Color(0xFF94A3B8)))),
            ElevatedButton(
              onPressed: () {
                final t = textCtrl.text.trim();
                if (t.isNotEmpty) {
                  c.createChecklistItem(t);
                  Navigator.of(ctx).pop();
                }
              },
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00E5FF)),
              child: const Text('Thêm mới', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      );
    }

    return Obx(() {
      final statusMap = c.status;
      final openChecklist = statusMap['open_checklist_items'] ?? c.checklist.length;
      final openObligations = statusMap['open_obligations'] ?? c.obligations.length;

      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CosaFloatingAppBar(
            title: 'Pháp lý & Thẩm định Hợp đồng AI',
            subtitle: 'AI Legal Reviewer, rà soát điều khoản rủi ro & quản lý tuân thủ pháp luật DN',
            icon: Icons.gavel_rounded,
            actions: [
              ElevatedButton.icon(
                onPressed: openContractReviewDialog,
                icon: const Icon(Icons.auto_awesome_rounded, size: 16, color: Colors.black),
                label: const Text('Rà soát hợp đồng AI', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF00E5FF),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: () {
                  showDialog(
                    context: context,
                    builder: (_) => Dialog(
                      backgroundColor: const Color(0xFF0F172A),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      child: const SizedBox(
                        width: 700,
                        height: 600,
                        child: ComplianceCenterPanel(),
                      ),
                    ),
                  );
                },
                icon: const Icon(Icons.verified_user_rounded, size: 16, color: Colors.white),
                label: const Text('Tuân thủ AI', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF3B82F6),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(100)),
                ),
              ),
              const SizedBox(width: 8),

              Container(
                decoration: const BoxDecoration(
                  color: AppTheme.surfaceDark,
                  shape: BoxShape.circle,
                ),
                child: IconButton(
                  tooltip: 'Tải lại dữ liệu',
                  icon: const Icon(Icons.refresh_rounded, color: Colors.white, size: 20),
                  onPressed: c.load,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                // Top 3 Metrics
                Row(
                  children: [
                    Expanded(
                      child: _buildMetricCard(
                        context,
                        title: 'Trợ lý Pháp lý',
                        value: 'Legal AI Active',
                        icon: Icons.shield_rounded,
                        color: const Color(0xFF00E5FF),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildMetricCard(
                        context,
                        title: 'Hạng mục kiểm tra',
                        value: '$openChecklist',
                        icon: Icons.fact_check_outlined,
                        color: openChecklist > 0 ? const Color(0xFFF59E0B) : const Color(0xFF10B981),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildMetricCard(
                        context,
                        title: 'Nghĩa vụ pháp lý',
                        value: '$openObligations',
                        icon: Icons.assignment_late_outlined,
                        color: openObligations > 0 ? const Color(0xFFF59E0B) : const Color(0xFF10B981),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // AI Contract Analyzer Quick Banner
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        const Color(0xFF00E5FF).withValues(alpha: 0.12),
                        const Color(0xFF0F172A),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFF00E5FF).withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF00E5FF).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.security_rounded, color: Color(0xFF00E5FF), size: 28),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Text(
                              'AI LEGAL CONTRACT AUDITOR',
                              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                            ),
                            SizedBox(height: 4),
                            Text(
                              'Rà soát tự động các điều khoản rủi ro: trần phạt vi phạm 8% Luật Thương Mại, quyền IP, nghĩa vụ thanh toán, quyền đơn phương chấm dứt...',
                              style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      ElevatedButton(
                        onPressed: openContractReviewDialog,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF00E5FF),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        child: const Text('Thử nghiệm ngay', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Checklist Section
                Container(
                  padding: const EdgeInsets.all(20),
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
                          Row(
                            children: const [
                              Icon(Icons.checklist_rtl_rounded, color: Color(0xFF00E5FF), size: 20),
                              SizedBox(width: 10),
                              Text(
                                'DANH MỤC TUÂN THỦ PHÁP LÝ DOANH NGHIỆP',
                                style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
                              ),
                            ],
                          ),
                          TextButton.icon(
                            onPressed: openAddChecklistDialog,
                            icon: const Icon(Icons.add, size: 16, color: Color(0xFF00E5FF)),
                            label: const Text('Thêm mục kiểm tra', style: TextStyle(color: Color(0xFF00E5FF), fontSize: 12)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      if (c.checklist.isEmpty) ...[
                        _buildDefaultChecklistRow('Đăng ký Giấy phép Kinh doanh & Mã số thuế DN', 'COMPLETED'),
                        _buildDefaultChecklistRow('Đăng ký tài khoản Thuế điện tử (eTax) & Chữ ký số CA', 'COMPLETED'),
                        _buildDefaultChecklistRow('Kê khai chế độ kế toán Thông tư 58/2026/TT-BTC', 'COMPLETED'),
                        _buildDefaultChecklistRow('Đăng ký nhãn hiệu độc quyền tại Cục Sở hữu trí tuệ', 'OPEN'),
                        _buildDefaultChecklistRow('Thông báo Website thương mại điện tử với Bộ Công Thương', 'OPEN'),
                      ] else ...[
                        ...c.checklist.map((item) {
                          final itMap = item is Map<String, dynamic> ? item : <String, dynamic>{};
                          return _buildDefaultChecklistRow(
                            itMap['title']?.toString() ?? '',
                            itMap['status']?.toString() ?? 'OPEN',
                          );
                        }),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Căn Cứ Pháp Lý & Văn Bản Luật (Business Knowledge Pack Legal Subsystem)
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: const [
                          Icon(Icons.gavel_rounded, color: Color(0xFF10B981), size: 20),
                          SizedBox(width: 10),
                          Text(
                            'CĂN CỨ PHÁP LÝ & VĂN BẢN QUẢN TRỊ BẢO CHỨNG',
                            style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Các nguồn luật Việt Nam và cơ chế chuẩn hóa được liên kết trực tiếp vào các quy trình SOP và Hợp đồng mẫu của doanh nghiệp.',
                        style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                      ),
                      const SizedBox(height: 14),
                      if (c.legalSources.isEmpty) ...[
                        _buildDefaultLegalSourceRow('Luật Doanh nghiệp 2020 (59/2020/QH14)', 'Quy định quản trị công ty, thẩm quyền ký kết, điều lệ doanh nghiệp', 'APPLICABLE'),
                        _buildDefaultLegalSourceRow('Luật Thương mại 2005 (36/2005/QH11)', 'Trần phạt vi phạm tối đa 8%, điều kiện miễn trách nhiệm, giao kết hợp đồng', 'APPLICABLE'),
                        _buildDefaultLegalSourceRow('Bộ luật Lao động 2019 (45/2019/QH14)', 'Hợp đồng lao động, thỏa thuận bảo mật NDA, nội quy lao động', 'APPLICABLE'),
                        _buildDefaultLegalSourceRow('Thông tư 58/2026/TT-BTC', 'Chế độ kế toán & chuẩn mực hạch toán tài chính doanh nghiệp', 'APPLICABLE'),
                      ] else ...[
                        ...c.legalSources.map((s) => _buildDefaultLegalSourceRow(
                          s['title'] ?? s['name'] ?? s['id'] ?? '',
                          s['description'] ?? (s['articles'] != null ? 'Điều khoản: ${(s['articles'] as List).join(', ')}' : 'Văn bản bảo chứng'),
                          s['status']?.toString().toUpperCase() ?? 'APPLICABLE',
                        )),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ],
      );
    });
  }

  Widget _buildDefaultLegalSourceRow(String title, String subtitle, String status) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF131D35),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: const Color(0xFF10B981).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.menu_book_rounded, color: Color(0xFF10B981), size: 16),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: const Color(0xFF10B981).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              status,
              style: const TextStyle(color: Color(0xFF10B981), fontSize: 9, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDefaultChecklistRow(String title, String status) {
    final isDone = status == 'COMPLETED';
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF131D35),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Row(
        children: [
          Icon(
            isDone ? Icons.check_circle_rounded : Icons.radio_button_unchecked,
            color: isDone ? const Color(0xFF10B981) : const Color(0xFF64748B),
            size: 18,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              title,
              style: TextStyle(
                color: isDone ? const Color(0xFF94A3B8) : Colors.white,
                fontSize: 13,
                decoration: isDone ? TextDecoration.lineThrough : null,
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: (isDone ? const Color(0xFF10B981) : const Color(0xFFF59E0B)).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              isDone ? 'ĐÃ HOÀN TẤT' : 'CẦN THỰC HIỆN',
              style: TextStyle(
                color: isDone ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
                fontSize: 9,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricCard(
    BuildContext context, {
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
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
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12, fontWeight: FontWeight.w500),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Icon(icon, color: color, size: 18),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
