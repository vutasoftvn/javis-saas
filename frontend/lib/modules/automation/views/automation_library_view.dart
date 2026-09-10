// COSA Automation MVP — Automation Library (Task 7).

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/localization/app_translations.dart';
import '../../../core/widgets/floating_app_bar.dart';
import '../controllers/automation_library_controller.dart';
import '../models/automation_models.dart';
import 'automation_configuration_view.dart';

class AutomationLibraryView extends StatelessWidget {
  const AutomationLibraryView({super.key});

  @override
  Widget build(BuildContext context) {
    final c = Get.isRegistered<AutomationLibraryController>()
        ? Get.find<AutomationLibraryController>()
        : Get.put(AutomationLibraryController());
    if (c.state.value == AutomationLoadState.idle) {
      c.load();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        CosaFloatingAppBar(
          title: L10nKey.automationLibraryTitle.tr,
          subtitle: L10nKey.automationLibrarySubtitle.tr,
        ),
        Expanded(
          child: Obx(() {
            switch (c.state.value) {
              case AutomationLoadState.idle:
              case AutomationLoadState.loading:
                return const Center(child: CircularProgressIndicator());
              case AutomationLoadState.forbidden:
                return _Message(L10nKey.automationStateForbidden.tr);
              case AutomationLoadState.unavailable:
                return _Message(L10nKey.automationStateUnavailable.tr);
              case AutomationLoadState.failed:
                return _Message('${L10nKey.automationStateFailed.tr}\n${c.errorMessage.value ?? ''}');
              case AutomationLoadState.empty:
                return _Message(L10nKey.automationStateEmpty.tr);
              case AutomationLoadState.ready:
                return ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    for (final d in c.definitions) _DefinitionCard(controller: c, definition: d),
                  ],
                );
            }
          }),
        ),
      ],
    );
  }
}

class _Message extends StatelessWidget {
  const _Message(this.text);
  final String text;
  @override
  Widget build(BuildContext context) =>
      Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(text, textAlign: TextAlign.center)));
}

class _DefinitionCard extends StatelessWidget {
  const _DefinitionCard({required this.controller, required this.definition});

  final AutomationLibraryController controller;
  final AutomationDefinitionView definition;

  String get _statusLabel => switch (definition.cardStatus) {
        AutomationCardStatus.ready => L10nKey.automationCardReady.tr,
        AutomationCardStatus.setupRequired => L10nKey.automationCardSetupRequired.tr,
        AutomationCardStatus.suspended => L10nKey.automationCardSuspended.tr,
        AutomationCardStatus.unavailable => L10nKey.automationCardUnavailable.tr,
        AutomationCardStatus.forbidden => L10nKey.automationCardForbidden.tr,
      };

  @override
  Widget build(BuildContext context) {
    final busy = controller.busyKey.value == definition.id;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(child: Text(definition.title, style: Theme.of(context).textTheme.titleMedium)),
                Chip(label: Text(_statusLabel)),
              ],
            ),
            const SizedBox(height: 4),
            Text(definition.purpose),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: [
                OutlinedButton(
                  onPressed: busy
                      ? null
                      : () => Get.to(() => AutomationConfigurationView(automationKey: definition.automationKey)),
                  child: Text(L10nKey.automationConfigure.tr),
                ),
                if (definition.cardStatus == AutomationCardStatus.ready)
                  FilledButton(
                    onPressed: busy ? null : () => controller.runNow(definition.id!),
                    child: Text(L10nKey.automationRunNow.tr),
                  ),
                if (definition.cardStatus == AutomationCardStatus.ready && definition.id != null)
                  TextButton(
                    onPressed: busy ? null : () => controller.suspend(definition.id!),
                    child: Text(L10nKey.automationSuspend.tr),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
