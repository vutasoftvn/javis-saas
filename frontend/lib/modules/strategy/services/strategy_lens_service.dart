import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../../data/models/strategy_lens_model.dart';
import '../../../data/models/evidence_model.dart';
import '../../../core/network/api_client.dart';

class StrategyLensService {
  /// Lấy tổng hợp 4 Lăng kính Chiến lược theo đúng Stage của dự án
  Future<StageLensSummaryModel?> getStageLensSummary(int projectId) async {
    try {
      final response = await ApiClient.get('/strategy/lenses/summary/$projectId');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return StageLensSummaryModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[StrategyLensService] getStageLensSummary error: $e');
    }
    return null;
  }

  // --- PESTEL Radar ---
  Future<List<PestelSignalModel>> getPestelSignals(int projectId) async {
    try {
      final response = await ApiClient.get('/strategy/lenses/pestel?project_id=$projectId');
      if (response.statusCode == 200) {
        final list = jsonDecode(utf8.decode(response.bodyBytes)) as List;
        return list
            .map((item) => PestelSignalModel.fromJson(item as Map<String, dynamic>))
            .toList();
      }
    } catch (e) {
      debugPrint('[StrategyLensService] getPestelSignals error: $e');
    }
    return [];
  }

  Future<PestelSignalModel?> createPestelSignal({
    required int projectId,
    required PestelDimension dimension,
    required String signalTitle,
    required String description,
    String impactLevel = 'medium',
    String timeHorizon = 'medium_term',
  }) async {
    try {
      final response = await ApiClient.post(
        '/strategy/lenses/pestel',
        body: {
          'project_id': projectId,
          'dimension': dimension.name,
          'signal_title': signalTitle,
          'description': description,
          'impact_level': impactLevel,
          'time_horizon': timeHorizon,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return PestelSignalModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[StrategyLensService] createPestelSignal error: $e');
    }
    return null;
  }

  Future<HypothesisModel?> convertPestelToHypothesis(int signalId) async {
    try {
      final response = await ApiClient.post(
        '/strategy/lenses/pestel/$signalId/to-hypothesis',
        body: {},
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return HypothesisModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[StrategyLensService] convertPestelToHypothesis error: $e');
    }
    return null;
  }

  // --- SWOT ---
  Future<List<SwotItemModel>> getSwotItems(int projectId) async {
    try {
      final response = await ApiClient.get('/strategy/lenses/swot?project_id=$projectId');
      if (response.statusCode == 200) {
        final list = jsonDecode(utf8.decode(response.bodyBytes)) as List;
        return list
            .map((item) => SwotItemModel.fromJson(item as Map<String, dynamic>))
            .toList();
      }
    } catch (e) {
      debugPrint('[StrategyLensService] getSwotItems error: $e');
    }
    return [];
  }

  Future<SwotItemModel?> createSwotItem({
    required int projectId,
    required SwotType category,
    required String statement,
    double importance = 0.5,
    List<int> evidenceRefs = const [],
    int? pestelSignalRef,
  }) async {
    try {
      final response = await ApiClient.post(
        '/strategy/lenses/swot',
        body: {
          'project_id': projectId,
          'category': category.name.toUpperCase(),
          'statement': statement,
          'importance': importance,
          'evidence_refs': evidenceRefs,
          'pestel_signal_ref': pestelSignalRef,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return SwotItemModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[StrategyLensService] createSwotItem error: $e');
    }
    return null;
  }

  // --- TOWS ---
  Future<List<TowsOptionModel>> getTowsOptions(int projectId) async {
    try {
      final response = await ApiClient.get('/strategy/lenses/tows?project_id=$projectId');
      if (response.statusCode == 200) {
        final list = jsonDecode(utf8.decode(response.bodyBytes)) as List;
        return list
            .map((item) => TowsOptionModel.fromJson(item as Map<String, dynamic>))
            .toList();
      }
    } catch (e) {
      debugPrint('[StrategyLensService] getTowsOptions error: $e');
    }
    return [];
  }

  Future<TowsOptionModel?> createTowsOption({
    required int projectId,
    required TowsType quadrant,
    required String title,
    required String strategyDescription,
    List<int> linkedStrengthIds = const [],
    List<int> linkedWeaknessIds = const [],
    List<int> linkedOpportunityIds = const [],
    List<int> linkedThreatIds = const [],
  }) async {
    try {
      final response = await ApiClient.post(
        '/strategy/lenses/tows',
        body: {
          'project_id': projectId,
          'quadrant': quadrant.name.toUpperCase(),
          'title': title,
          'strategy_description': strategyDescription,
          'linked_strength_ids': linkedStrengthIds,
          'linked_weakness_ids': linkedWeaknessIds,
          'linked_opportunity_ids': linkedOpportunityIds,
          'linked_threat_ids': linkedThreatIds,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return TowsOptionModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[StrategyLensService] createTowsOption error: $e');
    }
    return null;
  }

  Future<TowsOptionModel?> convertTowsToTactics({
    required int optionId,
    required String tacticTitle,
    required int weekNumber,
    required String leadIndicator,
    String ownerAgent = 'Strategy Agent',
  }) async {
    try {
      final response = await ApiClient.post(
        '/strategy/lenses/tows/$optionId/generate-tactics',
        body: {
          'tactic_title': tacticTitle,
          'week_number': weekNumber,
          'lead_indicator': leadIndicator,
          'owner_agent': ownerAgent,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return TowsOptionModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[StrategyLensService] convertTowsToTactics error: $e');
    }
    return null;
  }

  // --- Balanced Scorecard (BSC) ---
  Future<List<BscGoalModel>> getBscGoals(int projectId) async {
    try {
      final response = await ApiClient.get('/strategy/lenses/bsc?project_id=$projectId');
      if (response.statusCode == 200) {
        final list = jsonDecode(utf8.decode(response.bodyBytes)) as List;
        return list
            .map((item) => BscGoalModel.fromJson(item as Map<String, dynamic>))
            .toList();
      }
    } catch (e) {
      debugPrint('[StrategyLensService] getBscGoals error: $e');
    }
    return [];
  }

  Future<BscGoalModel?> createBscGoal({
    required int projectId,
    required BscPerspective perspective,
    required String objective,
    required String kpiName,
    required String targetValue,
    String currentValue = '0',
    List<String> initiatives = const [],
  }) async {
    try {
      final response = await ApiClient.post(
        '/strategy/lenses/bsc',
        body: {
          'project_id': projectId,
          'perspective': perspective.name.toUpperCase(),
          'objective': objective,
          'kpi_name': kpiName,
          'target_value': targetValue,
          'current_value': currentValue,
          'initiatives': initiatives,
        },
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return BscGoalModel.fromJson(data);
      }
    } catch (e) {
      debugPrint('[StrategyLensService] createBscGoal error: $e');
    }
    return null;
  }
}
