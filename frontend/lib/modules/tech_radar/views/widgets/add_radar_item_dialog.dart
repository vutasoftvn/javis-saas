import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/tech_radar_controller.dart';

class AddRadarItemDialog extends StatefulWidget {
  const AddRadarItemDialog({super.key});

  static void show(BuildContext context) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.75),
      builder: (context) => const AddRadarItemDialog(),
    );
  }

  @override
  State<AddRadarItemDialog> createState() => _AddRadarItemDialogState();
}

class _AddRadarItemDialogState extends State<AddRadarItemDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _categoryController = TextEditingController();
  final _descriptionController = TextEditingController();

  String _status = 'ASSESS';
  String _maturity = 'beta';
  String _potential = 'high';
  final String _cosaUse = 'pattern';
  final String _integration = 'adapter';

  final List<String> _categories = [
    'AI & Models',
    'Orchestration & Agents',
    'Memory & State',
    'Execution & Sandbox',
    'Workflow & Automation',
    'Quality & Security',
    'Database & Storage',
    'Channels & Protocols',
  ];

  @override
  void initState() {
    super.initState();
    _categoryController.text = _categories.first;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _categoryController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<TechRadarController>();

    return Dialog(
      backgroundColor: const Color(0xFF090E1B),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: const Color(0xFF00E5FF).withValues(alpha: 0.3),
        ),
      ),
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: Container(
        width: 580,
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF00E5FF).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(
                      Icons.radar_rounded,
                      color: Color(0xFF00E5FF),
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  const Text(
                    'Thêm Công nghệ vào Radar',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.close, color: Color(0xFF64748B), size: 20),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // Form fields
              TextFormField(
                controller: _nameController,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  labelText: 'Tên công nghệ / Thư viện *',
                  labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                  hintText: 'Ví dụ: Mem0, LiteLLM, AgentSkeptic, vLLM...',
                  hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.2), fontSize: 12),
                  filled: true,
                  fillColor: const Color(0xFF131B2E),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                  ),
                ),
                validator: (val) => val == null || val.trim().isEmpty ? 'Vui lòng nhập tên' : null,
              ),
              const SizedBox(height: 12),

              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: _categoryController.text,
                      dropdownColor: const Color(0xFF131B2E),
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      decoration: InputDecoration(
                        labelText: 'Phân loại / Danh mục',
                        labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                        filled: true,
                        fillColor: const Color(0xFF131B2E),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                        ),
                      ),
                      items: _categories.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                      onChanged: (val) {
                        if (val != null) setState(() => _categoryController.text = val);
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: _status,
                      dropdownColor: const Color(0xFF131B2E),
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      decoration: InputDecoration(
                        labelText: 'Vòng Radar (Ring)',
                        labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                        filled: true,
                        fillColor: const Color(0xFF131B2E),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                        ),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'ADOPT', child: Text('ADOPT (Chính thức)')),
                        DropdownMenuItem(value: 'TRIAL', child: Text('TRIAL (Thử nghiệm)')),
                        DropdownMenuItem(value: 'ASSESS', child: Text('ASSESS (Đánh giá)')),
                        DropdownMenuItem(value: 'WATCH', child: Text('WATCH (Theo dõi)')),
                        DropdownMenuItem(value: 'REJECT', child: Text('REJECT (Loại bỏ)')),
                      ],
                      onChanged: (val) {
                        if (val != null) setState(() => _status = val);
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: _maturity,
                      dropdownColor: const Color(0xFF131B2E),
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      decoration: InputDecoration(
                        labelText: 'Độ chín muồi (Maturity)',
                        labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                        filled: true,
                        fillColor: const Color(0xFF131B2E),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                        ),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'stable', child: Text('Stable (Ổn định)')),
                        DropdownMenuItem(value: 'beta', child: Text('Beta (Đang thử nghiệm)')),
                        DropdownMenuItem(value: 'experimental', child: Text('Experimental (Thực nghiệm)')),
                      ],
                      onChanged: (val) {
                        if (val != null) setState(() => _maturity = val);
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: _potential,
                      dropdownColor: const Color(0xFF131B2E),
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      decoration: InputDecoration(
                        labelText: 'Tiềm năng (Potential)',
                        labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                        filled: true,
                        fillColor: const Color(0xFF131B2E),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                        ),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'high', child: Text('High (Rất cao)')),
                        DropdownMenuItem(value: 'medium', child: Text('Medium (Trung bình)')),
                        DropdownMenuItem(value: 'low', child: Text('Low (Thấp)')),
                      ],
                      onChanged: (val) {
                        if (val != null) setState(() => _potential = val);
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              TextFormField(
                controller: _descriptionController,
                maxLines: 3,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  labelText: 'Mô tả & Ứng dụng trong COSA OS',
                  labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                  hintText: 'Giải thích lý do lựa chọn hoặc vị trí trong kiến trúc hệ thống...',
                  hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.2), fontSize: 12),
                  filled: true,
                  fillColor: const Color(0xFF131B2E),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Actions
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Hủy', style: TextStyle(color: Color(0xFF94A3B8))),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF00E5FF),
                      foregroundColor: Colors.black,
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text(
                      'Thêm vào Radar',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                    onPressed: () {
                      if (_formKey.currentState?.validate() ?? false) {
                        controller.createItem(
                          name: _nameController.text.trim(),
                          category: _categoryController.text.trim(),
                          status: _status,
                          maturity: _maturity,
                          potential: _potential,
                          cosaUse: _cosaUse,
                          integration: _integration,
                          description: _descriptionController.text.trim(),
                        );
                        Navigator.of(context).pop();
                      }
                    },
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
