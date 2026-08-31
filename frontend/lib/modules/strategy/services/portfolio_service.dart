import '../../../core/network/api_client.dart';
import '../models/strategy_list_result.dart';
import 'strategy_service_base.dart';

/// Portfolio Intelligence, SWOT, TOWS Options, Synergies & Allocations
class PortfolioService extends StrategyServiceBase {
  // ====================================================================
  // mCOSA V12 Portfolio Intelligence & Shared PESTEL (Sprint 6)
  // ====================================================================

  Future<Map<String, dynamic>> detectPortfolioNecessity() async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.get(
      '/strategy/portfolios/detect?workspace_id=$workspaceId',
    );
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolios() async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios?workspace_id=$workspaceId',
      );
      return decodeList(response, 'portfolios');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createPortfolio({
    required String name,
    String? description,
    String? strategicFocus,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios?workspace_id=$workspaceId',
      body: {
        'name': name,
        'description': ?description,
        'strategic_focus': ?strategicFocus,
      },
    );
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioProjects(String portfolioId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/projects?workspace_id=$workspaceId',
      );
      return decodeList(response, 'projects');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> addProjectToPortfolio(
    String portfolioId, {
    required String projectId,
    String strategicPriority = 'core',
    double capacityAllocation = 0.0,
    double founderAttentionHours = 0.0,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/projects?workspace_id=$workspaceId',
      body: {
        'project_id': projectId,
        'strategic_priority': strategicPriority,
        'capacity_allocation': capacityAllocation,
        'founder_attention_hours': founderAttentionHours,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> removeProjectFromPortfolio(String portfolioId, String projectId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete(
      '/strategy/portfolios/$portfolioId/projects/$projectId?workspace_id=$workspaceId',
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> getPortfolioImpactMatrix(String portfolioId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.get(
      '/strategy/portfolios/$portfolioId/impact-matrix?workspace_id=$workspaceId',
    );
    return decode(response);
  }

  // ====================================================================
  // mCOSA V12 Portfolio SWOT, Options & Synergies (Sprint 7)
  // ====================================================================

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioSwot(String portfolioId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/swot?workspace_id=$workspaceId',
      );
      return decodeList(response, 'swot_items');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> addPortfolioSwotItem(
    String portfolioId, {
    required String category,
    required String statement,
    String impact = 'medium',
    String likelihood = 'medium',
    String confidence = 'medium',
    String evidenceStatus = 'hypothesis',
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/swot?workspace_id=$workspaceId',
      body: {
        'category': category,
        'statement': statement,
        'impact': impact,
        'likelihood': likelihood,
        'confidence': confidence,
        'evidence_status': evidenceStatus,
      },
    );
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioTows(String portfolioId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/tows?workspace_id=$workspaceId',
      );
      return decodeList(response, 'tows_options');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> addPortfolioTowsOption(
    String portfolioId, {
    required String quadrant,
    required String title,
    String tradeoffs = '',
    String expectedImpact = 'medium',
    String confidence = 'medium',
    String status = 'draft',
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/tows?workspace_id=$workspaceId',
      body: {
        'quadrant': quadrant,
        'title': title,
        'tradeoffs': tradeoffs,
        'expected_impact': expectedImpact,
        'confidence': confidence,
        'status': status,
      },
    );
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioSynergies(String portfolioId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/synergies?workspace_id=$workspaceId',
      );
      return decodeList(response, 'synergies');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> addPortfolioSynergy(
    String portfolioId, {
    required String sourceProjectId,
    required String targetProjectId,
    String synergyType = 'SHARED_CAPABILITY',
    required String description,
    double? estimatedValue,
    String status = 'identified',
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/synergies?workspace_id=$workspaceId',
      body: {
        'source_project_id': sourceProjectId,
        'target_project_id': targetProjectId,
        'synergy_type': synergyType,
        'description': description,
        'estimated_value': ?estimatedValue,
        'status': status,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> deletePortfolioSynergy(String portfolioId, String synergyId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete(
      '/strategy/portfolios/$portfolioId/synergies/$synergyId?workspace_id=$workspaceId',
    );
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioDependencies(String portfolioId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/dependencies?workspace_id=$workspaceId',
      );
      return decodeList(response, 'dependencies');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> addPortfolioDependency(
    String portfolioId, {
    required String predecessorProjectId,
    required String successorProjectId,
    String dependencyType = 'BLOCKS',
    String? description,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/dependencies?workspace_id=$workspaceId',
      body: {
        'predecessor_project_id': predecessorProjectId,
        'successor_project_id': successorProjectId,
        'dependency_type': dependencyType,
        'description': ?description,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> deletePortfolioDependency(String portfolioId, String dependencyId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete(
      '/strategy/portfolios/$portfolioId/dependencies/$dependencyId?workspace_id=$workspaceId',
    );
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioOptions(String portfolioId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/strategy/portfolios/$portfolioId/options?workspace_id=$workspaceId',
      );
      return decodeList(response, 'options');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createPortfolioOption(
    String portfolioId, {
    required String title,
    String? description,
    String? towsOptionId,
    double strategicFitScore = 0.8,
    double feasibilityScore = 0.7,
    String riskLevel = 'MEDIUM',
    String status = 'draft',
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/options?workspace_id=$workspaceId',
      body: {
        'title': title,
        'description': ?description,
        'tows_option_id': ?towsOptionId,
        'strategic_fit_score': strategicFitScore,
        'feasibility_score': feasibilityScore,
        'risk_level': riskLevel,
        'status': status,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> updatePortfolioOption(
    String portfolioId,
    String optionId, {
    String? status,
    double? strategicFitScore,
    double? feasibilityScore,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/strategy/portfolios/$portfolioId/options/$optionId?workspace_id=$workspaceId',
      body: {
        'status': ?status,
        'strategic_fit_score': ?strategicFitScore,
        'feasibility_score': ?feasibilityScore,
      },
    );
    return decode(response);
  }

  // ====================================================================
  // mCOSA V12 Portfolio Cycles, WIP Limit & Capacity (Sprint 8)
  // ====================================================================

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioCycles(String portfolioId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get('/strategy/portfolios/$portfolioId/cycles?workspace_id=$workspaceId');
      return decodeList(response, 'cycles');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createPortfolioCycle(
    String portfolioId, {
    required String title,
    String? startDate,
    String? endDate,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolios/$portfolioId/cycles?workspace_id=$workspaceId',
      body: {
        'title': title,
        'start_date': ?startDate,
        'end_date': ?endDate,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> activatePortfolioCycle(String cycleId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolio-cycles/$cycleId/activate?workspace_id=$workspaceId',
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> getCycleAllocations(String cycleId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.get(
      '/strategy/portfolio-cycles/$cycleId/allocations?workspace_id=$workspaceId',
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> setCapacityAllocation(
    String cycleId, {
    required String projectId,
    required double allocatedPercentage,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolio-cycles/$cycleId/allocations/capacity?workspace_id=$workspaceId',
      body: {
        'project_id': projectId,
        'allocated_percentage': allocatedPercentage,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> setFounderAttentionAllocation(
    String cycleId, {
    required String projectId,
    required double allocatedHoursPerWeek,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/strategy/portfolio-cycles/$cycleId/allocations/founder-attention?workspace_id=$workspaceId',
      body: {
        'project_id': projectId,
        'allocated_hours_per_week': allocatedHoursPerWeek,
      },
    );
    return decode(response);
  }
}
