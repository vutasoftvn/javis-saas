import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/models/validation_models.dart';
import '../../../data/services/validation_service.dart';

class ValidationInterviewMessage {
  final String id;
  final String sender; // 'user' or 'ai'
  final String text;
  final DateTime timestamp;
  final ClusterSummaryModel? clusterSummary;
  final List<StructuredClaimModel> claims;

  ValidationInterviewMessage({
    required this.id,
    required this.sender,
    required this.text,
    required this.timestamp,
    this.clusterSummary,
    this.claims = const [],
  });
}

class ValidationInterviewController extends GetxController {
  final currentProjectId = RxnInt();
  final activeSession = Rxn<ValidationSessionModel>();
  final currentTopic = 'CUSTOMER'.obs;
  final isLoading = false.obs;
  
  final messages = <ValidationInterviewMessage>[].obs;
  final claims = <StructuredClaimModel>[].obs;
  final stateVector = Rxn<StateVectorModel>();

  Future<void> startOrResumeValidation(int projectId, {String initialTopic = 'CUSTOMER'}) async {
    currentProjectId.value = projectId;
    isLoading.value = true;

    try {
      final session = await ValidationService.startSession(projectId, initialTopic: initialTopic);
      if (session != null) {
        activeSession.value = session;
        currentTopic.value = session.currentTopic;
      }

      await refreshClaims();
      await refreshStateVector();

      if (messages.isEmpty) {
        messages.add(
          ValidationInterviewMessage(
            id: DateTime.now().millisecondsSinceEpoch.toString(),
            sender: 'ai',
            text: 'Chào anh/chị. Tôi là COSA Project Validation Interviewer. '
                'Chúng ta sẽ cùng rà soát các giả định và làm rõ dự án bắt đầu từ nhóm [${currentTopic.value}]. '
                'Anh/chị có thể chia sẻ tự nhiên qua chat, tôi sẽ tự động trích xuất các dữ kiện.',
            timestamp: DateTime.now(),
          ),
        );
      }
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> sendUserMessage(String userText) async {
    if (userText.trim().isEmpty || currentProjectId.value == null) return;
    final pId = currentProjectId.value!;

    final userMsg = ValidationInterviewMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      sender: 'user',
      text: userText,
      timestamp: DateTime.now(),
    );
    messages.add(userMsg);
    isLoading.value = true;

    try {
      final res = await ValidationService.sendValidationChat(
        pId,
        userText,
        currentTopic: currentTopic.value,
      );

      if (res != null) {
        if (res.suggestedNextTopic != null) {
          currentTopic.value = res.suggestedNextTopic!;
        }

        await refreshClaims();
        await refreshStateVector();

        final newlyExtractedClaims = claims
            .where((c) => res.extractedClaims.any((ec) => ec['id'] == c.id))
            .toList();

        messages.add(
          ValidationInterviewMessage(
            id: DateTime.now().millisecondsSinceEpoch.toString(),
            sender: 'ai',
            text: res.aiReply,
            timestamp: DateTime.now(),
            clusterSummary: res.clusterSummary,
            claims: newlyExtractedClaims,
          ),
        );
      }
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> confirmClaim(StructuredClaimModel claim) async {
    if (currentProjectId.value == null) return;
    final updated = await ValidationService.confirmClaim(currentProjectId.value!, claim.id);
    if (updated != null) {
      final index = claims.indexWhere((c) => c.id == claim.id);
      if (index != -1) {
        claims[index] = updated;
      }
      Get.snackbar(
        'Đã xác nhận',
        'Dữ kiện [${claim.subject}] đã được chuyển sang trạng thái FOUNDER_CONFIRMED',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.green.withValues(alpha: 0.2),
      );
      await refreshStateVector();
    }
  }

  Future<void> editClaim(StructuredClaimModel claim, String newValue) async {
    if (currentProjectId.value == null) return;
    final updated = await ValidationService.editClaim(
      currentProjectId.value!,
      claim.id,
      newValue,
    );
    if (updated != null) {
      final index = claims.indexWhere((c) => c.id == claim.id);
      if (index != -1) {
        claims[index] = updated;
      }
      Get.snackbar(
        'Đã cập nhật',
        'Dữ kiện [${claim.subject}] đã được sửa và lưu vết vào FieldRevision',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Colors.amber.withValues(alpha: 0.2),
      );
      await refreshStateVector();
    }
  }

  Future<void> markUncertain(StructuredClaimModel claim) async {
    if (currentProjectId.value == null) return;
    await editClaim(claim, 'UNKNOWN');
  }

  Future<void> refreshClaims() async {
    if (currentProjectId.value == null) return;
    final list = await ValidationService.getClaims(currentProjectId.value!);
    claims.assignAll(list);
  }

  Future<void> refreshStateVector() async {
    if (currentProjectId.value == null) return;
    final sv = await ValidationService.getStateVector(currentProjectId.value!);
    if (sv != null) {
      stateVector.value = sv;
    }
  }
}
