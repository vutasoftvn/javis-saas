import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/finance_controller.dart';
class FinanceDocumentsTab extends GetView<FinanceController> {
  const FinanceDocumentsTab({super.key});

  void _confirmVoidDocument(BuildContext context, String docId) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Hủy chứng từ này?', style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
        content: const Text(
          'Hệ thống sẽ chuyển trạng thái sang VOIDED và tự động ghi một bút toán đảo để cân đối sổ sách kế toán.',
          style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12, height: 1.4),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Quay lại', style: TextStyle(color: Color(0xFF94A3B8)))),
          ElevatedButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              controller.voidDocument(docId, 'Founder yêu cầu hủy chứng từ');
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFEF4444)),
            child: const Text('Xác nhận Hủy', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Obx(() {
        final docs = controller.documents;

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
                          'QUẢN LÝ CHỨNG TỪ KẾ TOÁN (PHIẾU THU, CHI, HÓA ĐƠN)',
                          style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Lập, ghi sổ và quản lý chứng từ gốc theo Thông tư 58/2026/TT-BTC',
                          style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: () => controller.load(),
                    icon: const Icon(Icons.refresh_rounded, size: 18, color: Color(0xFF94A3B8)),
                    tooltip: 'Làm mới chứng từ',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Content
            if (docs.isEmpty)
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
                    Icon(Icons.description_rounded, size: 48, color: Color(0xFF475569)),
                    SizedBox(height: 14),
                    Text(
                      'Chưa có chứng từ nào được lập',
                      style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
                    ),
                    SizedBox(height: 6),
                    Text(
                      'Bấm "+ Lập chứng từ" trên thanh tiêu đề để tạo Phiếu Thu, Phiếu Chi, Báo Có, Báo Nợ hoặc Hóa Đơn.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Color(0xFF64748B), fontSize: 12),
                    ),
                  ],
                ),
              )
            else
              ...docs.map((doc) {
                final docMap = doc is Map<String, dynamic> ? doc : <String, dynamic>{};
                final docId = docMap['id']?.toString() ?? '';
                final no = docMap['document_no']?.toString() ?? '';
                final type = docMap['document_type']?.toString() ?? 'HOA_DON';
                final status = docMap['status']?.toString() ?? 'DRAFT';
                final date = docMap['document_date']?.toString() ?? '';
                final isPosted = status == 'POSTED';
                final isVoided = status == 'VOIDED';

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
                      Icon(
                        isVoided ? Icons.cancel_outlined : Icons.description_rounded,
                        color: isPosted ? const Color(0xFF10B981) : (isVoided ? const Color(0xFFEF4444) : const Color(0xFFF59E0B)),
                        size: 20,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              no,
                              style: TextStyle(
                                color: isVoided ? const Color(0xFF64748B) : Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 13,
                                decoration: isVoided ? TextDecoration.lineThrough : null,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text('Loại: $type • Ngày: $date', style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: (isPosted ? const Color(0xFF10B981) : (isVoided ? const Color(0xFFEF4444) : const Color(0xFFF59E0B))).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          status,
                          style: TextStyle(
                            color: isPosted ? const Color(0xFF10B981) : (isVoided ? const Color(0xFFEF4444) : const Color(0xFFF59E0B)),
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      if (isPosted && docId.isNotEmpty) ...[
                        const SizedBox(width: 8),
                        IconButton(
                          icon: const Icon(Icons.delete_outline_rounded, color: Color(0xFFEF4444), size: 18),
                          tooltip: 'Hủy chứng từ & sinh bút toán đảo',
                          onPressed: () => _confirmVoidDocument(context, docId),
                        ),
                      ],
                    ],
                  ),
                );
              }),
          ],
        );
      });
}
