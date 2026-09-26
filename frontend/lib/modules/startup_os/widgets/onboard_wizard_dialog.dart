import 'package:flutter/material.dart';

import '../../../core/network/api_result.dart';
import '../controllers/startup_os_controller.dart';
import '../models/onboard_dimension_fields.dart';

/// Chuyển giá trị ngữ cảnh hiện tại (JSON Company) thành chuỗi điền sẵn form.
Map<String, String> prefillFromContext(OnboardDimensionForm form, Map<String, dynamic> context) {
  Object? source = context[form.dimension];
  // Company trả `founders` (danh sách) — form chỉ điền Founder hiện tại đầu tiên.
  if (form.dimension == 'founder') {
    final founders = context['founders'];
    source = founders is List && founders.isNotEmpty ? founders.first : null;
  }
  if (source is! Map<String, dynamic>) return const {};

  final out = <String, String>{};
  for (final field in form.fields) {
    final value = source[field.key];
    if (value == null) continue;
    switch (field.kind) {
      case OnboardFieldKind.stringArray:
        if (value is List) out[field.key] = value.whereType<String>().join(', ');
      case OnboardFieldKind.valueList:
        if (value is List) {
          out[field.key] = value
              .whereType<Map<String, dynamic>>()
              .map((v) => '${v['isFireWorthy'] == true ? '!' : ''}${v['valueText'] ?? ''}')
              .where((line) => line.replaceAll('!', '').isNotEmpty)
              .join('\n');
        }
      case OnboardFieldKind.competitorList:
        if (value is List) {
          out[field.key] = value.whereType<Map<String, dynamic>>().map((c) {
            final why = c['whyWinning'];
            return why is String && why.isNotEmpty ? '${c['name']} — $why' : '${c['name']}';
          }).join('\n');
        }
      default:
        out[field.key] = value.toString();
    }
  }
  return out;
}

/// Wizard form 7 chiều (Option B — song song với /cs:setup trong chat).
///
/// Chỉ gửi chiều Founder đã sửa hoặc tick xác nhận: gửi lại chiều chỉ được điền
/// sẵn sẽ làm Company đánh dấu "vừa rà soát" dù Founder không xem.
class OnboardWizardDialog extends StatefulWidget {
  const OnboardWizardDialog({super.key, required this.controller, required this.fullSetup});

  final StartupOsController controller;
  final bool fullSetup;

  @override
  State<OnboardWizardDialog> createState() => _OnboardWizardDialogState();
}

class _OnboardWizardDialogState extends State<OnboardWizardDialog> {
  late final List<OnboardDimensionForm> _forms =
      onboardDimensionForms.where((f) => widget.fullSetup || f.isFast).toList(growable: false);
  final Map<String, Map<String, TextEditingController>> _controllers = {};
  final Map<String, Map<String, String>> _dropdowns = {};
  final Set<String> _confirmed = {};
  int _step = 0;
  bool _loadingContext = true;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    for (final form in _forms) {
      _dropdowns[form.dimension] = {};
      _controllers[form.dimension] = {
        for (final f in form.fields)
          if (!_usesDropdown(f)) f.key: TextEditingController(),
      };
    }
    _prefill();
  }

  @override
  void dispose() {
    for (final byField in _controllers.values) {
      for (final c in byField.values) {
        c.dispose();
      }
    }
    super.dispose();
  }

  bool _usesDropdown(OnboardField f) => f.options != null || f.kind == OnboardFieldKind.boolean;

  Future<void> _prefill() async {
    final result = await widget.controller.loadCompanyContext();
    if (!mounted) return;
    if (result case ApiSuccess(:final data)) {
      for (final form in _forms) {
        final values = prefillFromContext(form, data);
        for (final entry in values.entries) {
          final field = form.fields.firstWhere((f) => f.key == entry.key);
          if (_usesDropdown(field)) {
            _dropdowns[form.dimension]![entry.key] = entry.value;
          } else {
            _controllers[form.dimension]![entry.key]!.text = entry.value;
          }
        }
      }
    }
    // Lỗi đọc ngữ cảnh không chặn wizard: form trống, Founder vẫn nhập được.
    setState(() => _loadingContext = false);
  }

  Map<String, String> _rawValues(OnboardDimensionForm form) => {
        for (final f in form.fields)
          f.key: _usesDropdown(f)
              ? (_dropdowns[form.dimension]![f.key] ?? '')
              : _controllers[form.dimension]![f.key]!.text,
      };

  Future<void> _submit() async {
    final payloads = <String, Map<String, Object>>{};
    try {
      for (final form in _forms) {
        if (!_confirmed.contains(form.dimension)) continue;
        final payload = buildDimensionPayload(form, _rawValues(form));
        if (payload != null) payloads[form.dimension] = payload;
      }
    } on FormatException catch (e) {
      setState(() => _error = e.message);
      return;
    }
    if (payloads.isEmpty) {
      setState(() => _error = 'Hãy sửa hoặc tick xác nhận ít nhất một chiều có dữ liệu.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    final outcome = await widget.controller.submitOnboarding(
      fullSetup: widget.fullSetup,
      payloads: payloads,
    );
    if (!mounted) return;
    Navigator.of(context).pop(outcome);
  }

  Widget _fieldInput(OnboardDimensionForm form, OnboardField field) {
    void markEdited() => setState(() => _confirmed.add(form.dimension));

    if (_usesDropdown(field)) {
      final options = field.options ?? const {'true': 'Có', 'false': 'Không'};
      final current = _dropdowns[form.dimension]![field.key];
      return DropdownButtonFormField<String>(
        key: Key('field-${form.dimension}-${field.key}'),
        isExpanded: true,
        initialValue: options.containsKey(current) ? current : null,
        decoration: InputDecoration(labelText: field.label),
        items: [
          const DropdownMenuItem<String>(value: '', child: Text('— Bỏ qua —')),
          for (final o in options.entries) DropdownMenuItem(value: o.key, child: Text(o.value)),
        ],
        onChanged: (v) {
          _dropdowns[form.dimension]![field.key] = v ?? '';
          markEdited();
        },
      );
    }
    final multiline = field.kind == OnboardFieldKind.valueList || field.kind == OnboardFieldKind.competitorList;
    final numeric = field.kind == OnboardFieldKind.integer || field.kind == OnboardFieldKind.number;
    return TextField(
      key: Key('field-${form.dimension}-${field.key}'),
      controller: _controllers[form.dimension]![field.key],
      maxLines: multiline ? 4 : 1,
      keyboardType: numeric ? const TextInputType.numberWithOptions(decimal: true) : null,
      decoration: InputDecoration(labelText: field.label, helperText: field.hint),
      onChanged: (_) => markEdited(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.fullSetup ? 'Thiết lập hồ sơ 7 chiều' : 'Cập nhật nhanh 2 chiều Fast'),
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      content: SizedBox(
        width: 560,
        height: 520,
        child: _loadingContext
            ? const Center(child: CircularProgressIndicator())
            : Column(
                children: [
                  Expanded(
                    child: Stepper(
                      currentStep: _step,
                      onStepTapped: (i) => setState(() => _step = i),
                      onStepContinue: _step < _forms.length - 1 ? () => setState(() => _step += 1) : null,
                      onStepCancel: _step > 0 ? () => setState(() => _step -= 1) : null,
                      controlsBuilder: (context, details) => Wrap(
                        spacing: 8,
                        children: [
                          if (details.onStepContinue != null)
                            TextButton(onPressed: details.onStepContinue, child: const Text('Chiều tiếp')),
                          if (details.onStepCancel != null)
                            TextButton(onPressed: details.onStepCancel, child: const Text('Quay lại')),
                        ],
                      ),
                      steps: [
                        for (final form in _forms)
                          Step(
                            title: Text(form.title),
                            state: _confirmed.contains(form.dimension) ? StepState.complete : StepState.indexed,
                            content: Column(
                              children: [
                                for (final field in form.fields)
                                  Padding(
                                    padding: const EdgeInsets.only(bottom: 8),
                                    child: _fieldInput(form, field),
                                  ),
                                CheckboxListTile(
                                  key: Key('confirm-${form.dimension}'),
                                  contentPadding: EdgeInsets.zero,
                                  value: _confirmed.contains(form.dimension),
                                  title: const Text('Xác nhận thông tin chiều này là hiện tại'),
                                  onChanged: (v) => setState(() {
                                    if (v == true) {
                                      _confirmed.add(form.dimension);
                                    } else {
                                      _confirmed.remove(form.dimension);
                                    }
                                  }),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
                  if (_error != null)
                    Text(_error!, key: const Key('wizard-error'), style: const TextStyle(color: Colors.redAccent)),
                ],
              ),
      ),
      actions: [
        TextButton(onPressed: _submitting ? null : () => Navigator.pop(context), child: const Text('Huỷ')),
        ElevatedButton(
          key: const Key('wizard-submit'),
          onPressed: _submitting || _loadingContext ? null : _submit,
          child: _submitting
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
              : Text('Lưu ${_confirmed.length} chiều'),
        ),
      ],
    );
  }
}
