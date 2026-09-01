import 'package:get/get.dart';
import '../../../../core/widgets/app_toast.dart';
import '../../services/strategy_service.dart';

mixin PortfolioStateMixin on GetxController {
  StrategyService get strategyService;
  RxBool get isSaving;
  RxnString get errorMessage;

  Future<void> runGuarded(Future<void> Function() action, {bool showSnackbar = false});

  final portfolios = <dynamic>[].obs;
  final selectedPortfolioId = RxnString();
  final currentPortfolioProjects = <dynamic>[].obs;
  final currentImpactMatrix = Rxn<Map<String, dynamic>>();
  final portfolioDetection = Rxn<Map<String, dynamic>>();
  final currentPortfolioTows = <dynamic>[].obs;
  final currentPortfolioSynergies = <dynamic>[].obs;
  final currentPortfolioDependencies = <dynamic>[].obs;
  final currentPortfolioOptions = <dynamic>[].obs;
  final currentPortfolioCycles = <dynamic>[].obs;
  final founderProfile = Rxn<Map<String, dynamic>>();
  final ceoNextActions = <dynamic>[].obs;
  final modelRunsAudit = <dynamic>[].obs;
  final modelProfiles = <dynamic>[].obs;

  Future<void> detectPortfolioNecessity() async {
    await runGuarded(() async {
      portfolioDetection.value = await strategyService.detectPortfolioNecessity();
    });
  }

  Future<void> loadPortfolios() async {
    await runGuarded(() async {
      final result = await strategyService.getPortfolios();
      portfolios.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
      if (portfolios.isNotEmpty && selectedPortfolioId.value == null) {
        await selectPortfolio(portfolios.first['id']?.toString() ?? '');
      }
    });
  }

  Future<void> selectPortfolio(String portfolioId) async {
    selectedPortfolioId.value = portfolioId;
    await Future.wait([
      loadPortfolioProjects(portfolioId),
      loadPortfolioImpactMatrix(portfolioId),
      loadPortfolioAdvancedData(portfolioId),
      loadPortfolioCycles(portfolioId),
    ]);
  }

  Future<void> loadPortfolioProjects(String portfolioId) async {
    await runGuarded(() async {
      final result = await strategyService.getPortfolioProjects(portfolioId);
      currentPortfolioProjects.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
    });
  }

  Future<void> loadPortfolioImpactMatrix(String portfolioId) async {
    await runGuarded(() async {
      currentImpactMatrix.value = await strategyService.getPortfolioImpactMatrix(portfolioId);
    });
  }

  Future<void> createPortfolio({
    required String name,
    String? description,
    String? strategicFocus,
  }) async {
    isSaving.value = true;
    await runGuarded(() async {
      final p = await strategyService.createPortfolio(name: name, description: description, strategicFocus: strategicFocus);
      await loadPortfolios();
      await selectPortfolio(p['id']?.toString() ?? '');
      AppToast.success('Đã khởi tạo Portfolio "$name"');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> addProjectToPortfolio(
    String portfolioId, {
    required String projectId,
    String strategicPriority = 'core',
    double capacityAllocation = 0.0,
    double founderAttentionHours = 0.0,
  }) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.addProjectToPortfolio(
        portfolioId,
        projectId: projectId,
        strategicPriority: strategicPriority,
        capacityAllocation: capacityAllocation,
        founderAttentionHours: founderAttentionHours,
      );
      await selectPortfolio(portfolioId);
      AppToast.success('Đã thêm dự án vào Portfolio');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> removeProjectFromPortfolio(String portfolioId, String projectId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.removeProjectFromPortfolio(portfolioId, projectId);
      await selectPortfolio(portfolioId);
      AppToast.info(
        'Đã gỡ dự án khỏi Portfolio',
        title: 'Đã xoá',
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> loadPortfolioAdvancedData(String portfolioId) async {
    await runGuarded(() async {
      final results = await Future.wait([
        strategyService.getPortfolioTows(portfolioId),
        strategyService.getPortfolioSynergies(portfolioId),
        strategyService.getPortfolioDependencies(portfolioId),
        strategyService.getPortfolioOptions(portfolioId),
      ]);
      currentPortfolioTows.value = results[0].items;
      currentPortfolioSynergies.value = results[1].items;
      currentPortfolioDependencies.value = results[2].items;
      currentPortfolioOptions.value = results[3].items;
      final failed = results.firstWhereOrNull((r) => r.errorMessage != null);
      if (failed != null) errorMessage.value = failed.errorMessage;
    });
  }

  Future<void> addPortfolioTowsOption(String portfolioId, {required String quadrant, required String title}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.addPortfolioTowsOption(portfolioId, quadrant: quadrant, title: title);
      final result = await strategyService.getPortfolioTows(portfolioId);
      currentPortfolioTows.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
      AppToast.success('Đã thêm định hướng TOWS');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> addPortfolioSynergy(String portfolioId, {required String sourceProjectId, required String targetProjectId, required String synergyType, required String description, double? estimatedValue}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.addPortfolioSynergy(portfolioId, sourceProjectId: sourceProjectId, targetProjectId: targetProjectId, synergyType: synergyType, description: description, estimatedValue: estimatedValue);
      final result = await strategyService.getPortfolioSynergies(portfolioId);
      currentPortfolioSynergies.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
      AppToast.success('Đã thêm điểm cộng hưởng');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deletePortfolioSynergy(String portfolioId, String synergyId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.deletePortfolioSynergy(portfolioId, synergyId);
      final result = await strategyService.getPortfolioSynergies(portfolioId);
      currentPortfolioSynergies.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
      AppToast.success('Đã xóa quan hệ cộng hưởng');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> addPortfolioDependency(String portfolioId, {required String predecessorProjectId, required String successorProjectId, required String dependencyType, String? description}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.addPortfolioDependency(portfolioId, predecessorProjectId: predecessorProjectId, successorProjectId: successorProjectId, dependencyType: dependencyType, description: description);
      final result = await strategyService.getPortfolioDependencies(portfolioId);
      currentPortfolioDependencies.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
      AppToast.success('Đã ghi nhận phụ thuộc');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deletePortfolioDependency(String portfolioId, String dependencyId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.deletePortfolioDependency(portfolioId, dependencyId);
      final result = await strategyService.getPortfolioDependencies(portfolioId);
      currentPortfolioDependencies.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
      AppToast.success('Đã xóa quan hệ phụ thuộc');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createPortfolioOption(String portfolioId, {required String title, String? description, double strategicFitScore = 0.8, double feasibilityScore = 0.7, String riskLevel = 'MEDIUM'}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.createPortfolioOption(portfolioId, title: title, description: description, strategicFitScore: strategicFitScore, feasibilityScore: feasibilityScore, riskLevel: riskLevel);
      final result = await strategyService.getPortfolioOptions(portfolioId);
      currentPortfolioOptions.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
      AppToast.success('Đã thêm Tùy Chọn Chiến Lược');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updatePortfolioOptionStatus(String portfolioId, String optionId, String newStatus) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.updatePortfolioOption(portfolioId, optionId, status: newStatus);
      final result = await strategyService.getPortfolioOptions(portfolioId);
      currentPortfolioOptions.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
      AppToast.success('Đã cập nhật trạng thái tùy chọn');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> loadFounderProfile() async {
    await runGuarded(() async {
      founderProfile.value = await strategyService.getFounderProfile();
    });
  }

  Future<void> updateFounderProfile({double? weeklyCapacityHours, int? maxActiveStrategicProjects}) async {
    isSaving.value = true;
    await runGuarded(() async {
      founderProfile.value = await strategyService.updateFounderProfile(weeklyCapacityHours: weeklyCapacityHours, maxActiveStrategicProjects: maxActiveStrategicProjects);
      AppToast.success('Đã cập nhật cấu hình WIP Limit');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> loadPortfolioCycles(String portfolioId) async {
    await runGuarded(() async {
      final result = await strategyService.getPortfolioCycles(portfolioId);
      currentPortfolioCycles.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
    });
  }

  Future<void> createPortfolioCycle(String portfolioId, {required String title}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.createPortfolioCycle(portfolioId, title: title);
      final result = await strategyService.getPortfolioCycles(portfolioId);
      currentPortfolioCycles.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
      AppToast.success('Đã khởi tạo chu kỳ danh mục "$title"');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> activatePortfolioCycle(String portfolioId, String cycleId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.activatePortfolioCycle(cycleId);
      final result = await strategyService.getPortfolioCycles(portfolioId);
      currentPortfolioCycles.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
      AppToast.success('Kích hoạt Chu kỳ Portfolio 12WY thành công');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> loadCeoNextActions() async {
    await runGuarded(() async {
      final result = await strategyService.getCeoNextActions(limit: 5);
      ceoNextActions.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
    });
  }

  Future<void> evaluateCeoNextActions({String? projectId, String? portfolioId}) async {
    isSaving.value = true;
    await runGuarded(() async {
      final result = await strategyService.evaluateCeoNextActions(projectId: projectId, portfolioId: portfolioId);
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
      if (result.items.isNotEmpty) {
        ceoNextActions.value = result.items.map((r) => r['candidate']).toList();
      } else {
        await loadCeoNextActions();
      }
      AppToast.success('Đã xếp hạng lại danh sách Next Best Actions');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updateNextActionStatus(String actionId, String newStatus) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.updateNextActionStatus(actionId, newStatus);
      await loadCeoNextActions();
      AppToast.success('Đã cập nhật trạng thái');
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> loadModelRunsAudit() async {
    await runGuarded(() async {
      final result = await strategyService.getModelRunsAudit(limit: 20);
      modelRunsAudit.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
    });
  }

  Future<void> loadModelProfiles() async {
    await runGuarded(() async {
      final result = await strategyService.getModelProfiles();
      modelProfiles.value = result.items;
      if (result.errorMessage != null) errorMessage.value = result.errorMessage;
    });
  }

  Future<void> updateModelProfile(String profileId, {String? displayName, double? temperature, bool? isActive}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.updateModelProfile(profileId, displayName: displayName, temperature: temperature, isActive: isActive);
      await loadModelProfiles();
      AppToast.success('Đã cập nhật cấu hình Model Profile');
    }, showSnackbar: true);
    isSaving.value = false;
  }
}
