import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/skill_registry_controller.dart';

class AddSkillCandidateDialog extends StatefulWidget {
  const AddSkillCandidateDialog({super.key});

  static void show(BuildContext context) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.75),
      builder: (context) => const AddSkillCandidateDialog(),
    );
  }

  @override
  State<AddSkillCandidateDialog> createState() => _AddSkillCandidateDialogState();
}

class _AddSkillCandidateDialogState extends State<AddSkillCandidateDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _instructionsController = TextEditingController();
  final _toolsController = TextEditingController();

  String _domain = 'sales';

  final List<Map<String, String>> _domainOptions = [
    {'value': 'sales', 'label': 'Bán hàng & CRM (Sales)'},
    {'value': 'marketing', 'label': 'Marketing & Lead Gen'},
    {'value': 'finance', 'label': 'Tài chính & Kế toán (Finance TT58)'},
    {'value': 'legal', 'label': 'Pháp lý & Hợp đồng (Legal)'},
    {'value': 'operations', 'label': 'Vận hành Doanh nghiệp (Operations)'},
    {'value': 'tech', 'label': 'Kỹ thuật & Code (Tech)'},
  ];

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _instructionsController.dispose();
    _toolsController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<SkillRegistryController>();

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
        width: 780,
        constraints: const BoxConstraints(maxWidth: 820),
        padding: const EdgeInsets.all(26),
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
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
                        Icons.psychology_outlined,
                        color: Color(0xFF00E5FF),
                        size: 22,
                      ),
                    ),
                    const SizedBox(width: 12),
                    const Text(
                      'Đăng ký Kỹ năng Mới (Candidate)',
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

                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      flex: 11,
                      child: TextFormField(
                        controller: _nameController,
                        style: const TextStyle(color: Colors.white, fontSize: 13.5),
                        decoration: InputDecoration(
                          labelText: 'Tên Kỹ năng *',
                          labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12.5),
                          hintText: 'VD: qualify_enterprise_b2b_lead',
                          hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.25), fontSize: 12.5),
                          filled: true,
                          fillColor: const Color(0xFF131B2E),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                            borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                          ),
                        ),
                        validator: (val) => val == null || val.trim().isEmpty ? 'Vui lòng nhập tên' : null,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      flex: 9,
                      child: DropdownButtonFormField<String>(
                        initialValue: _domain,
                        isExpanded: true,
                        dropdownColor: const Color(0xFF131B2E),
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        decoration: InputDecoration(
                          labelText: 'Lĩnh vực (Domain)',
                          labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12.5),
                          filled: true,
                          fillColor: const Color(0xFF131B2E),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                            borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                          ),
                        ),
                        items: _domainOptions
                            .map((opt) => DropdownMenuItem(
                                  value: opt['value'],
                                  child: Text(
                                    opt['label']!,
                                    overflow: TextOverflow.ellipsis,
                                    maxLines: 1,
                                    style: const TextStyle(fontSize: 13),
                                  ),
                                ))
                            .toList(),
                        onChanged: (val) {
                          if (val != null) setState(() => _domain = val);
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                TextFormField(
                  controller: _descriptionController,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    labelText: 'Mô tả ngắn gọn mục tiêu',
                    labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12.5),
                    hintText: 'Tóm tắt kỹ năng này giúp giải quyết bài toán gì cho founder...',
                    hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.25), fontSize: 12.5),
                    filled: true,
                    fillColor: const Color(0xFF131B2E),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                    ),
                  ),
                ),
                const SizedBox(height: 14),

                TextFormField(
                  controller: _instructionsController,
                  maxLines: 6,
                  style: const TextStyle(color: Colors.white, fontSize: 12.5, fontFamily: 'monospace', height: 1.45),
                  decoration: InputDecoration(
                    labelText: 'Quy trình SOP / System Instructions *',
                    labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12.5),
                    hintText: 'Các bước thực thi chi tiết, yêu cầu ràng buộc chính xác...',
                    hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.25), fontSize: 12.5),
                    filled: true,
                    fillColor: const Color(0xFF131B2E),
                    contentPadding: const EdgeInsets.all(14),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                    ),
                  ),
                  validator: (val) => val == null || val.trim().isEmpty ? 'Vui lòng nhập SOP hướng dẫn' : null,
                ),
                const SizedBox(height: 14),

                TextFormField(
                  controller: _toolsController,
                  style: const TextStyle(color: Colors.white, fontSize: 13, fontFamily: 'monospace'),
                  decoration: InputDecoration(
                    labelText: 'Công cụ cho phép (cách nhau bởi dấu phẩy)',
                    labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12.5),
                    hintText: 'crm.upsert_lead, email.send, google_search...',
                    hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.25), fontSize: 12.5),
                    filled: true,
                    fillColor: const Color(0xFF131B2E),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                    ),
                  ),
                ),
                const SizedBox(height: 22),

                // Actions
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: const Text('Hủy', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13.5)),
                    ),
                    const SizedBox(width: 14),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF00E5FF),
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 13),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      icon: const Icon(Icons.add_task, size: 18),
                      label: const Text(
                        'Tạo Ứng viên',
                        style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
                      ),
                      onPressed: () {
                        if (_formKey.currentState?.validate() ?? false) {
                          final tools = _toolsController.text
                              .split(',')
                              .map((t) => t.trim())
                              .where((t) => t.isNotEmpty)
                              .toList();

                          controller.createCandidate(
                            name: _nameController.text.trim(),
                            domain: _domain,
                            description: _descriptionController.text.trim(),
                            instructions: _instructionsController.text.trim(),
                            toolPermissions: tools,
                            createdByAgent: 'human_founder',
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
      ),
    );
  }
}
