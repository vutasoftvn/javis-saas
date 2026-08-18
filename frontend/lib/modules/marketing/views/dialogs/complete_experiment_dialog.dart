import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class CompleteExperimentDialog extends StatefulWidget {
  final Map<String, dynamic> experiment;
  final Function(String conclusion, String learning, Map<String, dynamic> observations) onComplete;

  const CompleteExperimentDialog({
    super.key,
    required this.experiment,
    required this.onComplete,
  });

  @override
  State<CompleteExperimentDialog> createState() => _CompleteExperimentDialogState();
}

class _CompleteExperimentDialogState extends State<CompleteExperimentDialog> {
  String _conclusion = 'supported';
  final _learningCtrl = TextEditingController();
  final _sampleCountCtrl = TextEditingController(text: '10');
  final _confirmedCountCtrl = TextEditingController(text: '7');

  @override
  Widget build(BuildContext context) {
    final hypothesis = widget.experiment['hypothesis'] ?? 'Thử nghiệm';

    return Dialog(
      backgroundColor: AppTheme.surfaceDark,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 540,
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
                      color: AppTheme.success.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.check_circle_rounded, color: AppTheme.success, size: 22),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Hoàn tất & Ghi nhận Bằng chứng (Evidence)',
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white)),
                        Text('Cập nhật trạng thái giả định & Vòng lặp Học hỏi (§25, §36)',
                            style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark)),
                      ],
                    ),
                  ),
                ],
              ),
              const Divider(height: 24),

              Text(
                'Thử nghiệm: $hypothesis',
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.white),
              ),
              const SizedBox(height: 16),

              // Kết luận
              const Text('1. Kết luận Thử nghiệm (Conclusion)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.white)),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: _conclusion,
                dropdownColor: AppTheme.surfaceDark,
                decoration: InputDecoration(
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
                items: const [
                  DropdownMenuItem(value: 'supported', child: Text('✅ Supported (Xác nhận giả định)')),
                  DropdownMenuItem(value: 'partially_supported', child: Text('🟡 Partially Supported (Xác nhận một phần)')),
                  DropdownMenuItem(value: 'contradicted', child: Text('❌ Contradicted (Bác bỏ giả định)')),
                  DropdownMenuItem(value: 'inconclusive', child: Text('⚪ Inconclusive (Chưa đủ kết luận)')),
                ],
                onChanged: (v) => setState(() => _conclusion = v ?? 'supported'),
              ),
              const SizedBox(height: 14),

              // Số liệu quan sát
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Cỡ mẫu thực tế', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 6),
                        TextField(
                          controller: _sampleCountCtrl,
                          keyboardType: TextInputType.number,
                          decoration: InputDecoration(
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
                        const Text('Số lượng đạt ngưỡng', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 6),
                        TextField(
                          controller: _confirmedCountCtrl,
                          keyboardType: TextInputType.number,
                          decoration: InputDecoration(
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

              // Learning summary
              const Text('2. Tóm tắt Bài học Rút ra (Learning Summary)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
              const SizedBox(height: 6),
              TextField(
                controller: _learningCtrl,
                maxLines: 3,
                decoration: InputDecoration(
                  hintText: 'Ví dụ: 8/10 founder xác nhận tính năng auto-posting là quan trọng nhất...',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  contentPadding: const EdgeInsets.all(10),
                ),
              ),
              const SizedBox(height: 20),

              // Actions
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Hủy'),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton(
                    onPressed: () {
                      if (_learningCtrl.text.isEmpty) return;
                      final sample = int.tryParse(_sampleCountCtrl.text) ?? 10;
                      final confirmed = int.tryParse(_confirmedCountCtrl.text) ?? 7;
                      widget.onComplete(
                        _conclusion,
                        _learningCtrl.text,
                        {'sample_size': sample, 'confirmed_count': confirmed},
                      );
                      Navigator.of(context).pop();
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.success,
                      foregroundColor: Colors.white,
                    ),
                    child: const Text('Ghi nhận & Cập nhật Evidence'),
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
