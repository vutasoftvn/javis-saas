import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../widgets/criticality_meter.dart';

class ExperimentDesignerDialog extends StatefulWidget {
  final List<dynamic> assumptions;
  final Function(Map<String, dynamic> experimentData) onSave;
  final Future<Map<String, dynamic>> Function(String assumptionId) onAIDesign;

  const ExperimentDesignerDialog({
    super.key,
    required this.assumptions,
    required this.onSave,
    required this.onAIDesign,
  });

  @override
  State<ExperimentDesignerDialog> createState() => _ExperimentDesignerDialogState();
}

class _ExperimentDesignerDialogState extends State<ExperimentDesignerDialog> {
  String? selectedAssumptionId;
  final _hypothesisCtrl = TextEditingController();
  final _metricCtrl = TextEditingController();
  final _thresholdCtrl = TextEditingController();
  final _sampleSizeCtrl = TextEditingController(text: '10');
  final _timeboxCtrl = TextEditingController(text: '7');
  String _selectedMethod = 'interview';
  bool _isDesigning = false;
  String? _risks;

  final List<String> _methods = [
    'interview',
    'pricing_test',
    'landing_page',
    'ab_test',
    'survey',
    'prototype',
    'campaign',
  ];

  Future<void> _triggerAIDesign() async {
    if (selectedAssumptionId == null) return;
    setState(() => _isDesigning = true);
    try {
      final res = await widget.onAIDesign(selectedAssumptionId!);
      if (mounted) {
        setState(() {
          _hypothesisCtrl.text = res['hypothesis'] ?? '';
          _metricCtrl.text = res['metric'] ?? '';
          _thresholdCtrl.text = res['success_threshold'] ?? '';
          _sampleSizeCtrl.text = (res['minimum_sample'] ?? 10).toString();
          _timeboxCtrl.text = (res['timebox_days'] ?? 7).toString();
          _selectedMethod = res['method'] ?? 'interview';
          _risks = res['risks'];
        });
      }
    } finally {
      if (mounted) setState(() => _isDesigning = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppTheme.surfaceDark,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 650,
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
                      color: AppTheme.primary.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.science_rounded, color: AppTheme.primaryLight, size: 22),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Thiết kế Thử nghiệm Nhỏ nhất (Smallest Experiment)',
                            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
                        Text('Cheap before expensive; Fast before slow; Evidence before scale (§27)',
                            style: TextStyle(fontSize: 12, color: AppTheme.textMutedDark)),
                      ],
                    ),
                  ),
                ],
              ),
              const Divider(height: 28),

              // Chọn Assumption
              const Text('1. Chọn Giả định Cần Kiểm chứng (Assumption)',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.white)),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: selectedAssumptionId,
                isExpanded: true,
                dropdownColor: AppTheme.surfaceDark,
                decoration: InputDecoration(
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                ),
                hint: const Text('Chọn một giả định để thiết kế thử nghiệm', style: TextStyle(color: AppTheme.textMutedDark)),
                items: widget.assumptions.map<DropdownMenuItem<String>>((a) {
                  final id = a['id'].toString();
                  final statement = a['statement'] ?? '';
                  final criticality = a['criticality'] ?? 9;
                  return DropdownMenuItem<String>(
                    value: id,
                    child: Row(
                      children: [
                        CriticalityMeter(score: criticality),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            statement,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                  );
                }).toList(),
                onChanged: (val) {
                  setState(() => selectedAssumptionId = val);
                  _triggerAIDesign();
                },
              ),
              const SizedBox(height: 16),

              // Button AI Auto-Design
              Align(
                alignment: Alignment.centerRight,
                child: OutlinedButton.icon(
                  onPressed: selectedAssumptionId != null && !_isDesigning ? _triggerAIDesign : null,
                  icon: _isDesigning
                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.auto_awesome_rounded, size: 16, color: AppTheme.primaryLight),
                  label: Text(_isDesigning ? 'AI đang thiết kế...' : '✨ AI Tự động Thiết kế Thử nghiệm Tối thiểu'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.primaryLight,
                    side: BorderSide(color: AppTheme.primaryLight.withValues(alpha: 0.5)),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Phương pháp và Giả thuyết
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    flex: 2,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Phương pháp (Method)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 6),
                        DropdownButtonFormField<String>(
                          initialValue: _selectedMethod,
                          dropdownColor: AppTheme.surfaceDark,
                          decoration: InputDecoration(
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          ),
                          items: _methods.map((m) => DropdownMenuItem(value: m, child: Text(m))).toList(),
                          onChanged: (v) => setState(() => _selectedMethod = v ?? 'interview'),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 3,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Chỉ số đo lường (Metric)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 6),
                        TextField(
                          controller: _metricCtrl,
                          decoration: InputDecoration(
                            hintText: 'problem_confirmation_rate, cvr...',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Hypothesis
              const Text('Giả thuyết Thử nghiệm (Hypothesis)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
              const SizedBox(height: 6),
              TextField(
                controller: _hypothesisCtrl,
                maxLines: 2,
                decoration: InputDecoration(
                  hintText: 'Ít nhất 60% đối tượng được phỏng vấn xác nhận nỗi đau...',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  contentPadding: const EdgeInsets.all(10),
                ),
              ),
              const SizedBox(height: 14),

              // Success Threshold & Sample Size & Timebox
              Row(
                children: [
                  Expanded(
                    flex: 2,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Ngưỡng Thành công', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 6),
                        TextField(
                          controller: _thresholdCtrl,
                          decoration: InputDecoration(
                            hintText: '>= 60% (6/10)',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Cỡ mẫu', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 6),
                        TextField(
                          controller: _sampleSizeCtrl,
                          keyboardType: TextInputType.number,
                          decoration: InputDecoration(
                            hintText: '10',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Thời hạn (ngày)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 6),
                        TextField(
                          controller: _timeboxCtrl,
                          keyboardType: TextInputType.number,
                          decoration: InputDecoration(
                            hintText: '7',
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),

              if (_risks != null) ...[
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.amber.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.amber.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.info_outline_rounded, size: 16, color: Colors.amberAccent),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Rủi ro: $_risks',
                          style: const TextStyle(fontSize: 11, color: Colors.amberAccent),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 24),

              // Action buttons
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
                      if (_hypothesisCtrl.text.isEmpty) return;
                      widget.onSave({
                        if (selectedAssumptionId != null) 'assumption_id': int.tryParse(selectedAssumptionId!),
                        'hypothesis': _hypothesisCtrl.text,
                        'method': _selectedMethod,
                        'metric': _metricCtrl.text.isNotEmpty ? _metricCtrl.text : 'conversion_rate',
                        'success_threshold': _thresholdCtrl.text,
                        'minimum_sample': int.tryParse(_sampleSizeCtrl.text) ?? 10,
                        'timebox_days': int.tryParse(_timeboxCtrl.text) ?? 7,
                      });
                      Navigator.of(context).pop();
                    },
                    icon: const Icon(Icons.play_arrow_rounded, size: 18),
                    label: const Text('Khởi tạo Thử nghiệm'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
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
