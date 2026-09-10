// COSA Automation MVP — Run Inspector (Task 8).
// Projects the manifest + step evidence. forbidden ≠ unavailable ≠ offline ≠
// pending ≠ empty ≠ failed — no badge fabricates a status.

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/localization/app_translations.dart';
import '../../../core/widgets/floating_app_bar.dart';
import '../controllers/automation_library_controller.dart' show AutomationLoadState;
import '../controllers/automation_run_inspector_controller.dart';

class AutomationRunInspectorView extends StatelessWidget {
  const AutomationRunInspectorView({super.key, required this.invocationId});

  final String invocationId;

  @override
  Widget build(BuildContext context) {
    final c = Get.isRegistered<AutomationRunInspectorController>()
        ? Get.find<AutomationRunInspectorController>()
        : Get.put(AutomationRunInspectorController());
    if (c.state.value == AutomationLoadState.idle) {
      c.load(invocationId);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        CosaFloatingAppBar(
          title: L10nKey.automationInspectorTitle.tr,
          subtitle: L10nKey.automationInspectorSubtitle.tr,
        ),
        Expanded(
          child: Obx(() {
            switch (c.state.value) {
              case AutomationLoadState.idle:
              case AutomationLoadState.loading:
                return const Center(child: CircularProgressIndicator());
              case AutomationLoadState.forbidden:
                return _msg(L10nKey.automationStateForbidden.tr);
              case AutomationLoadState.unavailable:
                return _msg(L10nKey.automationStateUnavailable.tr);
              case AutomationLoadState.failed:
                return _msg('${L10nKey.automationStateFailed.tr}\n${c.errorMessage.value ?? ''}');
              case AutomationLoadState.empty:
                return _msg(L10nKey.automationStateEmpty.tr);
              case AutomationLoadState.ready:
                return _body(context, c);
            }
          }),
        ),
      ],
    );
  }

  static Widget _msg(String t) =>
      Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(t, textAlign: TextAlign.center)));

  Widget _body(BuildContext context, AutomationRunInspectorController c) {
    final ins = c.inspector.value!;
    final inv = c.invocation.value;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(ins.automationKey, style: Theme.of(context).textTheme.titleMedium),
        Text('${L10nKey.automationPinnedRevision.tr}: #${ins.revisionNo} · ${ins.revisionHash}'),
        Text('${L10nKey.automationRunState.tr}: ${ins.state}'),
        Text('${L10nKey.automationSourceHealth.tr}: ${ins.sourceHealth}'),
        if (ins.failureReason != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text('${L10nKey.automationFailureReason.tr}: ${ins.failureReason}'),
          ),
        const Divider(height: 32),
        Text(L10nKey.automationTimeline.tr, style: Theme.of(context).textTheme.titleSmall),
        for (final s in ins.steps)
          ListTile(
            dense: true,
            title: Text(s.name),
            subtitle: Text([
              s.state,
              if (s.retryCount > 0) 'retry ${s.retryCount}',
              if (s.policyDecision != null) 'policy ${s.policyDecision}',
              if (s.failureReason != null) s.failureReason,
            ].join(' · ')),
            trailing: s.evidenceRef == null ? null : Text(s.evidenceRef!),
          ),
        const Divider(height: 32),
        Text(L10nKey.automationEvidence.tr, style: Theme.of(context).textTheme.titleSmall),
        for (final e in ins.evidenceRefs) Text('• $e'),
        const SizedBox(height: 24),
        if (inv != null && inv.isCancellable)
          OutlinedButton(
            onPressed: () => c.cancel(),
            child: Text(L10nKey.automationCancelRun.tr),
          ),
      ],
    );
  }
}
