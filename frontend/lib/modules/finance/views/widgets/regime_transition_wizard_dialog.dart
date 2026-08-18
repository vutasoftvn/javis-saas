import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/theme/app_theme.dart';
import '../../controllers/finance_controller.dart';

class RegimeTransitionWizardDialog extends StatefulWidget {
  final int currentYear;
  final String currentRegime;
  final VoidCallback onCompleted;

  const RegimeTransitionWizardDialog({
    super.key,
    required this.currentYear,
    required this.currentRegime,
    required this.onCompleted,
  });

  @override
  State<RegimeTransitionWizardDialog> createState() => _RegimeTransitionWizardDialogState();
}

class _RegimeTransitionWizardDialogState extends State<RegimeTransitionWizardDialog> {
  final FinanceController controller = Get.find<FinanceController>();

  int _currentStep = 0;
  late int _targetYear;
  String _targetRegulation = "TT199_2026";
  final TextEditingController _notesController = TextEditingController();

  bool _isLoadingPreview = false;
  Map<String, dynamic>? _previewData;
  bool _isExecuting = false;

  @override
  void initState() {
    super.initState();
    _targetYear = widget.currentYear + 1;
    _targetRegulation = widget.currentRegime == "TT58_2026" ? "TT199_2026" : "TT58_2026";
  }

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _fetchPreview() async {
    setState(() => _isLoadingPreview = true);
    final data = await controller.previewTransition(
      fromYear: widget.currentYear,
      toYear: _targetYear,
      toRegulation: _targetRegulation,
    );
    setState(() {
      _previewData = data;
      _isLoadingPreview = false;
      _currentStep = 1;
    });
  }

  Future<void> _executeTransition() async {
    setState(() => _isExecuting = true);
    final success = await controller.executeTransition(
      fromYear: widget.currentYear,
      toYear: _targetYear,
      toRegulation: _targetRegulation,
      notes: _notesController.text,
    );
    setState(() => _isExecuting = false);
    if (success) {
      widget.onCompleted();
      Get.back();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 850,
        height: 650,
        padding: const EdgeInsets.all(24),
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
                        color: AppTheme.primary.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.published_with_changes_rounded, color: AppTheme.primary, size: 24),
                    ),
                    const SizedBox(width: 12),
                    const Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Quy Trình Chuyển Đổi Chế Độ Kế Toán & Khóa Sổ Niên Độ',
                          style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          'Bảo toàn dữ liệu lịch sử và tự động sinh bút toán chuyển đổi số dư đầu kỳ.',
                          style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
                        ),
                      ],
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white70),
                  onPressed: () => Get.back(),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(color: Color(0xFF1E293B)),
            const SizedBox(height: 12),

            // Step Indicator
            _buildStepIndicator(),
            const SizedBox(height: 16),

            // Step Body
            Expanded(
              child: _currentStep == 0
                  ? _buildStep0SelectRegime()
                  : _currentStep == 1
                      ? _buildStep1ReviewMappings()
                      : _buildStep2ConfirmAndExecute(),
            ),

            const SizedBox(height: 16),
            // Actions
            _buildActionButtons(),
          ],
        ),
      ),
    );
  }

  Widget _buildStepIndicator() {
    return Row(
      children: [
        _buildStepBadge(0, '1. Chọn Chế Độ & Năm Đích'),
        const Expanded(child: Divider(color: Color(0xFF334155), thickness: 1.5)),
        _buildStepBadge(1, '2. Đối Soát Ánh Xạ Số Dư'),
        const Expanded(child: Divider(color: Color(0xFF334155), thickness: 1.5)),
        _buildStepBadge(2, '3. Khóa Sổ & Kích Hoạt'),
      ],
    );
  }

  Widget _buildStepBadge(int stepIndex, String label) {
    final isActive = _currentStep == stepIndex;
    final isDone = _currentStep > stepIndex;

    return Row(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: isActive ? AppTheme.primary : (isDone ? const Color(0xFF10B981) : const Color(0xFF1E293B)),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Row(
            children: [
              if (isDone)
                const Icon(Icons.check, size: 12, color: Colors.white)
              else
                Text(
                  '${stepIndex + 1}',
                  style: TextStyle(
                    color: isActive ? Colors.black : Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                  ),
                ),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  color: isActive ? Colors.black : Colors.white,
                  fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildStep0SelectRegime() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B).withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: Row(
            children: [
              const Icon(Icons.info_outline, color: AppTheme.primary, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Niên độ hiện tại: ${widget.currentYear} (${widget.currentRegime == "TT58_2026" ? "Thông tư 58 Tối giản" : "Thông tư 199 SME"}). Khi chuyển đổi, niên độ ${widget.currentYear} sẽ được khóa sổ Read-Only.',
                  style: const TextStyle(color: Colors.white70, fontSize: 12),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        const Text(
          'Chọn Chế độ Kế toán Đích áp dụng cho Niên độ Mới:',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
        ),
        RadioGroup<String>(
          groupValue: _targetRegulation,
          onChanged: (val) {
            if (val != null) setState(() => _targetRegulation = val);
          },
          child: Column(
            children: [
              RadioListTile<String>(
                value: "TT199_2026",
                tileColor: const Color(0xFF090D16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                title: const Text('Thông tư 199/2026/TT-BTC (Thay thế TT 133/2016)', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                subtitle: const Text('Chế độ kế toán Doanh nghiệp Nhỏ & Vừa (SME) chuẩn mực, hệ thống tài khoản kép Nợ/Có, BCTC đầy đủ B01, B02, B03, B09.', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 11)),
              ),
              const SizedBox(height: 8),
              RadioListTile<String>(
                value: "TT58_2026",
                tileColor: const Color(0xFF090D16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                title: const Text('Thông tư 58/2026/TT-BTC', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                subtitle: const Text('Chế độ kế toán Doanh nghiệp Siêu nhỏ (Micro / Startup hạt giống), tối giản dòng tiền thu chi, ghi sổ nhanh.', style: TextStyle(color: AppTheme.textMutedDark, fontSize: 11)),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            const Text('Niên độ áp dụng mới: ', style: TextStyle(color: Colors.white, fontSize: 13)),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                '$_targetYear (Bắt đầu 01/01/$_targetYear)',
                style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildStep1ReviewMappings() {
    if (_isLoadingPreview) {
      return const Center(child: CircularProgressIndicator());
    }

    final mappings = _previewData?['mappings'] as List? ?? [];
    final isBalanced = _previewData?['is_balanced'] ?? true;
    final totalDebit = _previewData?['total_debit'] ?? 0.0;
    final totalCredit = _previewData?['total_credit'] ?? 0.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Bảng Đối Soát Ánh Xạ Số Dư Đầu Kỳ:',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: (isBalanced ? const Color(0xFF10B981) : Colors.red).withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                isBalanced ? 'CÂN BẰNG NỢ / CÓ (Δ = 0)' : 'LỆCH CÂN ĐỐI',
                style: TextStyle(
                  color: isBalanced ? const Color(0xFF10B981) : Colors.red,
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Expanded(
          child: Container(
            decoration: BoxDecoration(
              color: const Color(0xFF090D16),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: ListView.separated(
              itemCount: mappings.length,
              separatorBuilder: (context, index) => const Divider(height: 1, color: Color(0xFF1E293B)),
              itemBuilder: (context, idx) {
                final m = mappings[idx];
                final side = m['entry_side'] ?? 'DEBIT';
                final isDebit = side == 'DEBIT';

                return ListTile(
                  dense: true,
                  leading: Icon(
                    isDebit ? Icons.arrow_downward : Icons.arrow_upward,
                    size: 16,
                    color: isDebit ? const Color(0xFF10B981) : AppTheme.primary,
                  ),
                  title: Text(
                    '${m['source_name']} ➔ ${m['target_account']} (${m['target_account_name']})',
                    style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                  ),
                  subtitle: Text(
                    'Phân loại: ${m['source_category']} | Ghi bên: $side',
                    style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 10),
                  ),
                  trailing: Text(
                    '${m['opening_balance'].toStringAsFixed(0)} đ',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                  ),
                );
              },
            ),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Tổng Dư Nợ: ${totalDebit.toStringAsFixed(0)} đ', style: const TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold, fontSize: 12)),
            Text('Tổng Dư Có: ${totalCredit.toStringAsFixed(0)} đ', style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold, fontSize: 12)),
          ],
        ),
      ],
    );
  }

  Widget _buildStep2ConfirmAndExecute() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B).withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.lock_outline, color: AppTheme.warning, size: 20),
                  SizedBox(width: 8),
                  Text('Xác Nhận Khóa Sổ & Kích Hoạt Niên Độ Mới', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                '1. Niên độ ${widget.currentYear} (${widget.currentRegime}) sẽ được chuyển sang trạng thái "LOCKED" (Chỉ đọc).\n'
                '2. Niên độ $_targetYear ($_targetRegulation) sẽ được kích hoạt với Bút toán Số dư Đầu kỳ tự động.\n'
                '3. Dữ liệu quá khứ của bạn không bao giờ bị ghi đè hay mất quyền truy cập.',
                style: const TextStyle(color: Colors.white70, fontSize: 12, height: 1.4),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        const Text('Ghi chú lý do chuyển đổi chế độ (Auditing):', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 12)),
        const SizedBox(height: 6),
        TextField(
          controller: _notesController,
          style: const TextStyle(color: Colors.white, fontSize: 13),
          decoration: InputDecoration(
            filled: true,
            fillColor: const Color(0xFF090D16),
            hintText: 'Ví dụ: Doanh nghiệp mở rộng quy mô từ Startup lên SME, chuyển đổi theo nghị quyết HĐQT.',
            hintStyle: const TextStyle(color: Colors.white30, fontSize: 12),
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: const BorderSide(color: Color(0xFF1E293B)),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildActionButtons() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        if (_currentStep > 0)
          OutlinedButton(
            onPressed: () => setState(() => _currentStep--),
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.white70,
              side: const BorderSide(color: Color(0xFF334155)),
            ),
            child: const Text('Quay lại'),
          )
        else
          const SizedBox.shrink(),
        Row(
          children: [
            OutlinedButton(
              onPressed: () => Get.back(),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.white70,
                side: const BorderSide(color: Color(0xFF334155)),
              ),
              child: const Text('Huỷ bỏ'),
            ),
            const SizedBox(width: 12),
            if (_currentStep == 0)
              ElevatedButton.icon(
                onPressed: _fetchPreview,
                icon: const Icon(Icons.arrow_forward, size: 16),
                label: const Text('Xem trước Ánh xạ Số dư'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: AppTheme.backgroundDarker,
                ),
              )
            else if (_currentStep == 1)
              ElevatedButton.icon(
                onPressed: () => setState(() => _currentStep = 2),
                icon: const Icon(Icons.arrow_forward, size: 16),
                label: const Text('Tiếp tục Xác nhận'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: AppTheme.backgroundDarker,
                ),
              )
            else
              ElevatedButton.icon(
                onPressed: _isExecuting ? null : _executeTransition,
                icon: _isExecuting ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.check_circle_outline, size: 16),
                label: const Text('Xác nhận & Khóa sổ Niên độ'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  foregroundColor: Colors.white,
                ),
              ),
          ],
        ),
      ],
    );
  }
}
