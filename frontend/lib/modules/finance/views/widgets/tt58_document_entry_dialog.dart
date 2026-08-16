import 'package:flutter/material.dart';

class TT58DocumentEntryDialog extends StatefulWidget {
  final Future<bool> Function({
    required String documentNo,
    required String documentType,
    required double amount,
    required String direction,
    required String description,
    String category,
  }) onSubmit;

  const TT58DocumentEntryDialog({super.key, required this.onSubmit});

  @override
  State<TT58DocumentEntryDialog> createState() => _TT58DocumentEntryDialogState();
}

enum PaymentChannel { cash, bank, other }

class _TT58DocumentEntryDialogState extends State<TT58DocumentEntryDialog> {
  final _formKey = GlobalKey<FormState>();
  final _noController = TextEditingController();
  final _amountController = TextEditingController();
  final _descController = TextEditingController();
  final _bankAccountController = TextEditingController(text: 'Vietcombank');

  PaymentChannel _channel = PaymentChannel.cash;
  String _documentType = 'PHIEU_THU';
  String _direction = 'IN';
  String _category = 'DOANH_THU';
  bool _isLoading = false;

  final List<String> _popularBanks = [
    'Vietcombank',
    'Techcombank',
    'MBBank',
    'ACB',
    'BIDV',
    'VietinBank',
    'VPBank',
    'TPBank',
  ];

  @override
  void initState() {
    super.initState();
    _applyChannelDefaults(PaymentChannel.cash);
  }

  @override
  void dispose() {
    _noController.dispose();
    _amountController.dispose();
    _descController.dispose();
    _bankAccountController.dispose();
    super.dispose();
  }

  void _applyChannelDefaults(PaymentChannel channel) {
    final suffix = DateTime.now().millisecondsSinceEpoch.toString().substring(8);
    setState(() {
      _channel = channel;
      if (channel == PaymentChannel.cash) {
        _documentType = 'PHIEU_THU';
        _direction = 'IN';
        _category = 'DOANH_THU';
        _noController.text = 'PT-$suffix';
      } else if (channel == PaymentChannel.bank) {
        _documentType = 'BAO_CO';
        _direction = 'IN';
        _category = 'DOANH_THU';
        _noController.text = 'BC-$suffix';
      } else {
        _documentType = 'HOA_DON';
        _direction = 'IN';
        _category = 'DOANH_THU';
        _noController.text = 'HD-$suffix';
      }
    });
  }

  void _onTypeChanged(String? type) {
    if (type == null) return;
    final suffix = DateTime.now().millisecondsSinceEpoch.toString().substring(8);
    setState(() {
      _documentType = type;
      switch (type) {
        case 'PHIEU_THU':
          _direction = 'IN';
          _category = 'DOANH_THU';
          _noController.text = 'PT-$suffix';
          break;
        case 'PHIEU_CHI':
          _direction = 'OUT';
          _category = 'CHI_PHI_VAN_HANH';
          _noController.text = 'PC-$suffix';
          break;
        case 'BAO_CO':
          _direction = 'IN';
          _category = 'DOANH_THU';
          _noController.text = 'BC-$suffix';
          break;
        case 'BAO_NO':
          _direction = 'OUT';
          _category = 'CHI_PHI_VAN_HANH';
          _noController.text = 'UNC-$suffix';
          break;
        case 'HOA_DON':
          _direction = 'IN';
          _category = 'DOANH_THU';
          _noController.text = 'HD-$suffix';
          break;
        case 'PHIEU_XUAT':
          _direction = 'OUT';
          _category = 'GIA_VON';
          _noController.text = 'PX-$suffix';
          break;
      }
    });
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;
    final amount = double.tryParse(_amountController.text.trim().replaceAll(',', '')) ?? 0;
    if (amount <= 0) return;

    String finalDescription = _descController.text.trim();
    if (_channel == PaymentChannel.bank && _bankAccountController.text.trim().isNotEmpty) {
      final bankInfo = '[Ngân hàng: ${_bankAccountController.text.trim()}]';
      if (!finalDescription.contains(bankInfo)) {
        finalDescription = finalDescription.isEmpty ? bankInfo : '$bankInfo $finalDescription';
      }
    }

    setState(() => _isLoading = true);
    try {
      final success = await widget.onSubmit(
        documentNo: _noController.text.trim(),
        documentType: _documentType,
        amount: amount,
        direction: _direction,
        description: finalDescription,
        category: _category,
      );
      if (success && mounted) {
        Navigator.of(context).pop();
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  List<DropdownMenuItem<String>> _getDocumentTypeItems() {
    if (_channel == PaymentChannel.cash) {
      return const [
        DropdownMenuItem(value: 'PHIEU_THU', child: Text('💵 Phiếu Thu Tiền Mặt (Mẫu 01-TT)')),
        DropdownMenuItem(value: 'PHIEU_CHI', child: Text('💵 Phiếu Chi Tiền Mặt (Mẫu 02-TT)')),
      ];
    } else if (_channel == PaymentChannel.bank) {
      return const [
        DropdownMenuItem(value: 'BAO_CO', child: Text('🏦 Giấy Báo Có (Thu tiền vào TK Bank)')),
        DropdownMenuItem(value: 'BAO_NO', child: Text('🏦 Báo Nợ / Ủy Nhiệm Chi (Chi từ TK Bank)')),
      ];
    } else {
      return const [
        DropdownMenuItem(value: 'HOA_DON', child: Text('🧾 Hóa Đơn Bán Hàng (Ghi nhận doanh thu)')),
        DropdownMenuItem(value: 'PHIEU_XUAT', child: Text('📦 Phiếu Xuất Kho (Ghi nhận giá vốn)')),
      ];
    }
  }

  Widget _buildChannelChip(PaymentChannel channel, String label, IconData icon) {
    final isSelected = _channel == channel;
    return Expanded(
      child: InkWell(
        onTap: () => _applyChannelDefaults(channel),
        borderRadius: BorderRadius.circular(8),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFF00E5FF).withValues(alpha: 0.15) : const Color(0xFF131D35),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: isSelected ? const Color(0xFF00E5FF) : const Color(0xFF1E293B),
              width: isSelected ? 1.5 : 1,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 15, color: isSelected ? const Color(0xFF00E5FF) : const Color(0xFF94A3B8)),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  color: isSelected ? const Color(0xFF00E5FF) : const Color(0xFF94A3B8),
                  fontSize: 12,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        padding: const EdgeInsets.all(24),
        constraints: const BoxConstraints(maxWidth: 500),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'LẬP & GHI SỔ CHỨNG TỪ TT58',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.8,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Color(0xFF64748B), size: 20),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Kênh thanh toán / Nguồn quỹ
              const Text('KÊNH / NGUỒN THANH TOÁN', style: TextStyle(color: Color(0xFF64748B), fontSize: 10, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
              const SizedBox(height: 8),
              Row(
                children: [
                  _buildChannelChip(PaymentChannel.cash, 'Tiền mặt', Icons.payments_outlined),
                  const SizedBox(width: 8),
                  _buildChannelChip(PaymentChannel.bank, 'Ngân hàng', Icons.account_balance_outlined),
                  const SizedBox(width: 8),
                  _buildChannelChip(PaymentChannel.other, 'Khác', Icons.receipt_long_outlined),
                ],
              ),
              const SizedBox(height: 16),

              // Loại chứng từ
              DropdownButtonFormField<String>(
                key: ValueKey(_channel),
                initialValue: _documentType,
                dropdownColor: const Color(0xFF131D35),
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  labelText: 'Loại chứng từ',
                  labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                  filled: true,
                  fillColor: const Color(0xFF131D35),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                ),
                items: _getDocumentTypeItems(),
                onChanged: _onTypeChanged,
              ),

              // Chọn ngân hàng nếu là kênh Bank
              if (_channel == PaymentChannel.bank) ...[
                const SizedBox(height: 12),
                Autocomplete<String>(
                  initialValue: TextEditingValue(text: _bankAccountController.text),
                  optionsBuilder: (textEditingValue) {
                    if (textEditingValue.text.isEmpty) return _popularBanks;
                    return _popularBanks.where((b) => b.toLowerCase().contains(textEditingValue.text.toLowerCase()));
                  },
                  onSelected: (val) => _bankAccountController.text = val,
                  fieldViewBuilder: (context, controller, focusNode, onEditingComplete) {
                    _bankAccountController.text = controller.text;
                    return TextFormField(
                      controller: controller,
                      focusNode: focusNode,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      decoration: InputDecoration(
                        labelText: 'Tài khoản / Tên ngân hàng',
                        hintText: 'Ví dụ: Vietcombank, Techcombank, ACB...',
                        hintStyle: const TextStyle(color: Color(0xFF475569), fontSize: 12),
                        labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                        filled: true,
                        fillColor: const Color(0xFF131D35),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                      ),
                      onChanged: (val) => _bankAccountController.text = val,
                    );
                  },
                ),
              ],

              const SizedBox(height: 12),
              TextFormField(
                controller: _noController,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  labelText: 'Số hiệu chứng từ',
                  labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                  filled: true,
                  fillColor: const Color(0xFF131D35),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                ),
                validator: (val) => val == null || val.isEmpty ? 'Vui lòng nhập số chứng từ' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _amountController,
                keyboardType: TextInputType.number,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  labelText: 'Số tiền (VNĐ)',
                  labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                  filled: true,
                  fillColor: const Color(0xFF131D35),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                ),
                validator: (val) => val == null || val.isEmpty ? 'Vui lòng nhập số tiền' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _descController,
                maxLines: 2,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  labelText: 'Nội dung diễn giải',
                  labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                  filled: true,
                  fillColor: const Color(0xFF131D35),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                ),
              ),
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Hủy', style: TextStyle(color: Color(0xFF94A3B8))),
                  ),
                  const SizedBox(width: 10),
                  ElevatedButton(
                    onPressed: _isLoading ? null : _handleSubmit,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    ),
                    child: _isLoading
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                        : const Text('Ghi sổ ngay', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
