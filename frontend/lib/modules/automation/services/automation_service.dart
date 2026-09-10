// COSA Automation MVP — Flutter service.
// In Startup Core, automation capabilities are disabled.
// Methods return ApiFailureDetail with ApiFailureCode.unavailable cleanly.

import 'package:http/http.dart' as http;

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/automation_models.dart';

class AutomationService {
  AutomationService({MvpRequestClient? client, http.Client? httpClient});

  static ApiResult<T> _unavailable<T>(String endpoint) => ApiFailure<T>(
        ApiFailureDetail(
          code: ApiFailureCode.unavailable,
          message: 'Automation capability disabled in Startup Core',
          endpointId: endpoint,
        ),
      );

  Future<ApiResult<List<AutomationDefinitionView>>> listDefinitions() async =>
      _unavailable('automation.definition.list');

  Future<ApiResult<AutomationDefinitionView>> getDefinition(String definitionId) async =>
      _unavailable('automation.definition.get');

  Future<ApiResult<AutomationDefinitionView>> configure({
    required String definitionId,
    required String automationKey,
    required Map<String, dynamic> configuration,
    required Map<String, dynamic> triggerContract,
  }) async =>
      _unavailable('automation.definition.configure');

  Future<ApiResult<AutomationDefinitionView>> publish(String definitionId) async =>
      _unavailable('automation.definition.publish');

  Future<ApiResult<AutomationDefinitionView>> suspend(String definitionId) async =>
      _unavailable('automation.definition.suspend');

  Future<ApiResult<AutomationInvocationView>> runNow({
    required String definitionId,
    required String clientRequestId,
  }) async =>
      _unavailable('automation.invocation.create');

  Future<ApiResult<AutomationInvocationView>> getInvocation(String invocationId) async =>
      _unavailable('automation.invocation.get');

  Future<ApiResult<AutomationInvocationView>> cancel({
    required String invocationId,
    required int expectedVersion,
  }) async =>
      _unavailable('automation.invocation.cancel');

  Future<ApiResult<AutomationRunInspector>> runInspector(String invocationId) async =>
      _unavailable('automation.run.inspector.read');

  Future<ApiResult<List<NeedsYouItem>>> needsYou() async =>
      _unavailable('automation.needs_you.list');
}
