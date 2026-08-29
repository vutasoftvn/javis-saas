import 'package:flutter/material.dart';

class ComplianceIncidentDialog extends StatefulWidget {
  final String deploymentId;
  final Future<void> Function(String severity, String summary) onSubmit;

  const ComplianceIncidentDialog({
    super.key,
    required this.deploymentId,
    required this.onSubmit,
  });

  @override
  State<ComplianceIncidentDialog> createState() => _ComplianceIncidentDialogState();
}

class _ComplianceIncidentDialogState extends State<ComplianceIncidentDialog> {
  final _summaryController = TextEditingController();
  String _severity = 'HIGH';
  bool _submitting = false;

  @override
  void dispose() {
    _summaryController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final summary = _summaryController.text.trim();
    if (summary.isEmpty) return;
    setState(() => _submitting = true);
    try {
      await widget.onSubmit(_severity, summary);
      if (mounted) Navigator.of(context).pop(true);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        padding: const EdgeInsets.all(24),
        constraints: const BoxConstraints(maxWidth: 480),
        child: Column(

          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Báo cáo sự cố tuân thủ AI',
                  style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Color(0xFF94A3B8)),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Text('Mức độ nghiêm trọng', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              initialValue: _severity,
              dropdownColor: const Color(0xFF1E293B),

              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: InputDecoration(
                filled: true,
                fillColor: const Color(0xFF1E293B),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
              items: const [
                DropdownMenuItem(value: 'LOW', child: Text('LOW - Thấp')),
                DropdownMenuItem(value: 'MEDIUM', child: Text('MEDIUM - Trung bình')),
                DropdownMenuItem(value: 'HIGH', child: Text('HIGH - Cao (Có nguy cơ pháp lý)')),
                DropdownMenuItem(value: 'CRITICAL', child: Text('CRITICAL - Nghiêm trọng (Dừng khẩn cấp)')),
              ],
              onChanged: (val) {
                if (val != null) setState(() => _severity = val);
              },
            ),
            const SizedBox(height: 16),
            const Text('Tóm tắt sự cố', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
            const SizedBox(height: 8),
            TextField(
              controller: _summaryController,
              maxLines: 3,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: InputDecoration(
                hintText: 'Mô tả tóm tắt sự cố tuân thủ hoặc dấu hiệu vi phạm...',
                hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 13),
                filled: true,
                fillColor: const Color(0xFF1E293B),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
              ),
            ),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Huỷ', style: TextStyle(color: Color(0xFF94A3B8))),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: _submitting ? null : _submit,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFEF4444),
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  child: _submitting
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Text('Gửi báo cáo', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
