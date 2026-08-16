import 'package:flutter/material.dart';

class AiOutreachComposerDialog extends StatefulWidget {
  final String leadId;
  final String leadName;
  final String company;
  final Future<Map<String, dynamic>?> Function({
    required String leadId,
    String channel,
    String tone,
    String? focusPainPoint,
  }) onGenerateOutreach;

  const AiOutreachComposerDialog({
    super.key,
    required this.leadId,
    required this.leadName,
    required this.company,
    required this.onGenerateOutreach,
  });

  @override
  State<AiOutreachComposerDialog> createState() => _AiOutreachComposerDialogState();
}

class _AiOutreachComposerDialogState extends State<AiOutreachComposerDialog> {
  String _selectedChannel = 'email';
  String _selectedTone = 'professional';
  final TextEditingController _painPointController = TextEditingController(
    text: 'Chi phí vận hành và quy trình thủ công cần tự động hóa',
  );

  bool _isGenerating = false;
  Map<String, dynamic>? _generatedDraft;

  Future<void> _handleGenerate() async {
    setState(() {
      _isGenerating = true;
    });

    try {
      final res = await widget.onGenerateOutreach(
        leadId: widget.leadId,
        channel: _selectedChannel,
        tone: _selectedTone,
        focusPainPoint: _painPointController.text.trim(),
      );
      setState(() {
        _generatedDraft = res;
      });
    } finally {
      setState(() {
        _isGenerating = false;
      });
    }
  }

  @override
  void dispose() {
    _painPointController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: const BorderSide(color: Color(0xFF00E5FF), width: 1.2),
      ),
      child: Container(
        width: 540,
        padding: const EdgeInsets.all(22),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF00E5FF).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.auto_awesome_rounded,
                    color: Color(0xFF00E5FF),
                    size: 20,
                  ),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'AI OUTREACH COMPOSER',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.0,
                      ),
                    ),
                    Text(
                      'Tiếp cận: ${widget.leadName} (${widget.company})',
                      style: const TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close, color: Color(0xFF64748B), size: 18),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const Divider(color: Color(0xFF1E293B), height: 24),
            // Options Row
            Row(
              children: [
                // Tone Selector
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Tone giọng', style: TextStyle(color: Color(0xFF64748B), fontSize: 11, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 6),
                      DropdownButtonFormField<String>(
                        initialValue: _selectedTone,
                        dropdownColor: const Color(0xFF131D35),
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        decoration: InputDecoration(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          filled: true,
                          fillColor: const Color(0xFF131D35),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                        ),
                        items: const [
                          DropdownMenuItem(value: 'professional', child: Text('Chuyên nghiệp & B2B')),
                          DropdownMenuItem(value: 'friendly', child: Text('Thân thiện & Gợi mở')),
                          DropdownMenuItem(value: 'urgent', child: Text('Khẩn trương & Trực diện')),
                        ],
                        onChanged: (v) => setState(() => _selectedTone = v ?? 'professional'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 14),
                // Channel Selector
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Kênh tiếp cận', style: TextStyle(color: Color(0xFF64748B), fontSize: 11, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 6),
                      DropdownButtonFormField<String>(
                        initialValue: _selectedChannel,
                        dropdownColor: const Color(0xFF131D35),
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        decoration: InputDecoration(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          filled: true,
                          fillColor: const Color(0xFF131D35),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
                        ),
                        items: const [
                          DropdownMenuItem(value: 'email', child: Text('Email (Resend/Gmail)')),
                          DropdownMenuItem(value: 'zalo', child: Text('Zalo ZNS / Message')),
                        ],
                        onChanged: (v) => setState(() => _selectedChannel = v ?? 'email'),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            // Pain Point Input
            const Text('Trọng tâm nhu cầu / Pain point', style: TextStyle(color: Color(0xFF64748B), fontSize: 11, fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            TextField(
              controller: _painPointController,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                hintText: 'Nhập pain point của khách hàng...',
                hintStyle: const TextStyle(color: Color(0xFF475569), fontSize: 12),
                filled: true,
                fillColor: const Color(0xFF131D35),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1E293B))),
              ),
            ),
            const SizedBox(height: 16),
            // Draft Output Preview if generated
            if (_generatedDraft != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF090D16),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.check_circle_rounded, size: 14, color: Color(0xFF10B981)),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            'Tiêu đề: ${_generatedDraft!['subject'] ?? ''}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _generatedDraft!['body_preview'] ?? '',
                      maxLines: 4,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11, height: 1.4),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],
            // Action Buttons
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Đóng', style: TextStyle(color: Color(0xFF94A3B8))),
                ),
                const SizedBox(width: 10),
                ElevatedButton.icon(
                  onPressed: _isGenerating ? null : _handleGenerate,
                  icon: _isGenerating
                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                      : const Icon(Icons.auto_awesome, size: 16, color: Colors.black),
                  label: Text(
                    _generatedDraft == null ? 'Soạn thảo & Gửi duyệt' : 'Tạo lại bản nháp',
                    style: const TextStyle(color: Colors.black, fontWeight: FontWeight.w700),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF00E5FF),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
