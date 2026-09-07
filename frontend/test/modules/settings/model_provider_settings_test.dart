import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/session/session_controller.dart';
import 'package:frontend/core/session/session_snapshot.dart';
import 'package:frontend/modules/settings/models/settings_models.dart';
import 'package:frontend/modules/settings/services/model_provider_service.dart';
import 'package:frontend/modules/settings/views/model_provider_settings_view.dart';

SessionSnapshot _snapshot(String role) => SessionSnapshot(
      userId: 'user-1',
      workspaceId: 'ws-1',
      role: role,
      runtime: SessionRuntimeInfo(
        mode: 'LOCAL_ONLY',
        modeSource: 'configured',
        presenceStatus: 'ONLINE',
        lastHeartbeatAt: null,
        asOf: DateTime.utc(2026, 9, 7),
      ),
      capabilities: const [],
    );

final _testMeta = ApiResponseMeta(
  dataState: ApiDataState.populated,
  observedAt: DateTime(2026, 9, 7),
  sources: const [],
);

class FakeModelProviderService implements ModelProviderService {
  List<ModelProviderModel> providers = const [
    ModelProviderModel(
      profileId: 'deepseek-1',
      providerType: 'deepseek_api',
      modelId: 'deepseek-chat',
      credentialConfigured: true,
      status: 'ACTIVE',
    ),
  ];

  ModelPolicyModel policy = const ModelPolicyModel(
    scope: 'WORKSPACE',
    scopeKey: 'ws-1',
    primaryProfileId: 'system-default',
    resolvedProfileId: 'system-default',
    resolvedProviderType: 'deepseek_api',
    resolvedModelId: 'deepseek-chat',
    isSystemDefault: true,
  );

  bool testConnectionCalled = false;
  bool testConnectionResultOk = true;
  Map<String, dynamic>? lastCreateProviderCall;
  Map<String, dynamic>? lastSetPolicyCall;

  @override
  Future<ApiResult<List<ModelProviderModel>>> listProviders() async {
    return ApiSuccess(data: providers, meta: _testMeta);
  }

  @override
  Future<ApiResult<ModelPolicyModel>> getPolicy(String agentProfile) async {
    return ApiSuccess(data: policy, meta: _testMeta);
  }

  @override
  Future<ApiResult<ModelProviderModel>> createProvider({
    required String providerType,
    String? profileId,
    String? modelId,
    String? apiKey,
    String? baseUrl,
    List<String>? allowedModels,
    double? budgetUsdLimit,
    int? maxConcurrency,
  }) async {
    lastCreateProviderCall = {
      'providerType': providerType,
      'profileId': profileId,
      'modelId': modelId,
      'apiKey': apiKey,
      'baseUrl': baseUrl,
    };
    final created = ModelProviderModel(
      profileId: profileId ?? 'generated-id',
      providerType: providerType,
      modelId: modelId ?? 'default-model',
      credentialConfigured: apiKey != null,
      status: 'ACTIVE',
    );
    providers = [...providers, created];
    return ApiSuccess(data: created, meta: _testMeta);
  }

  @override
  Future<ApiResult<ModelProviderTestResultModel>> testConnection(String profileId) async {
    testConnectionCalled = true;
    return ApiSuccess(
      data: ModelProviderTestResultModel(
        profileId: profileId,
        providerType: 'deepseek_api',
        modelId: 'deepseek-chat',
        ok: testConnectionResultOk,
        liveCallAttempted: true,
        detail: testConnectionResultOk ? 'live call thành công' : 'live call thất bại: TimeoutError',
      ),
      meta: _testMeta,
    );
  }

  @override
  Future<ApiResult<ModelPolicyModel>> setPolicy(
    String agentProfile, {
    required String primaryProfileId,
    List<String> fallbackProfileIds = const [],
  }) async {
    lastSetPolicyCall = {
      'agentProfile': agentProfile,
      'primaryProfileId': primaryProfileId,
      'fallbackProfileIds': fallbackProfileIds,
    };
    policy = ModelPolicyModel(
      scope: 'WORKSPACE',
      scopeKey: 'ws-1',
      primaryProfileId: primaryProfileId,
      fallbackProfileIds: fallbackProfileIds,
      resolvedProfileId: primaryProfileId,
      resolvedProviderType: 'deepseek_api',
      resolvedModelId: 'deepseek-chat',
      isSystemDefault: false,
    );
    return ApiSuccess(data: policy, meta: _testMeta);
  }
}

void main() {
  setUp(() {
    Get.reset();
  });

  Future<void> pumpView(WidgetTester tester, FakeModelProviderService service) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: ModelProviderSettingsView(service: service),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('member sees read-only provider status, no mutation controls', (tester) async {
    Get.put(SessionController()).seedForTest(_snapshot('member'));
    final service = FakeModelProviderService();

    await pumpView(tester, service);

    expect(find.textContaining('deepseek-1'), findsOneWidget);
    // Member không thấy nút "Thêm provider" hay nút test-connection.
    expect(find.text('Thêm provider'), findsNothing);
    expect(find.byKey(const ValueKey('model-provider-test-deepseek-1')), findsNothing);
  });

  testWidgets('founder can open add-provider form and submit; api key field is cleared and never redisplayed', (tester) async {
    Get.put(SessionController()).seedForTest(_snapshot('founder'));
    final service = FakeModelProviderService();

    await pumpView(tester, service);

    expect(find.text('Thêm provider'), findsOneWidget);
    await tester.tap(find.text('Thêm provider'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const ValueKey('model-provider-model-id-field')),
      'gpt-4o-mini',
    );
    await tester.enterText(
      find.byKey(const ValueKey('model-provider-api-key-field')),
      'sk-plaintext-should-never-be-shown-again',
    );

    await tester.ensureVisible(find.byKey(const ValueKey('model-provider-submit')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('model-provider-submit')));
    await tester.pumpAndSettle();

    expect(service.lastCreateProviderCall?['apiKey'], 'sk-plaintext-should-never-be-shown-again');

    // Sau khi submit, form đóng lại và API key KHÔNG xuất hiện ở bất kỳ đâu
    // trên cây widget (không bị echo lại từ response hay giữ trong field).
    expect(find.text('sk-plaintext-should-never-be-shown-again'), findsNothing);
    expect(find.byKey(const ValueKey('model-provider-api-key-field')), findsNothing);
  });

  testWidgets('provider only labeled usable after test-connection returns ok=true from server', (tester) async {
    Get.put(SessionController()).seedForTest(_snapshot('founder'));
    final service = FakeModelProviderService()..testConnectionResultOk = true;

    await pumpView(tester, service);

    // Trước khi test: dù credentialConfigured=true, KHÔNG được gắn nhãn "Khả dụng".
    expect(find.textContaining('Khả dụng'), findsNothing);
    expect(find.textContaining('Đã cấu hình (chưa kiểm tra)'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('model-provider-test-deepseek-1')));
    await tester.pumpAndSettle();

    expect(service.testConnectionCalled, isTrue);
    expect(find.textContaining('Khả dụng (đã kiểm tra)'), findsOneWidget);
  });

  testWidgets('failed test-connection does not label provider usable', (tester) async {
    Get.put(SessionController()).seedForTest(_snapshot('founder'));
    final service = FakeModelProviderService()..testConnectionResultOk = false;

    await pumpView(tester, service);

    await tester.tap(find.byKey(const ValueKey('model-provider-test-deepseek-1')));
    await tester.pumpAndSettle();

    expect(find.textContaining('Khả dụng'), findsNothing);
    expect(find.textContaining('Kiểm tra thất bại'), findsOneWidget);
  });

  testWidgets('shows resolved workspace precedence from server without client-side recomputation', (tester) async {
    Get.put(SessionController()).seedForTest(_snapshot('founder'));
    final service = FakeModelProviderService();

    await pumpView(tester, service);

    expect(find.byKey(const ValueKey('model-policy-precedence')), findsOneWidget);
    expect(find.textContaining('System default'), findsOneWidget);
  });

  testWidgets('founder-entered fallback profile IDs are threaded through to setPolicy on workspace default', (tester) async {
    // Final-review finding #5 regression: trước fix, không có ô nhập nào cho
    // `fallback_profile_ids` — founder không có cách nào trong sản phẩm thật
    // để populate fallback list dù backend/resolver hỗ trợ đầy đủ.
    Get.put(SessionController()).seedForTest(_snapshot('founder'));
    final service = FakeModelProviderService();

    await pumpView(tester, service);

    expect(find.byKey(const ValueKey('model-policy-fallback-ids-field')), findsOneWidget);

    await tester.enterText(
      find.byKey(const ValueKey('model-policy-fallback-ids-field')),
      'fallback-a, fallback-b ,fallback-c',
    );

    await tester.tap(find.text('Đặt làm workspace default'));
    await tester.pumpAndSettle();

    expect(service.lastSetPolicyCall?['agentProfile'], '_workspace_default');
    expect(service.lastSetPolicyCall?['primaryProfileId'], 'deepseek-1');
    expect(
      service.lastSetPolicyCall?['fallbackProfileIds'],
      ['fallback-a', 'fallback-b', 'fallback-c'],
    );
  });

  testWidgets('member does not see fallback profile IDs editor', (tester) async {
    Get.put(SessionController()).seedForTest(_snapshot('member'));
    final service = FakeModelProviderService();

    await pumpView(tester, service);

    expect(find.byKey(const ValueKey('model-policy-fallback-ids-field')), findsNothing);
  });
}
