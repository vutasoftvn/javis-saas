import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/contracts/enums.generated.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';
import 'package:frontend/modules/strategy/controllers/project_kickoff_controller.dart';
import 'package:frontend/modules/strategy/services/project_operating_setup_service.dart';
import 'package:frontend/modules/strategy/services/strategy_service_base.dart';

class FakeProjectOperatingSetupService extends ProjectOperatingSetupService {
  FakeProjectOperatingSetupService({ProjectOperatingSetup? initialSetup})
    : _setup =
          initialSetup ??
          const ProjectOperatingSetup(
            projectId: 'p-1',
            workspaceId: 'w-1',
            status: OperatingSetupStatus.notStarted,
          );

  ProjectOperatingSetup _setup;
  int saveDraftCallCount = 0;
  int activateCallCount = 0;
  int requestKickoffSuggestionCallCount = 0;
  bool throwOnRequestKickoffSuggestion = false;
  ProjectOperatingSetup? getOverride;
  // Chỉ dùng cho test mô phỏng race dispose-trong-lúc-poll: cho phép giữ
  // `get()` "đang chờ" đủ lâu để test có thể gọi `onDelete()` (dispose thật,
  // set isClosed=true) NGAY GIỮA lúc `await` này còn treo — tái tạo đúng tình
  // huống bug gốc thay vì chỉ dispose trước khi tick kịp bắt đầu.
  Duration getDelay = Duration.zero;

  @override
  Future<ProjectOperatingSetup> get(String projectId) async {
    if (getDelay > Duration.zero) {
      await Future.delayed(getDelay);
    }
    return getOverride ?? _setup;
  }

  @override
  Future<void> requestKickoffSuggestion(String projectId) async {
    requestKickoffSuggestionCallCount++;
    if (throwOnRequestKickoffSuggestion) {
      throw StrategyApiException(500, 'cosa down');
    }
  }

  @override
  Future<ProjectOperatingSetup> saveDraft(
    String projectId,
    ProjectOperatingSetupDraft draft,
  ) async {
    saveDraftCallCount++;
    // Mô phỏng hành vi backend: gán id ổn định cho mỗi action nếu chưa có
    final actionWithIds = draft.firstWeekActions
        .map(
          (a) => FirstWeekActionDraft(
            id: a.id ?? 'id-action-$saveDraftCallCount-${draft.firstWeekActions.indexOf(a)}',
            title: a.title,
          ),
        )
        .toList();
    _setup = ProjectOperatingSetup(
      projectId: projectId,
      workspaceId: 'w-1',
      status: OperatingSetupStatus.inProgress,
      targetCustomer: draft.targetCustomer,
      problemStatement: draft.problemStatement,
      evidenceLevel: draft.evidenceLevel,
      selectedStage: draft.selectedStage,
      stageDurationWeeks: draft.stageDurationWeeks,
      weeklyReviewWeekday: draft.weeklyReviewWeekday,
      weeklyReviewTime: draft.weeklyReviewTime,
      firstWeekOutcome: draft.firstWeekOutcome,
      firstWeekActions: actionWithIds,
    );
    return _setup;
  }

  @override
  Future<ProjectOperatingSetup> activate(
    String projectId,
    ProjectOperatingSetupDraft draft,
  ) async {
    activateCallCount++;
    _setup = ProjectOperatingSetup(
      projectId: projectId,
      workspaceId: 'w-1',
      status: OperatingSetupStatus.active,
      targetCustomer: draft.targetCustomer,
      problemStatement: draft.problemStatement,
      evidenceLevel: draft.evidenceLevel,
      selectedStage: draft.selectedStage,
      stageDurationWeeks: draft.stageDurationWeeks,
      weeklyReviewWeekday: draft.weeklyReviewWeekday,
      weeklyReviewTime: draft.weeklyReviewTime,
      firstWeekOutcome: draft.firstWeekOutcome,
      firstWeekActions: draft.firstWeekActions,
    );
    return _setup;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('resume selects the first incomplete step', () async {
    // 1. Missing evidence -> step 0
    final c1 = ProjectKickoffController(
      service: FakeProjectOperatingSetupService(
        initialSetup: const ProjectOperatingSetup(
          projectId: 'p-1',
          workspaceId: 'w-1',
          status: OperatingSetupStatus.inProgress,
          targetCustomer: 'Founders',
          problemStatement: 'Reporting is slow',
          evidenceLevel: null,
        ),
      ),
    );
    await c1.load('p-1');
    expect(c1.currentStep.value, 0);

    // 2. Step 0 complete, step 1 incomplete -> step 1
    final c2 = ProjectKickoffController(
      service: FakeProjectOperatingSetupService(
        initialSetup: const ProjectOperatingSetup(
          projectId: 'p-1',
          workspaceId: 'w-1',
          status: OperatingSetupStatus.inProgress,
          targetCustomer: 'Founders',
          problemStatement: 'Reporting is slow',
          evidenceLevel: KickoffEvidenceLevel.oneToFourInterviews,
          selectedStage: null,
          stageDurationWeeks: null,
        ),
      ),
    );
    await c2.load('p-1');
    expect(c2.currentStep.value, 1);

    // 3. Step 0 and 1 complete -> step 2
    final c3 = ProjectKickoffController(
      service: FakeProjectOperatingSetupService(
        initialSetup: const ProjectOperatingSetup(
          projectId: 'p-1',
          workspaceId: 'w-1',
          status: OperatingSetupStatus.inProgress,
          targetCustomer: 'Founders',
          problemStatement: 'Reporting is slow',
          evidenceLevel: KickoffEvidenceLevel.oneToFourInterviews,
          selectedStage: ProjectLifecycleStage.p0Discovery,
          stageDurationWeeks: 2,
        ),
      ),
    );
    await c3.load('p-1');
    expect(c3.currentStep.value, 2);
  });

  test('selectEvidence updates stage recommendation and enforces limits', () {
    final controller = ProjectKickoffController();

    // None -> forces P0 / 2 weeks
    controller.selectEvidence(KickoffEvidenceLevel.none);
    expect(controller.selectedStage.value, ProjectLifecycleStage.p0Discovery);
    expect(controller.stageDurationWeeks.value, 2);
    expect(controller.isP1Allowed, isFalse);

    // 5+ interviews -> recommends P1 / 4 weeks
    controller.selectEvidence(KickoffEvidenceLevel.fivePlusInterviews);
    expect(
      controller.selectedStage.value,
      ProjectLifecycleStage.p1ProblemValidation,
    );
    expect(controller.stageDurationWeeks.value, 4);
    expect(controller.isP1Allowed, isTrue);
  });

  test(
    'canActivate validates all required fields and evidence requirements',
    () {
      final controller = ProjectKickoffController();
      expect(controller.canActivate, isFalse);

      controller.targetCustomerCtrl.text = 'B2B Sales';
      expect(controller.canActivate, isFalse);

      controller.problemStatementCtrl.text =
          'Lead qualification takes too long';
      expect(controller.canActivate, isFalse);

      controller.selectEvidence(KickoffEvidenceLevel.none);
      expect(controller.canActivate, isFalse);

      controller.firstWeekOutcomeCtrl.text = 'Interview 5 leads';
      expect(controller.canActivate, isFalse);

      // Add 1 action -> valid for P0
      controller.addAction('Find 10 prospects');
      expect(controller.canActivate, isTrue);

      // Try selecting P1 with NONE evidence -> canActivate is false
      controller.selectedStage.value =
          ProjectLifecycleStage.p1ProblemValidation;
      expect(controller.canActivate, isFalse);

      // Change evidence to 5+ interviews -> P1 becomes valid
      controller.selectEvidence(KickoffEvidenceLevel.fivePlusInterviews);
      controller.selectedStage.value =
          ProjectLifecycleStage.p1ProblemValidation;
      controller.stageDurationWeeks.value = 4;
      expect(controller.canActivate, isTrue);
    },
  );

  test(
    'addAction and removeAction persist immediately instead of waiting for '
    'activate (regression: 3rd first-week action used to be lost if the '
    'founder navigated away before hitting "Xác nhận vòng đầu")',
    () async {
      final fakeService = FakeProjectOperatingSetupService();
      final controller = ProjectKickoffController(service: fakeService);
      await controller.load('p-1');

      await controller.addAction('Interview lead #1');
      expect(fakeService.saveDraftCallCount, 1);
      expect(controller.setup.value?.firstWeekActions.length, 1);

      await controller.addAction('Interview lead #2');
      await controller.addAction('Interview lead #3');
      expect(fakeService.saveDraftCallCount, 3);
      expect(controller.setup.value?.firstWeekActions.length, 3);
      expect(
        controller.setup.value?.firstWeekActions.last.title,
        'Interview lead #3',
      );

      await controller.removeAction(0);
      expect(fakeService.saveDraftCallCount, 4);
      expect(controller.setup.value?.firstWeekActions.length, 2);
    },
  );

  test('updateWeeklyReviewCadence persists the new weekday/time', () async {
    final fakeService = FakeProjectOperatingSetupService();
    final controller = ProjectKickoffController(service: fakeService);
    await controller.load('p-1');

    await controller.updateWeeklyReviewCadence(weekday: 3, time: '10:00');

    expect(controller.weeklyReviewWeekday.value, 3);
    expect(controller.weeklyReviewTime.value, '10:00');
    expect(fakeService.saveDraftCallCount, 1);
    expect(controller.setup.value?.weeklyReviewWeekday, 3);
    expect(controller.setup.value?.weeklyReviewTime, '10:00');
  });

  test('activate invokes service and updates setup to ACTIVE', () async {
    final fakeService = FakeProjectOperatingSetupService();
    final controller = ProjectKickoffController(service: fakeService);
    await controller.load('p-1');

    controller.targetCustomerCtrl.text = 'B2B Finance';
    controller.problemStatementCtrl.text =
        'Invoicing reconciliation is painful';
    controller.selectEvidence(KickoffEvidenceLevel.fivePlusInterviews);
    controller.selectedStage.value = ProjectLifecycleStage.p1ProblemValidation;
    controller.stageDurationWeeks.value = 4;
    controller.firstWeekOutcomeCtrl.text = 'Talk to 5 controllers';
    controller.addAction('List 10 candidate finance teams');

    expect(controller.canActivate, isTrue);
    final ok = await controller.activate();
    expect(ok, isTrue);
    expect(fakeService.activateCallCount, 1);
    expect(controller.setup.value?.status, OperatingSetupStatus.active);
  });

  test(
    'activate() flushes pending text left in the "Thêm việc" input '
    '(regression: task typed but not yet confirmed via "Thêm việc"/Enter '
    'was silently dropped when the founder pressed "Xác nhận vòng đầu" '
    'directly)',
    () async {
      final fakeService = FakeProjectOperatingSetupService();
      final controller = ProjectKickoffController(service: fakeService);
      await controller.load('p-1');

      controller.targetCustomerCtrl.text = 'B2B Finance';
      controller.problemStatementCtrl.text =
          'Invoicing reconciliation is painful';
      controller.selectEvidence(KickoffEvidenceLevel.none);
      controller.firstWeekOutcomeCtrl.text = 'Talk to 5 controllers';

      await controller.addAction('Interview lead #1');
      // Founder gõ task 2 nhưng KHÔNG bấm "Thêm việc"/Enter, bấm thẳng
      // "Xác nhận vòng đầu" luôn.
      controller.newActionCtrl.text = 'Interview lead #2';

      expect(controller.canActivate, isTrue);
      final ok = await controller.activate();
      expect(ok, isTrue);
      expect(controller.firstWeekActions.length, 2);
      expect(controller.firstWeekActions.last.title, 'Interview lead #2');
      expect(
        controller.newActionCtrl.text,
        isEmpty,
        reason: 'Input phải được clear sau khi flush vào list',
      );
      expect(
        controller.setup.value?.firstWeekActions
            .map((a) => a.title)
            .toList(),
        equals(['Interview lead #1', 'Interview lead #2']),
      );
    },
  );

  test(
    'saveCurrentStep adopts server-assigned action IDs to prevent task churn',
    () async {
      // Hồi quy: sau fix sơ bộ auto-save, mỗi lần addAction() hay updateWeeklyReviewCadence()
      // gọi saveCurrentStep(), nhưng id từ server không bao giờ được copy lại vào
      // firstWeekActions RxList → list cục bộ vẫn có id: null → lần save tiếp theo
      // backend sinh id MỚI cho mọi action → hệ thống materialize churn task mỗi lần
      final fakeService = FakeProjectOperatingSetupService();
      final controller = ProjectKickoffController(service: fakeService);
      await controller.load('p-1');

      // Thêm action đầu tiên
      await controller.addAction('Interview lead #1');
      expect(fakeService.saveDraftCallCount, 1);
      final firstActionId = controller.firstWeekActions.first.id;
      expect(
        firstActionId,
        isNotNull,
        reason:
            'Sau saveCurrentStep(), action phải có id từ server, không null',
      );

      // Thêm action thứ hai — nếu bug vẫn tồn tại, lần save này sẽ sinh id MỚI
      // cho action #1 cũ vì action #1 vẫn có id: null
      await controller.addAction('Interview lead #2');
      expect(fakeService.saveDraftCallCount, 2);

      // Kiểm tra action #1 giữ nguyên id (không bị tạo lại)
      final firstActionIdAfterSecondSave =
          controller.firstWeekActions[0].id;
      expect(
        firstActionIdAfterSecondSave,
        equals(firstActionId),
        reason:
            'Action #1 phải giữ nguyên id, không được tạo id mới mỗi lần save',
      );

      // Kiểm tra action #2 có id gán từ lần save thứ 2
      final secondActionId = controller.firstWeekActions[1].id;
      expect(
        secondActionId,
        isNotNull,
        reason: 'Action #2 phải có id từ server',
      );
      expect(
        secondActionId,
        isNot(equals(firstActionId)),
        reason: 'Action #2 phải có id khác action #1',
      );
    },
  );

  // Lưu ý: `group()` của flutter_test (test_compat.dart) không nhận tham số
  // `timeout` như `group()` gốc của package:test — chỉ `test()` mới nhận. Đặt
  // timeout 10s ở từng test riêng lẻ (dư so với 1 tick poll 2.1s trong test)
  // thay vì ở group.
  group('requestKickoffSuggestion', () {
    test(
      'không gọi service khi overwrite=false và outcome đã có nội dung',
      () async {
        final service = FakeProjectOperatingSetupService();
        final controller = ProjectKickoffController(service: service);
        await controller.load('p1');
        controller.firstWeekOutcomeCtrl.text = 'Đã tự gõ rồi';

        await controller.requestKickoffSuggestion(overwrite: false);

        expect(service.requestKickoffSuggestionCallCount, 0);
      },
      timeout: const Timeout(Duration(seconds: 10)),
    );

    test(
      'gọi service khi overwrite=true dù outcome đã có nội dung',
      () async {
        final service = FakeProjectOperatingSetupService();
        final controller = ProjectKickoffController(service: service);
        await controller.load('p1');
        controller.firstWeekOutcomeCtrl.text = 'Đã tự gõ rồi';
        service.getOverride = const ProjectOperatingSetup(
          projectId: 'p1',
          workspaceId: 'w1',
          status: OperatingSetupStatus.inProgress,
          aiSuggestionStatus: 'completed',
          aiSuggestedOutcome: 'Gợi ý AI mới',
          aiSuggestedActions: ['Việc AI gợi ý'],
        );

        await controller.requestKickoffSuggestion(overwrite: true);
        await Future.delayed(const Duration(milliseconds: 2100));

        expect(service.requestKickoffSuggestionCallCount, 1);
        expect(controller.firstWeekOutcomeCtrl.text, 'Gợi ý AI mới');
        expect(controller.firstWeekActions.map((a) => a.title).toList(), [
          'Việc AI gợi ý',
        ]);
        expect(controller.aiSuggestionLoading.value, false);
      },
      timeout: const Timeout(Duration(seconds: 10)),
    );

    test(
      'dừng loading ngay khi service throw (không poll)',
      () async {
        final service = FakeProjectOperatingSetupService()
          ..throwOnRequestKickoffSuggestion = true;
        final controller = ProjectKickoffController(service: service);
        await controller.load('p1');

        await controller.requestKickoffSuggestion(overwrite: true);

        expect(controller.aiSuggestionLoading.value, false);
      },
      timeout: const Timeout(Duration(seconds: 10)),
    );

    test(
      'dừng poll và tắt loading khi status=failed',
      () async {
        final service = FakeProjectOperatingSetupService();
        final controller = ProjectKickoffController(service: service);
        await controller.load('p1');
        service.getOverride = const ProjectOperatingSetup(
          projectId: 'p1',
          workspaceId: 'w1',
          status: OperatingSetupStatus.inProgress,
          aiSuggestionStatus: 'failed',
        );

        await controller.requestKickoffSuggestion(overwrite: true);
        await Future.delayed(const Duration(milliseconds: 2100));

        expect(controller.aiSuggestionLoading.value, false);
        expect(controller.firstWeekOutcomeCtrl.text, isEmpty);
      },
      timeout: const Timeout(Duration(seconds: 10)),
    );

    test(
      'dừng poll và tắt loading sau khi vượt mốc 30s nếu status không bao '
      'giờ về trạng thái cuối (nhánh timeout — trước đây chưa có test)',
      () {
        // Dùng fake_async để "tua" 30s ảo tức thời thay vì chờ 30s thật —
        // Timer.periodic bên trong _pollSuggestion() và Future.delayed bên
        // trong FakeProjectOperatingSetupService đều chạy trên cùng đồng hồ
        // ảo này nên vẫn tất định.
        fakeAsync((async) {
          final service = FakeProjectOperatingSetupService();
          final controller = ProjectKickoffController(service: service);
          controller.load('p1');
          async.elapse(const Duration(milliseconds: 10));

          // Status không bao giờ "completed"/"failed" — mô phỏng backend kẹt
          // (job worker chết, hoặc job không bao giờ hoàn tất).
          service.getOverride = const ProjectOperatingSetup(
            projectId: 'p1',
            workspaceId: 'w1',
            status: OperatingSetupStatus.inProgress,
            aiSuggestionStatus: 'pending',
          );

          controller.requestKickoffSuggestion(overwrite: true);
          async.elapse(const Duration(milliseconds: 10));
          expect(controller.aiSuggestionLoading.value, isTrue);

          // 15 tick x 2000ms = 30000ms (_suggestionPollTimeoutMs) — tick thứ
          // 15 thấy _suggestionPollElapsedMs đã >= 30000ms nên tự dừng, dù
          // status vẫn "pending". Elapse dư 50ms để chắc chắn tick 15 chạy
          // xong trọn vẹn.
          async.elapse(const Duration(milliseconds: 30050));

          expect(controller.aiSuggestionLoading.value, isFalse);
          expect(controller.firstWeekOutcomeCtrl.text, isEmpty);
          expect(controller.firstWeekActions, isEmpty);
        });
      },
      timeout: const Timeout(Duration(seconds: 10)),
    );

    test(
      'không crash khi controller bị dispose (onDelete) trong lúc 1 tick '
      'poll đang chờ _service.get() (race điều kiện của bug gốc: '
      'timer.cancel() trong onClose() chỉ chặn tick TƯƠNG LAI, không huỷ '
      'được continuation của tick đang await dở — ghi vào '
      'firstWeekOutcomeCtrl đã dispose sẽ throw AssertionError nếu thiếu '
      'guard isClosed)',
      () {
        fakeAsync((async) {
          // getDelay giữ `_service.get()` "đang treo" đủ lâu để test có thể
          // dispose NGAY GIỮA lúc await còn chưa resolve — tái tạo đúng race,
          // khác với chỉ dispose trước khi tick kịp bắt đầu (không có ý nghĩa
          // vì onClose() đã cancel timer, tick sẽ không bao giờ chạy).
          final service = FakeProjectOperatingSetupService()
            ..getDelay = const Duration(milliseconds: 500);
          final controller = ProjectKickoffController(service: service);
          controller.load('p1');
          async.elapse(const Duration(milliseconds: 600));

          service.getOverride = const ProjectOperatingSetup(
            projectId: 'p1',
            workspaceId: 'w1',
            status: OperatingSetupStatus.inProgress,
            aiSuggestionStatus: 'completed',
            aiSuggestedOutcome: 'Gợi ý AI mới',
            aiSuggestedActions: ['Việc AI gợi ý'],
          );

          controller.requestKickoffSuggestion(overwrite: true);
          async.elapse(const Duration(milliseconds: 10));
          expect(controller.aiSuggestionLoading.value, isTrue);

          // Timer.periodic được tạo ở mốc đồng hồ ảo hiện tại (~610ms, sau
          // 600ms load() tiêu tốn + 10ms flush await ở trên) nên tick ĐẦU
          // TIÊN bắn ở ~610+2000=2610ms và ngay lập tức bắt đầu `await
          // _service.get()` (delay riêng 500ms, resolve ở ~3110ms). Elapse
          // thêm 2100ms (610 -> 2710ms) để đứng NGAY GIỮA khoảng await đó
          // (đã fire tick, chưa resolve get()) rồi mới dispose — đây chính
          // là interleaving của bug gốc.
          async.elapse(const Duration(milliseconds: 2100));

          // Dispose qua onDelete() (không phải gọi thẳng onClose()) vì GetX
          // chỉ set `isClosed = true` bên trong _onDelete() trước khi gọi
          // onClose() — đây cũng là đường dispose thật khi Get gỡ controller
          // (get_instance.dart, get_view.dart đều gọi `i.onDelete()`).
          // `onDelete` là `InternalFinalCallback<void>` (callable object, không
          // phải `Function` thật) nên không dùng được matcher `returnsNormally`
          // — gọi trực tiếp; nếu nó throw thì test tự fail vì lỗi thoát ra
          // ngoài scope.
          controller.onDelete();
          expect(controller.isClosed, isTrue);

          // Chờ nốt cho `await _service.get()` của tick đang treo resolve
          // (bắt đầu await ở ~2610ms, delay 500ms -> resolve ở ~3110ms; hiện
          // đang ở ~2710ms nên cần thêm >= 400ms, dùng dư 450ms). Nếu guard
          // `isClosed` trong _pollSuggestion() bị thiếu, dòng elapse dưới đây
          // sẽ ném AssertionError (used after dispose) vì code sẽ chạy
          // `firstWeekOutcomeCtrl.text = ...` trên TextEditingController đã
          // bị dispose ở trên.
          expect(
            () => async.elapse(const Duration(milliseconds: 450)),
            returnsNormally,
          );
        });
      },
      timeout: const Timeout(Duration(seconds: 10)),
    );
  });
}
