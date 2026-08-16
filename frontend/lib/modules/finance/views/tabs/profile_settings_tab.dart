import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/finance_controller.dart';

class FinanceProfileSettingsTab extends GetView<FinanceController> {
  const FinanceProfileSettingsTab({super.key});

  static const List<Map<String, dynamic>> _taxProfiles = [
    {
      'mode': 'TT58_MODE_1',
      'label': 'Chế độ 1 (P1): GTGT % Doanh thu + TNDN % Doanh thu',
      'desc': 'Áp dụng cho DN siêu nhỏ tính thuế trực tiếp theo tỷ lệ % trên doanh thu. Đơn giản nhất. Được miễn nộp Báo cáo tài chính cho cơ quan thuế.',
      'books': ['S1-DNSN (Sổ doanh thu, chi phí, tiền mặt & ngân hàng)'],
    },
    {
      'mode': 'TT58_MODE_2',
      'label': 'Chế độ 2 (P2): GTGT % Doanh thu + TNDN trên Thu nhập tính thuế',
      'desc': 'GTGT tính theo % doanh thu, TNDN tính theo doanh thu trừ chi phí hợp lệ. Bắt buộc lập Báo cáo tài chính năm (B01, B02, B03).',
      'books': ['S2a-DNSN (Doanh thu)', 'S2b-DNSN (Chi phí)', 'S2c-DNSN (Tiền lương)', 'S2d-DNSN (Hàng hóa/Vật tư)'],
    },
    {
      'mode': 'TT58_MODE_3',
      'label': 'Chế độ 3 (P3): GTGT Khấu trừ + TNDN % Doanh thu',
      'desc': 'GTGT áp dụng phương pháp khấu trừ thuế đầu vào, TNDN theo % doanh thu. Được miễn nộp Báo cáo tài chính cho cơ quan thuế.',
      'books': ['S3a-DNSN (Doanh thu & Thuế GTGT)', 'S3b-DNSN (Chi phí & Thuế GTGT)'],
    },
    {
      'mode': 'TT58_MODE_4',
      'label': 'Chế độ 4 (P4): GTGT Khấu trừ + TNDN trên Thu nhập tính thuế',
      'desc': 'Đầy đủ cả GTGT khấu trừ và TNDN tính trên thu nhập chịu thuế. Bắt buộc lập Báo cáo tài chính năm (B01, B02, B03).',
      'books': ['S2b-DNSN', 'S2c-DNSN', 'S2d-DNSN', 'S3b-DNSN'],
    },
  ];

  @override
  Widget build(BuildContext context) => Obx(() {
        final profile = controller.profile;
        final currentMode = profile['mode']?.toString() ?? 'TT58_MODE_1';

        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
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
                      Icon(Icons.gavel_rounded, color: Color(0xFF00E5FF), size: 20),
                      SizedBox(width: 10),
                      Text(
                        'LỰA CHỌN CHẾ ĐỘ KẾ TOÁN (THÔNG TƯ 58/2026/TT-BTC)',
                        style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Doanh nghiệp siêu nhỏ được lựa chọn 1 trong 4 chế độ tính thuế & sổ sách phù hợp với mô hình kinh doanh.',
                    style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                  ),
                  const SizedBox(height: 20),
                  ..._taxProfiles.map((p) {
                    final isSelected = currentMode == p['mode'];
                    final books = p['books'] as List<String>;

                    return Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: isSelected ? const Color(0xFF00E5FF).withValues(alpha: 0.08) : const Color(0xFF131D35),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: isSelected ? const Color(0xFF00E5FF) : const Color(0xFF1E293B),
                          width: isSelected ? 1.5 : 1.0,
                        ),
                      ),
                      child: InkWell(
                        onTap: () => controller.updateProfileMode(p['mode'] as String),
                        borderRadius: BorderRadius.circular(12),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Icon(
                                    isSelected ? Icons.radio_button_checked : Icons.radio_button_off,
                                    color: isSelected ? const Color(0xFF00E5FF) : const Color(0xFF64748B),
                                    size: 18,
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(
                                      p['label'] as String,
                                      style: TextStyle(
                                        color: isSelected ? Colors.white : const Color(0xFFCBD5E1),
                                        fontWeight: FontWeight.bold,
                                        fontSize: 13,
                                      ),
                                    ),
                                  ),
                                  if (isSelected)
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF00E5FF).withValues(alpha: 0.2),
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                      child: const Text(
                                        'ĐANG ÁP DỤNG',
                                        style: TextStyle(color: Color(0xFF00E5FF), fontSize: 9, fontWeight: FontWeight.bold),
                                      ),
                                    ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Padding(
                                padding: const EdgeInsets.only(left: 28),
                                child: Text(p['desc'] as String, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                              ),
                              const SizedBox(height: 8),
                              Padding(
                                padding: const EdgeInsets.only(left: 28),
                                child: Wrap(
                                  spacing: 6,
                                  children: books.map((b) {
                                    return Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF1E293B),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text(b, style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 10)),
                                    );
                                  }).toList(),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
          ],
        );
      });
}
