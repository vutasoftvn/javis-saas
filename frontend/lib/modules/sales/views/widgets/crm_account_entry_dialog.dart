import 'package:flutter/material.dart';

class CrmAccountEntryDialog extends StatefulWidget {
  final Future<bool> Function({
    required String name,
    required String category,
    String? domain,
    String? industry,
    String? sizeSegment,
    String? source,
    String? lifecycleStatus,
    List<String>? tags,
    String? contactName,
    String? contactPhone,
    String? contactEmail,
  }) onSubmit;

  const CrmAccountEntryDialog({super.key, required this.onSubmit});

  @override
  State<CrmAccountEntryDialog> createState() => _CrmAccountEntryDialogState();
}

class _CrmAccountEntryDialogState extends State<CrmAccountEntryDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _domainController = TextEditingController();
  final _industryController = TextEditingController(text: 'SaaS & Công nghệ');
  final _contactNameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _customTagController = TextEditingController();

  String _category = 'CUSTOMER'; // CUSTOMER, PARTNER, VENDOR
  String _sizeSegment = 'Tiêu chuẩn';
  String _lifecycleStatus = 'ACTIVE';
  bool _isLoading = false;

  final List<String> _selectedTags = ['#VIP'];
  final List<String> _suggestedTags = [
    '#VIP',
    '#KeyAccount',
    '#HotLead',
    '#SaaS',
    '#F&B',
    '#BánLẻ',
    '#SảnXuất',
    '#ĐạiLý',
    '#Inbound',
    '#HàNội',
    '#TPHCM',
  ];

  @override
  void dispose() {
    _nameController.dispose();
    _domainController.dispose();
    _industryController.dispose();
    _contactNameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _customTagController.dispose();
    super.dispose();
  }

  void _toggleTag(String tag) {
    setState(() {
      if (_selectedTags.contains(tag)) {
        _selectedTags.remove(tag);
      } else {
        _selectedTags.add(tag);
      }
    });
  }

  void _addCustomTag() {
    final text = _customTagController.text.trim();
    if (text.isEmpty) return;
    final formatted = text.startsWith('#') ? text : '#$text';
    setState(() {
      if (!_selectedTags.contains(formatted)) {
        _selectedTags.add(formatted);
      }
      _customTagController.clear();
    });
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isLoading = true);
    try {
      final success = await widget.onSubmit(
        name: _nameController.text.trim(),
        category: _category,
        domain: _domainController.text.trim().isEmpty ? null : _domainController.text.trim(),
        industry: _industryController.text.trim().isEmpty ? null : _industryController.text.trim(),
        sizeSegment: _sizeSegment,
        source: 'Nhập trực tiếp CRM',
        lifecycleStatus: _lifecycleStatus,
        tags: _selectedTags,
        contactName: _contactNameController.text.trim().isEmpty ? null : _contactNameController.text.trim(),
        contactPhone: _phoneController.text.trim().isEmpty ? null : _phoneController.text.trim(),
        contactEmail: _emailController.text.trim().isEmpty ? null : _emailController.text.trim(),
      );
      if (success && mounted) {
        Navigator.of(context).pop();
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Widget _buildCategoryChip(String category, String label, IconData icon) {
    final isSelected = _category == category;
    return Expanded(
      child: InkWell(
        onTap: () {
          setState(() {
            _category = category;
            if (category == 'PARTNER') {
              _lifecycleStatus = 'PARTNER';
              if (!_selectedTags.contains('#ĐạiLý')) _selectedTags.add('#ĐạiLý');
            } else if (category == 'VENDOR') {
              _lifecycleStatus = 'VENDOR';
            } else {
              _lifecycleStatus = 'ACTIVE';
            }
          });
        },
        borderRadius: BorderRadius.circular(8),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 6),
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
              Flexible(
                child: Text(
                  label,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: isSelected ? const Color(0xFF00E5FF) : const Color(0xFF94A3B8),
                    fontSize: 12,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                  ),
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
        constraints: const BoxConstraints(maxWidth: 560),
        child: SingleChildScrollView(
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
                      'THÊM KHÁCH HÀNG / ĐỐI TÁC MỚI',
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

                // 1. Phân loại đối tượng
                const Text('PHÂN LOẠI ĐỐI TƯỢNG', style: TextStyle(color: Color(0xFF64748B), fontSize: 10, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _buildCategoryChip('CUSTOMER', 'Khách hàng', Icons.business_center_outlined),
                    const SizedBox(width: 8),
                    _buildCategoryChip('PARTNER', 'Đối tác / Đại lý', Icons.handshake_outlined),
                    const SizedBox(width: 8),
                    _buildCategoryChip('VENDOR', 'Nhà cung cấp', Icons.local_shipping_outlined),
                  ],
                ),
                const SizedBox(height: 16),

                // 2. Tên doanh nghiệp & Website
                TextFormField(
                  controller: _nameController,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    labelText: 'Tên Doanh nghiệp / Tổ chức / Đối tác *',
                    labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                    filled: true,
                    fillColor: const Color(0xFF131D35),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                  ),
                  validator: (val) => val == null || val.trim().isEmpty ? 'Vui lòng nhập tên đối tác/khách hàng' : null,
                ),
                const SizedBox(height: 12),

                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _domainController,
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        decoration: InputDecoration(
                          labelText: 'Website / Domain',
                          hintText: 'company.com',
                          hintStyle: const TextStyle(color: Color(0xFF475569), fontSize: 12),
                          labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                          filled: true,
                          fillColor: const Color(0xFF131D35),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: _industryController,
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        decoration: InputDecoration(
                          labelText: 'Ngành nghề / Lĩnh vực',
                          labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                          filled: true,
                          fillColor: const Color(0xFF131D35),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // 3. Phân hạng & Trạng thái
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        initialValue: _sizeSegment,
                        dropdownColor: const Color(0xFF131D35),
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        decoration: InputDecoration(
                          labelText: 'Phân hạng (Tier / Quy mô)',
                          labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                          filled: true,
                          fillColor: const Color(0xFF131D35),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                        ),
                        items: const [
                          DropdownMenuItem(value: 'VIP', child: Text('⭐ VIP (Chiến lược)')),
                          DropdownMenuItem(value: 'Key Account', child: Text('🏆 Key Account (Lớn)')),
                          DropdownMenuItem(value: 'Tiềm năng', child: Text('🔥 Tiềm năng cao')),
                          DropdownMenuItem(value: 'Tiêu chuẩn', child: Text('🔹 Tiêu chuẩn (SMB)')),
                        ],
                        onChanged: (v) => setState(() => _sizeSegment = v ?? 'Tiêu chuẩn'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        key: ValueKey(_lifecycleStatus),
                        initialValue: _lifecycleStatus,
                        dropdownColor: const Color(0xFF131D35),
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        decoration: InputDecoration(
                          labelText: 'Trạng thái vòng đời',
                          labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                          filled: true,
                          fillColor: const Color(0xFF131D35),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                        ),
                        items: const [
                          DropdownMenuItem(value: 'PROSPECT', child: Text('🌱 Tiềm năng mới')),
                          DropdownMenuItem(value: 'ONBOARDING', child: Text('⚙️ Đang triển khai')),
                          DropdownMenuItem(value: 'ACTIVE', child: Text('✅ Đang hoạt động')),
                          DropdownMenuItem(value: 'PARTNER', child: Text('🤝 Đối tác phân phối')),
                          DropdownMenuItem(value: 'VENDOR', child: Text('🚚 Nhà cung cấp')),
                          DropdownMenuItem(value: 'WATCH', child: Text('⚠️ Cần theo dõi')),
                          DropdownMenuItem(value: 'AT_RISK', child: Text('🚨 Nguy cơ rời bỏ')),
                        ],
                        onChanged: (v) => setState(() => _lifecycleStatus = v ?? 'ACTIVE'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // 4. Người liên hệ chính
                const Text('THÔNG TIN NGƯỜI ĐẠI DIỆN / LIÊN HỆ', style: TextStyle(color: Color(0xFF64748B), fontSize: 10, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _contactNameController,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    labelText: 'Họ và tên người liên hệ',
                    labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                    filled: true,
                    fillColor: const Color(0xFF131D35),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _phoneController,
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        decoration: InputDecoration(
                          labelText: 'Số điện thoại',
                          labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                          filled: true,
                          fillColor: const Color(0xFF131D35),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: _emailController,
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        decoration: InputDecoration(
                          labelText: 'Email liên hệ',
                          labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                          filled: true,
                          fillColor: const Color(0xFF131D35),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // 5. Hệ thống Tags phân loại
                const Text('TAGS PHÂN LOẠI ĐA CHIỀU', style: TextStyle(color: Color(0xFF64748B), fontSize: 10, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: _suggestedTags.map((tag) {
                    final isSel = _selectedTags.contains(tag);
                    return FilterChip(
                      selected: isSel,
                      label: Text(tag, style: TextStyle(fontSize: 11, color: isSel ? const Color(0xFF00E5FF) : const Color(0xFF94A3B8))),
                      backgroundColor: const Color(0xFF131D35),
                      selectedColor: const Color(0xFF00E5FF).withValues(alpha: 0.15),
                      checkmarkColor: const Color(0xFF00E5FF),
                      side: BorderSide(color: isSel ? const Color(0xFF00E5FF) : const Color(0xFF1E293B)),
                      onSelected: (_) => _toggleTag(tag),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _customTagController,
                        style: const TextStyle(color: Colors.white, fontSize: 12),
                        decoration: InputDecoration(
                          hintText: 'Thêm tag tùy biến (ví dụ: #ĐàNẵng, #FMCG)...',
                          hintStyle: const TextStyle(color: Color(0xFF475569), fontSize: 12),
                          filled: true,
                          fillColor: const Color(0xFF131D35),
                          isDense: true,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                        ),
                        onFieldSubmitted: (_) => _addCustomTag(),
                      ),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      onPressed: _addCustomTag,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF1E293B),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                      child: const Text('+ Thêm Tag', style: TextStyle(color: Colors.white, fontSize: 11)),
                    ),
                  ],
                ),
                const SizedBox(height: 24),

                // Buttons
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
                        backgroundColor: const Color(0xFF00E5FF),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 11),
                      ),
                      child: _isLoading
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                          : const Text('Lưu vào CRM', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
