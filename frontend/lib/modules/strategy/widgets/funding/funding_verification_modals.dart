import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../modules/finance/services/policy_funding_service.dart';

class FundingVerificationModals {
  static void openFounderVerificationModal(
    BuildContext context,
    PolicyFundingService service,
    Map<String, dynamic> program,
    Future<void> Function() onUpdated,
  ) {
    final progId = program['id']?.toString() ?? program['id_str'] ?? '';
    final progName = program['name'] ?? 'Chương trình';
    final authority = program['authority'] ?? '';
    final sourceClaim = program['source_claim'] ?? '';
    final claims = program['claims'] as List<dynamic>? ?? [];

    final urlCtrl = TextEditingController(text: program['source_url'] ?? '');
    final authCtrl = TextEditingController(text: authority);
    final noteCtrl = TextEditingController();
    String selectedStatus = 'VERIFIED_ACTIVE';

    Get.dialog(
      Dialog(
        backgroundColor: AppTheme.surfaceDark,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: AppTheme.borderDark),
        ),
        child: Container(
          width: 720,
          constraints: const BoxConstraints(maxHeight: 650),
          padding: const EdgeInsets.all(24),
          child: StatefulBuilder(
            builder: (context, setModalState) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.verified_user_rounded, color: AppTheme.primary, size: 22),
                          const SizedBox(width: 10),
                          Text(
                            'Kiểm chứng Quyền lợi: $progName',
                            style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      IconButton(
                        onPressed: () => Get.back(),
                        icon: const Icon(Icons.close_rounded, color: AppTheme.textMutedDark),
                      ),
                    ],
                  ),
                  const Divider(color: AppTheme.borderDark),
                  const SizedBox(height: 8),
                  if (sourceClaim.isNotEmpty)
                    Container(
                      padding: const EdgeInsets.all(10),
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: AppTheme.accent.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppTheme.accent.withValues(alpha: 0.3)),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.info_outline, color: AppTheme.accent, size: 16),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Nguồn tham khảo: $sourceClaim',
                              style: const TextStyle(color: Colors.white70, fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    ),
                  Expanded(
                    child: SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (claims.isNotEmpty) ...[
                            const Text(
                              'DANH SÁCH MỆNH ĐỀ TỪ TÀI LIỆU NGUỒN (CLAIMS):',
                              style: TextStyle(color: AppTheme.primaryLight, fontSize: 12, fontWeight: FontWeight.bold),
                            ),
                            const SizedBox(height: 8),
                            ...claims.map((c) {
                              final claimVal = c['claim_value'] ?? '';
                              final claimType = c['claim_type'] ?? '';
                              return Container(
                                margin: const EdgeInsets.only(bottom: 6),
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                decoration: BoxDecoration(
                                  color: const Color(0xFF060A14),
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: AppTheme.borderDark),
                                ),
                                child: Row(
                                  children: [
                                    const Icon(Icons.check_circle_outline, color: AppTheme.primary, size: 14),
                                    const SizedBox(width: 8),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: AppTheme.primary.withValues(alpha: 0.15),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text(claimType, style: const TextStyle(color: AppTheme.primary, fontSize: 10, fontWeight: FontWeight.bold)),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Text(claimVal, style: const TextStyle(color: Colors.white, fontSize: 12)),
                                    ),
                                  ],
                                ),
                              );
                            }),
                            const SizedBox(height: 16),
                          ],
                          const Text(
                            'THÔNG TIN XÁC MINH CHÍNH THỨC:',
                            style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 8),
                          TextField(
                            controller: urlCtrl,
                            style: const TextStyle(color: Colors.white, fontSize: 13),
                            decoration: InputDecoration(
                              labelText: 'Cổng thông tin / Link văn bản chính thức',
                              labelStyle: const TextStyle(color: AppTheme.textMutedDark),
                              hintText: 'https://...',
                              hintStyle: const TextStyle(color: Colors.white24),
                              filled: true,
                              fillColor: const Color(0xFF060A14),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppTheme.borderDark)),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                            ),
                          ),
                          const SizedBox(height: 10),
                          TextField(
                            controller: authCtrl,
                            style: const TextStyle(color: Colors.white, fontSize: 13),
                            decoration: InputDecoration(
                              labelText: 'Cơ quan có thẩm quyền ban hành',
                              labelStyle: const TextStyle(color: AppTheme.textMutedDark),
                              filled: true,
                              fillColor: const Color(0xFF060A14),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppTheme.borderDark)),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                            ),
                          ),
                          const SizedBox(height: 10),
                          TextField(
                            controller: noteCtrl,
                            maxLines: 2,
                            style: const TextStyle(color: Colors.white, fontSize: 13),
                            decoration: InputDecoration(
                              labelText: 'Ghi chú kiểm chứng của Founder',
                              labelStyle: const TextStyle(color: AppTheme.textMutedDark),
                              hintText: 'Ví dụ: Đã đối chiếu với Cổng DVC BKHCN...',
                              hintStyle: const TextStyle(color: Colors.white24),
                              filled: true,
                              fillColor: const Color(0xFF060A14),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppTheme.borderDark)),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                            ),
                          ),
                          const SizedBox(height: 14),
                          const Text(
                            'KẾT QUẢ XÁC MINH:',
                            style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                          ),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              ChoiceChip(
                                label: const Text('Hiệu lực (Active)', style: TextStyle(fontSize: 12)),
                                selected: selectedStatus == 'VERIFIED_ACTIVE',
                                selectedColor: const Color(0xFF10B981),
                                onSelected: (s) => setModalState(() => selectedStatus = 'VERIFIED_ACTIVE'),
                              ),
                              ChoiceChip(
                                label: const Text('Căn cứ (Enacted)', style: TextStyle(fontSize: 12)),
                                selected: selectedStatus == 'VERIFIED_ENACTED',
                                selectedColor: const Color(0xFF00E5FF),
                                onSelected: (s) => setModalState(() => selectedStatus = 'VERIFIED_ENACTED'),
                              ),
                              ChoiceChip(
                                label: const Text('Không đúng / Đóng', style: TextStyle(fontSize: 12)),
                                selected: selectedStatus == 'REJECTED_SOURCE_DATA',
                                selectedColor: const Color(0xFFEF4444),
                                onSelected: (s) => setModalState(() => selectedStatus = 'REJECTED_SOURCE_DATA'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      OutlinedButton(onPressed: () => Get.back(), child: const Text('Hủy')),
                      const SizedBox(width: 10),
                      ElevatedButton.icon(
                        onPressed: () async {
                          Get.back();
                          try {
                            await service.verifyProgram(
                              programId: progId,
                              resultStatus: selectedStatus,
                              officialSourceUrl: urlCtrl.text.trim(),
                              officialAuthority: authCtrl.text.trim(),
                              notes: noteCtrl.text.trim(),
                            );
                            await onUpdated();
                            Get.snackbar(
                              'Đã cập nhật',
                              'Chương trình "$progName" đã được cập nhật trạng thái $selectedStatus.',
                              snackPosition: SnackPosition.BOTTOM,
                              backgroundColor: AppTheme.success.withValues(alpha: 0.2),
                              colorText: Colors.white,
                            );
                          } catch (e) {
                            Get.snackbar('Lỗi xác minh', e.toString(), snackPosition: SnackPosition.BOTTOM);
                          }
                        },
                        icon: const Icon(Icons.check_circle_outline, size: 16),
                        label: const Text('Lưu & Cập nhật Matching'),
                        style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: const Color(0xFF04070E)),
                      ),
                    ],
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
