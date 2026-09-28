import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/projects/controllers/ai_initiative_portfolio_controller.dart';
import 'package:frontend/modules/projects/models/ai_initiative_portfolio.dart';
import 'package:frontend/modules/projects/services/ai_initiative_portfolio_service.dart';

class MockPortfolioService extends AiInitiativePortfolioService {
  final ApiResult<AiInitiativePortfolioResponse> result;

  MockPortfolioService(this.result);

  @override
  Future<ApiResult<AiInitiativePortfolioResponse>> getPortfolio(String projectId) async {
    return result;
  }
}

void main() {
  test('controller loads portfolio successfully into ready state', () async {
    final mockResponse = AiInitiativePortfolioResponse(
      projectId: 'proj_1',
      workspaceId: 'ws_1',
      items: [
        AiInitiativePortfolioItem(
          initiativeId: 'init_1',
          initiativeRevision: 1,
          title: 'Test Initiative',
          lifecycleState: 'PILOT',
          riskTier: 'LOW',
          autonomyTier: 'A1',
          businessOwnerMemberId: 'mem_1',
          baselineMetricValue: null,
          targetMetricValue: '80%',
          latestOutcomeValue: null,
          costBudgetStatus: 'OK',
          adoptionStatus: 'NO_DATA',
          qualityStatus: 'PASSED',
          dataReadinessStatus: 'LEVEL_1',
          nextRequiredGate: 'VALIDATION_BASELINE_AND_METRICS',
          blockingReasons: [],
          authorizedActions: [],
        ),
      ],
      totalCount: 1,
    );

    final service = MockPortfolioService(
      ApiSuccess(
        data: mockResponse,
        meta: ApiResponseMeta(
          dataState: ApiDataState.populated,
          observedAt: DateTime.now(),
        ),
      ),
    );
    final controller = AiInitiativePortfolioController(projectId: 'proj_1', service: service);

    await controller.loadPortfolio();

    expect(controller.isLoading.value, false);
    expect(controller.state.value, PortfolioState.ready);
    expect(controller.items.length, 1);
    expect(controller.items.first.title, 'Test Initiative');
  });

  test('controller sets error state on API failure', () async {
    final service = MockPortfolioService(
      const ApiFailure(
        ApiFailureDetail(
          code: ApiFailureCode.unknown,
          message: 'Network error',
          statusCode: 500,
        ),
      ),
    );
    final controller = AiInitiativePortfolioController(projectId: 'proj_1', service: service);

    await controller.loadPortfolio();

    expect(controller.isLoading.value, false);
    expect(controller.state.value, PortfolioState.error);
    expect(controller.errorMessage.value, 'Network error');
  });
}
