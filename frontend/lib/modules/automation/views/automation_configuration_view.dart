// COSA Automation MVP — guided typed configuration form (Task 7).
// Renders only the blueprint's typed fields. A user can never enter a raw
// prompt, model provider, capability set, connector secret or arbitrary target.

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/localization/app_translations.dart';
import '../controllers/automation_library_controller.dart';
import '../models/automation_models.dart';

class AutomationConfigurationView extends StatefulWidget {
  const AutomationConfigurationView({super.key, required this.automationKey});

  final String automationKey;

  @override
  State<AutomationConfigurationView> createState() => _AutomationConfigurationViewState();
}

class _AutomationConfigurationViewState extends State<AutomationConfigurationView> {
  final _form = GlobalKey<FormState>();
  final Map<String, dynamic> _values = {};
  String _triggerKind = 'manual';

  AutomationLibraryController get _c => Get.find<AutomationLibraryController>();

  AutomationDefinitionView? get _definition => _c.definitions
      .firstWhereOrNull((d) => d.automationKey == widget.automationKey);

  @override
  Widget build(BuildContext context) {
    final def = _definition;
    return Scaffold(
      appBar: AppBar(title: Text(L10nKey.automationConfigureTitle.tr)),
      body: def == null
          ? Center(child: Text(L10nKey.automationStateUnavailable.tr))
          : Form(
              key: _form,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Text(def.purpose),
                  const SizedBox(height: 16),
                  for (final field in def.configFields) _field(field),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    initialValue: _triggerKind,
                    decoration: InputDecoration(labelText: L10nKey.automationTriggerKind.tr),
                    items: const [
                      DropdownMenuItem(value: 'manual', child: Text('manual')),
                      DropdownMenuItem(value: 'schedule', child: Text('schedule')),
                    ],
                    onChanged: (v) => setState(() => _triggerKind = v ?? 'manual'),
                  ),
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: _submit,
                    child: Text(L10nKey.automationSaveConfiguration.tr),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _field(AutomationConfigField f) {
    if (f.type == 'enum') {
      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: DropdownButtonFormField<String>(
          decoration: InputDecoration(labelText: f.label, helperText: f.help),
          items: [for (final v in f.enumValues) DropdownMenuItem(value: v, child: Text(v))],
          onChanged: (v) => _values[f.key] = v,
          validator: (v) => f.required && (v == null || v.isEmpty) ? L10nKey.automationFieldRequired.tr : null,
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextFormField(
        decoration: InputDecoration(labelText: f.label, helperText: f.help),
        keyboardType: f.type == 'number' ? TextInputType.number : TextInputType.text,
        validator: (v) =>
            f.required && (v == null || v.trim().isEmpty) ? L10nKey.automationFieldRequired.tr : null,
        onChanged: (v) => _values[f.key] = f.type == 'number' ? num.tryParse(v) : v,
      ),
    );
  }

  Future<void> _submit() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    final trigger = <String, dynamic>{'kind': _triggerKind};
    final saved = await _c.configure(
      automationKey: widget.automationKey,
      configuration: Map<String, dynamic>.from(_values)..removeWhere((_, v) => v == null),
      triggerContract: trigger,
    );
    if (!mounted) return;
    if (saved != null) {
      Get.back();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_c.errorMessage.value ?? L10nKey.automationStateFailed.tr)),
      );
    }
  }
}
