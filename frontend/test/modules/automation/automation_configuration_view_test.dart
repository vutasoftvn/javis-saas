import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/localization/app_translations.dart';
import 'package:frontend/modules/automation/controllers/automation_library_controller.dart';
import 'package:frontend/modules/automation/models/automation_models.dart';
import 'package:frontend/modules/automation/views/automation_configuration_view.dart';
import 'package:get/get.dart';

AutomationDefinitionView _def() => AutomationDefinitionView.fromJson({
      'id': '1',
      'automationKey': 'operating.weekly-review',
      'title': 'Weekly review digest',
      'purpose': 'KPI/risk/decision digest',
      'domain': 'operating',
      'lifecycleState': 'DRAFT',
      'configured': false,
      'configFields': [
        {'key': 'projectId', 'label': 'Project', 'type': 'string', 'required': true},
        {'key': 'lookbackWeeks', 'label': 'Weeks', 'type': 'number', 'required': false},
      ],
      'currentRevision': null,
      'draftRevision': null,
    });

void main() {
  setUp(() => Get.testMode = true);
  tearDown(Get.reset);

  testWidgets('renders only the blueprint typed fields and enforces required', (tester) async {
    final c = AutomationLibraryController();
    c.definitions.add(_def());
    Get.put<AutomationLibraryController>(c);

    await tester.pumpWidget(GetMaterialApp(
      translations: AppTranslations(),
      locale: const Locale('en', 'US'),
      home: const AutomationConfigurationView(automationKey: 'operating.weekly-review'),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Project'), findsOneWidget);
    expect(find.text('Weeks'), findsOneWidget);
    // no free-form prompt / model / capability field is ever rendered
    expect(find.text('Prompt'), findsNothing);
    expect(find.text('Model provider'), findsNothing);

    await tester.tap(find.text(L10nKey.automationSaveConfiguration.tr));
    await tester.pumpAndSettle();
    expect(find.text(L10nKey.automationFieldRequired.tr), findsWidgets);
  });
}
