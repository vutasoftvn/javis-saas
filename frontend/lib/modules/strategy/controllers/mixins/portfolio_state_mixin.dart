import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../services/strategy_service.dart';

mixin PortfolioStateMixin on GetxController {
  StrategyService get strategyService;
  RxBool get isSaving;

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
      portfolios.value = await strategyService.getPortfolios();
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
      currentPortfolioProjects.value = await strategyService.getPortfolioProjects(portfolioId);
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
      Get.snackbar('Thành công', 'Đã khởi tạo Portfolio "$name"', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
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
      Get.snackbar('Thành công', 'Đã thêm dự án vào Portfolio', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> removeProjectFromPortfolio(String portfolioId, String projectId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.removeProjectFromPortfolio(portfolioId, projectId);
      await selectPortfolio(portfolioId);
      Get.snackbar('Đã xoá', 'Đã gỡ dự án khỏi Portfolio', snackPosition: SnackPosition.BOTTOM);
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
      currentPortfolioTows.value = results[0];
      currentPortfolioSynergies.value = results[1];
      currentPortfolioDependencies.value = results[2];
      currentPortfolioOptions.value = results[3];
    });
  }

  Future<void> addPortfolioTowsOption(String portfolioId, {required String quadrant, required String title}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.addPortfolioTowsOption(portfolioId, quadrant: quadrant, title: title);
      currentPortfolioTows.value = await strategyService.getPortfolioTows(portfolioId);
      Get.snackbar('Thành công', 'Đã thêm định hướng TOWS', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> addPortfolioSynergy(String portfolioId, {required String sourceProjectId, required String targetProjectId, required String synergyType, required String description, double? estimatedValue}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.addPortfolioSynergy(portfolioId, sourceProjectId: sourceProjectId, targetProjectId: targetProjectId, synergyType: synergyType, description: description, estimatedValue: estimatedValue);
      currentPortfolioSynergies.value = await strategyService.getPortfolioSynergies(portfolioId);
      Get.snackbar('Thành công', 'Đã thêm điểm cộng hưởng', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deletePortfolioSynergy(String portfolioId, String synergyId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.deletePortfolioSynergy(portfolioId, synergyId);
      currentPortfolioSynergies.value = await strategyService.getPortfolioSynergies(portfolioId);
      Get.snackbar('Thành công', 'Đã xóa quan hệ cộng hưởng', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> addPortfolioDependency(String portfolioId, {required String predecessorProjectId, required String successorProjectId, required String dependencyType, String? description}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.addPortfolioDependency(portfolioId, predecessorProjectId: predecessorProjectId, successorProjectId: successorProjectId, dependencyType: dependencyType, description: description);
      currentPortfolioDependencies.value = await strategyService.getPortfolioDependencies(portfolioId);
      Get.snackbar('Thành công', 'Đã ghi nhận phụ thuộc', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deletePortfolioDependency(String portfolioId, String dependencyId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.deletePortfolioDependency(portfolioId, dependencyId);
      currentPortfolioDependencies.value = await strategyService.getPortfolioDependencies(portfolioId);
      Get.snackbar('Thành công', 'Đã xóa quan hệ phụ thuộc', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createPortfolioOption(String portfolioId, {required String title, String? description, double strategicFitScore = 0.8, double feasibilityScore = 0.7, String riskLevel = 'MEDIUM'}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.createPortfolioOption(portfolioId, title: title, description: description, strategicFitScore: strategicFitScore, feasibilityScore: feasibilityScore, riskLevel: riskLevel);
      currentPortfolioOptions.value = await strategyService.getPortfolioOptions(portfolioId);
      Get.snackbar('Thành công', 'Đã thêm Tùy Chọn Chiến Lược', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updatePortfolioOptionStatus(String portfolioId, String optionId, String newStatus) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.updatePortfolioOption(portfolioId, optionId, status: newStatus);
      currentPortfolioOptions.value = await strategyService.getPortfolioOptions(portfolioId);
      Get.snackbar('Thành công', 'Đã cập nhật trạng thái tùy chọn', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
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
      Get.snackbar('Thành công', 'Đã cập nhật cấu hình WIP Limit', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> loadPortfolioCycles(String portfolioId) async {
    await runGuarded(() async {
      currentPortfolioCycles.value = await strategyService.getPortfolioCycles(portfolioId);
    });
  }

  Future<void> createPortfolioCycle(String portfolioId, {required String title}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.createPortfolioCycle(portfolioId, title: title);
      currentPortfolioCycles.value = await strategyService.getPortfolioCycles(portfolioId);
      Get.snackbar('Thành công', 'Đã khởi tạo chu kỳ danh mục "$title"', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> activatePortfolioCycle(String portfolioId, String cycleId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.activatePortfolioCycle(cycleId);
      currentPortfolioCycles.value = await strategyService.getPortfolioCycles(portfolioId);
      Get.snackbar('Thành công', 'Kích hoạt Chu kỳ Portfolio 12WY thành công', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> loadCeoNextActions() async {
    await runGuarded(() async {
      ceoNextActions.value = await strategyService.getCeoNextActions(limit: 5);
    });
  }

  Future<void> evaluateCeoNextActions({String? projectId, String? portfolioId}) async {
    isSaving.value = true;
    await runGuarded(() async {
      final rankings = await strategyService.evaluateCeoNextActions(projectId: projectId, portfolioId: portfolioId);
      if (rankings.isNotEmpty) {
        ceoNextActions.value = rankings.map((r) => r['candidate']).toList();
      } else {
        await loadCeoNextActions();
      }
      Get.snackbar('Thành công', 'Đã xếp hạng lại danh sách Next Best Actions', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updateNextActionStatus(String actionId, String newStatus) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.updateNextActionStatus(actionId, newStatus);
      await loadCeoNextActions();
      Get.snackbar('Thành công', 'Đã cập nhật trạng thái', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> loadModelRunsAudit() async {
    await runGuarded(() async {
      modelRunsAudit.value = await strategyService.getModelRunsAudit(limit: 20);
    });
  }

  Future<void> loadModelProfiles() async {
    await runGuarded(() async {
      modelProfiles.value = await strategyService.getModelProfiles();
    });
  }

  Future<void> updateModelProfile(String profileId, {String? displayName, double? temperature, bool? isActive}) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.updateModelProfile(profileId, displayName: displayName, temperature: temperature, isActive: isActive);
      await loadModelProfiles();
      Get.snackbar('Thành công', 'Đã cập nhật cấu hình Model Profile', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }
}
