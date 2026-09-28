import 'package:get/get.dart';
import 'package:frontend/core/network/api_result.dart';
import '../models/ai_initiative_portfolio.dart';
import '../services/ai_initiative_portfolio_service.dart';

enum PortfolioState {
  loading,
  ready,
  blocked,
  unavailable,
  error,
}

class AiInitiativePortfolioController extends GetxController {
  final String _explicitProjectId;
  final AiInitiativePortfolioService _service;

  AiInitiativePortfolioController({
    String? projectId,
    AiInitiativePortfolioService? service,
  })  : _explicitProjectId = projectId ?? '',
        _service = service ?? AiInitiativePortfolioService();

  String get projectId =>
      _explicitProjectId.isNotEmpty ? _explicitProjectId : Get.parameters['projectId'] ?? '';

  final isLoading = false.obs;
  final state = PortfolioState.loading.obs;
  final errorMessage = RxnString();
  final items = <AiInitiativePortfolioItem>[].obs;
  final totalCount = 0.obs;

  @override
  void onInit() {
    super.onInit();
    if (projectId.isNotEmpty) {
      loadPortfolio();
    }
  }

  Future<void> loadPortfolio() async {
    if (projectId.isEmpty) {
      state.value = PortfolioState.error;
      errorMessage.value = 'Missing projectId';
      return;
    }

    isLoading.value = true;
    errorMessage.value = null;
    state.value = PortfolioState.loading;

    try {
      final result = await _service.getPortfolio(projectId);
      if (result is ApiSuccess<AiInitiativePortfolioResponse>) {
        items.assignAll(result.data.items);
        totalCount.value = result.data.totalCount;
        state.value = PortfolioState.ready;
      } else if (result is ApiFailure<AiInitiativePortfolioResponse>) {
        state.value = PortfolioState.error;
        errorMessage.value = result.failure.message;
      }
    } catch (e) {
      state.value = PortfolioState.error;
      errorMessage.value = e.toString();
    } finally {
      isLoading.value = false;
    }
  }
}
