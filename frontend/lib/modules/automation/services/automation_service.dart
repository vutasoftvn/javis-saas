// COSA Automation MVP — Flutter service (Task 7 / 8).
// Calls generated endpoints only. When a capability is disabled the
// MvpRequestClient short-circuits with ApiFailureCode.unavailable and no HTTP
// request is made — the module never hand-rolls a route string.

import 'package:http/http.dart' as http;

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/automation_models.dart';

class AutomationService {
  AutomationService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  final MvpRequestClient _client;

  Future<ApiResult<List<AutomationDefinitionView>>> listDefinitions() {
    return _client.request<List<AutomationDefinitionView>>(
      MvpEndpoint.automationDefinitionList,
      decode: (json) => (json as List<dynamic>)
          .map((e) => AutomationDefinitionView.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Future<ApiResult<AutomationDefinitionView>> getDefinition(String definitionId) {
    return _client.request<AutomationDefinitionView>(
      MvpEndpoint.automationDefinitionGet,
      pathParams: {'definitionId': definitionId},
      decode: (json) => AutomationDefinitionView.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<AutomationDefinitionView>> configure({
    required String definitionId,
    required String automationKey,
    required Map<String, dynamic> configuration,
    required Map<String, dynamic> triggerContract,
  }) {
    return _client.request<AutomationDefinitionView>(
      MvpEndpoint.automationDefinitionConfigure,
      pathParams: {'definitionId': definitionId},
      body: {
        'automationKey': automationKey,
        'configuration': configuration,
        'triggerContract': triggerContract,
      },
      decode: (json) => AutomationDefinitionView.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<AutomationDefinitionView>> publish(String definitionId) {
    return _client.request<AutomationDefinitionView>(
      MvpEndpoint.automationDefinitionPublish,
      pathParams: {'definitionId': definitionId},
      body: const {},
      decode: (json) => AutomationDefinitionView.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<AutomationDefinitionView>> suspend(String definitionId) {
    return _client.request<AutomationDefinitionView>(
      MvpEndpoint.automationDefinitionSuspend,
      pathParams: {'definitionId': definitionId},
      body: const {},
      decode: (json) => AutomationDefinitionView.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<AutomationInvocationView>> runNow({
    required String definitionId,
    required String clientRequestId,
  }) {
    return _client.request<AutomationInvocationView>(
      MvpEndpoint.automationInvocationCreate,
      pathParams: {'definitionId': definitionId},
      body: {
        'command': {'triggerKind': 'manual', 'clientRequestId': clientRequestId},
      },
      decode: (json) => AutomationInvocationView.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<AutomationInvocationView>> getInvocation(String invocationId) {
    return _client.request<AutomationInvocationView>(
      MvpEndpoint.automationInvocationGet,
      pathParams: {'invocationId': invocationId},
      decode: (json) => AutomationInvocationView.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<AutomationInvocationView>> cancel({
    required String invocationId,
    required int expectedVersion,
  }) {
    return _client.request<AutomationInvocationView>(
      MvpEndpoint.automationInvocationCancel,
      pathParams: {'invocationId': invocationId},
      body: {'expectedVersion': expectedVersion},
      decode: (json) => AutomationInvocationView.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<AutomationRunInspector>> runInspector(String invocationId) {
    return _client.request<AutomationRunInspector>(
      MvpEndpoint.automationRunInspectorRead,
      pathParams: {'invocationId': invocationId},
      decode: (json) => AutomationRunInspector.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<List<NeedsYouItem>>> needsYou() {
    return _client.request<List<NeedsYouItem>>(
      MvpEndpoint.automationNeedsYouList,
      decode: (json) => (json as List<dynamic>)
          .map((e) => NeedsYouItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
