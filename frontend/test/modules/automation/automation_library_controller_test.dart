import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/automation/controllers/automation_library_controller.dart';
import 'package:frontend/modules/automation/models/automation_models.dart';
import 'package:frontend/modules/automation/services/automation_service.dart';
import 'package:get/get.dart';

class _FakeService implements AutomationService {
  _FakeService(this._list);
  final ApiResult<List<AutomationDefinitionView>> _list;

  @override
  Future<ApiResult<List<AutomationDefinitionView>>> listDefinitions() async => _list;

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

ApiSuccess<T> _ok<T>(T data) => ApiSuccess<T>(
      data: data,
      meta: ApiResponseMeta(dataState: ApiDataState.populated, observedAt: DateTime(2026)),
    );

ApiFailure<T> _fail<T>(ApiFailureCode code) =>
    ApiFailure<T>(ApiFailureDetail(code: code, message: 'x'));

AutomationDefinitionView _def(String key, String lifecycle) => AutomationDefinitionView.fromJson({
      'id': '1',
      'automationKey': key,
      'title': key,
      'purpose': '',
      'domain': 'operating',
      'lifecycleState': lifecycle,
      'configured': lifecycle != 'DRAFT',
      'configFields': const [],
      'currentRevision': null,
      'draftRevision': null,
    });

void main() {
  setUp(() => Get.testMode = true);
  tearDown(Get.reset);

  test('ready state lists definitions', () async {
    final c = AutomationLibraryController(
      service: _FakeService(_ok<List<AutomationDefinitionView>>([_def('operating.weekly-review', 'PUBLISHED')])),
    );
    await c.load();
    expect(c.state.value, AutomationLoadState.ready);
    expect(c.definitions, hasLength(1));
  });

  test('empty result is a distinct state', () async {
    final c = AutomationLibraryController(service: _FakeService(_ok<List<AutomationDefinitionView>>([])));
    await c.load();
    expect(c.state.value, AutomationLoadState.empty);
  });

  test('forbidden, unavailable and failed are three distinct states', () async {
    for (final entry in {
      ApiFailureCode.forbidden: AutomationLoadState.forbidden,
      ApiFailureCode.unavailable: AutomationLoadState.unavailable,
      ApiFailureCode.unknown: AutomationLoadState.failed,
    }.entries) {
      final c = AutomationLibraryController(
        service: _FakeService(_fail<List<AutomationDefinitionView>>(entry.key)),
      );
      await c.load();
      expect(c.state.value, entry.value, reason: '${entry.key}');
    }
  });
}
