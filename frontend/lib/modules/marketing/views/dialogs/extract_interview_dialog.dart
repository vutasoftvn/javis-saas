import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class ExtractInterviewDialog extends StatefulWidget {
  final Function(String transcript, String customerName, String segment, bool saveToDb) onExtract;

  const ExtractInterviewDialog({
    super.key,
    required this.onExtract,
  });

  @override
  State<ExtractInterviewDialog> createState() => _ExtractInterviewDialogState();
}

class _ExtractInterviewDialogState extends State<ExtractInterviewDialog> {
  final _transcriptCtrl = TextEditingController();
  final _customerNameCtrl = TextEditingController(text: 'Khách hàng mục tiêu');
  final _segmentCtrl = TextEditingController(text: 'ICP Target');
  bool _saveToDb = true;

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppTheme.surfaceDark,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 600,
        padding: const EdgeInsets.all(24),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.tealAccent.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.record_voice_over_rounded, color: Colors.tealAccent, size: 22),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('AI Trích xuất Phỏng vấn Khách hàng (§35)',
                            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
                        Text('Trích xuất Pain Signals, Objections, Quotes & tự động sinh Evidence',
                            style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark)),
                      ],
                    ),
                  ),
                ],
              ),
              const Divider(height: 24),

              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Tên Khách hàng / Người đại diện', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 6),
                        TextField(
                          controller: _customerNameCtrl,
                          decoration: InputDecoration(
                            hintText: 'Anh Nam - CEO SME...',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Phân khúc (Segment)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 6),
                        TextField(
                          controller: _segmentCtrl,
                          decoration: InputDecoration(
                            hintText: 'Chủ Homestay, SME...',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              const Text('Nội dung Phỏng vấn / Ghi chú cuộc gọi (Transcript)',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
              const SizedBox(height: 6),
              TextField(
                controller: _transcriptCtrl,
                maxLines: 7,
                decoration: InputDecoration(
                  hintText: 'Dán đoạn ghi chép, hội thoại hoặc tóm tắt cuộc phỏng vấn ở đây...\nVí dụ:\n- Khách: Bên anh đang mất thời gian đăng bài Notion và ChatGPT.\n- Khách: “Nếu có tool tự động, anh sẵn sàng trả 1 triệu/tháng”.',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  contentPadding: const EdgeInsets.all(12),
                ),
              ),
              const SizedBox(height: 14),

              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Tự động lưu vào Customer Evidence Store và đối soát Giả định',
                    style: TextStyle(fontSize: 12)),
                value: _saveToDb,
                onChanged: (v) => setState(() => _saveToDb = v ?? true),
                controlAffinity: ListTileControlAffinity.leading,
              ),
              const SizedBox(height: 16),

              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Hủy'),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton.icon(
                    onPressed: () {
                      if (_transcriptCtrl.text.isEmpty) return;
                      widget.onExtract(
                        _transcriptCtrl.text,
                        _customerNameCtrl.text,
                        _segmentCtrl.text,
                        _saveToDb,
                      );
                      Navigator.of(context).pop();
                    },
                    icon: const Icon(Icons.auto_awesome_rounded, size: 16),
                    label: const Text('Phân tích & Sinh Evidence'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: Colors.white,
                    ),
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
