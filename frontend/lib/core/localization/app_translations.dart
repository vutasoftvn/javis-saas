import 'package:get/get.dart';
import 'locales/en/en_auth.dart';
import 'locales/en/en_chat.dart';
import 'locales/en/en_common.dart';
import 'locales/en/en_settings.dart';
import 'locales/en/en_strategy.dart';
import 'locales/vi/vi_auth.dart';
import 'locales/vi/vi_chat.dart';
import 'locales/vi/vi_common.dart';
import 'locales/vi/vi_settings.dart';
import 'locales/vi/vi_strategy.dart';
import 'locales/en/en_tasks.dart';
import 'locales/vi/vi_tasks.dart';
import 'locales/en/en_automation.dart';
import 'locales/vi/vi_automation.dart';

abstract final class L10nKey {
  // App
  static const appTitle = 'app.title';

  // Navigation Groups
  static const navGroupConversation = 'nav.group.conversation';
  static const navGroupCycle = 'nav.group.cycle';
  static const navGroupOperations = 'nav.group.operations';
  static const navGroupAi = 'nav.group.ai';
  static const navGroupFinanceVault = 'nav.group.financeVault';
  static const navGroupOrganization = 'nav.group.organization';
  static const navGroupExperimental = 'nav.group.experimental';

  // Navigation Items
  static const navCommandCenter = 'nav.item.commandCenter';
  static const navStrategy = 'nav.item.strategy';
  static const navProjects = 'nav.item.projects';
  static const navOkrs = 'nav.item.okrs';
  static const navTwelveWy = 'nav.item.twelveWy';
  static const navFunding = 'nav.item.funding';
  static const navTasks = 'nav.item.tasks';
  static const navApprovals = 'nav.item.approvals';
  static const navNeedsYou = 'nav.item.needsYou';
  static const navBlockedWork = 'nav.item.blockedWork';
  static const navWorkInspector = 'nav.item.workInspector';
  static const navAiAgents = 'nav.item.aiAgents';
  static const navLegal = 'nav.item.legal';
  static const navMarketing = 'nav.item.marketing';
  static const navCrm = 'nav.item.crm';
  static const navSkillRegistry = 'nav.item.skillRegistry';
  static const navFinance = 'nav.item.finance';
  static const navVault = 'nav.item.vault';
  static const navOrgChart = 'nav.item.orgChart';
  static const navWorkflows = 'nav.item.workflows';
  static const navTemplates = 'nav.item.templates';
  static const navSettings = 'nav.item.settings';
  static const navAdvancedWorkflows = 'nav.item.advancedWorkflows';
  static const navAdvancedOrgChart = 'nav.item.advancedOrgChart';

  // Modules (canonical)
  static const moduleFinance = 'module.finance';
  static const moduleLegal = 'module.legal';
  static const moduleCrm = 'module.crm';
  static const moduleTasks = 'module.tasks';

  // Tasks - Status
  static const tasksStatusTodo = 'tasks.status.todo';
  static const tasksStatusInProgress = 'tasks.status.inProgress';
  static const tasksStatusWaitingApproval = 'tasks.status.waitingApproval';
  static const tasksStatusBlocked = 'tasks.status.blocked';
  static const tasksStatusDone = 'tasks.status.done';
  static const tasksStatusCancelled = 'tasks.status.cancelled';

  // Tasks - Priority
  static const tasksPriorityLow = 'tasks.priority.low';
  static const tasksPriorityMedium = 'tasks.priority.medium';
  static const tasksPriorityHigh = 'tasks.priority.high';

  // Tasks - UI
  static const tasksAddQuick = 'tasks.addQuick';
  static const tasksDialogTitle = 'tasks.dialog.title';
  static const tasksDialogHintTitle = 'tasks.dialog.hintTitle';
  static const tasksDialogHintDescription = 'tasks.dialog.hintDescription';
  static const tasksDialogSave = 'tasks.dialog.save';
  static const tasksDialogCancel = 'tasks.dialog.cancel';

  // Chat UI
  static const chatNewConversation = 'chat.newConversation';
  static const chatHistory = 'chat.history';
  static const chatNoConversations = 'chat.noConversations';
  static const chatStartNew = 'chat.startNew';
  static const chatComposerHint = 'chat.composer.hint';
  static const chatReconnecting = 'chat.reconnecting';
  static const chatAgentOsTitle = 'chat.agentOsTitle';
  static const chatAdvisoryDomain = 'chat.advisoryDomain';

  // Profile UI
  static const profileTitle = 'profile.title';
  static const profileLanguageTitle = 'profile.language.title';
  static const profileLanguageVi = 'profile.language.vi';
  static const profileLanguageEn = 'profile.language.en';
  static const profileUnnamed = 'profile.unnamed';
  static const profileEmail = 'profile.email';
  static const profileFullName = 'profile.fullName';
  static const profileSaveName = 'profile.saveName';
  static const profilePhone = 'profile.phone';
  static const profileNoPhone = 'profile.noPhone';
  static const profileSavePhone = 'profile.savePhone';
  static const profileLogout = 'profile.logout';

  // Auth UI
  static const authIdentifierLabel = 'auth.identifier.label';
  static const authIdentifierHint = 'auth.identifier.hint';
  static const authPasswordLabel = 'auth.password.label';
  static const authRememberMe = 'auth.rememberMe';
  static const authLoginButton = 'auth.loginButton';
  static const authNoAccount = 'auth.noAccount';
  static const authCreateAccount = 'auth.createAccount';
  static const authLanguageSwitchTooltip = 'auth.languageSwitchTooltip';

  // Register UI
  static const regStep1Title = 'reg.step1.title';
  static const regStep2Title = 'reg.step2.title';
  static const regStep1Subtitle = 'reg.step1.subtitle';
  static const regStep2Subtitle = 'reg.step2.subtitle';
  static const regStepAccount = 'reg.step.account';
  static const regStepCompany = 'reg.step.company';
  static const regFullNameLabel = 'reg.fullName.label';
  static const regEmailLabel = 'reg.email.label';
  static const regEmailHint = 'reg.email.hint';
  static const regPasswordLabel = 'reg.password.label';
  static const regConfirmPasswordLabel = 'reg.confirmPassword.label';
  static const regCreatingAccount = 'reg.creatingAccount';
  static const regContinue = 'reg.continue';
  static const regTabCreateCompany = 'reg.tab.createCompany';
  static const regTabJoinCompany = 'reg.tab.joinCompany';
  static const regInvitationTokenLabel = 'reg.invitationToken.label';
  static const regInvitationTokenHint = 'reg.invitationToken.hint';
  static const regInvitationTokenHelper = 'reg.invitationToken.helper';
  static const regCompanyNameLabel = 'reg.companyName.label';
  static const regCompanyNameHint = 'reg.companyName.hint';
  static const regCompanyNameHelper = 'reg.companyName.helper';
  static const regInitializingBrain = 'reg.initializingBrain';
  static const regInitialize = 'reg.initialize';
  static const regBackToStep1 = 'reg.backToStep1';
  static const regAlreadyHaveAccount = 'reg.alreadyHaveAccount';
  static const regLoginNow = 'reg.loginNow';

  // Settings UI
  static const settingsTitle = 'settings.title';
  static const settingsSubtitle = 'settings.subtitle';
  static const settingsModulesTitle = 'settings.modules.title';
  static const settingsModulesSubtitle = 'settings.modules.subtitle';
  static const settingsModuleUserVisible = 'settings.modules.userVisible';
  static const settingsModuleWorkspaceEnabled = 'settings.modules.workspaceEnabled';
  static const settingsModuleUpdateError = 'settings.modules.updateError';

  // Common UI
  static const commonAdd = 'common.add';
  static const commonEdit = 'common.edit';
  static const commonSave = 'common.save';
  static const commonCancel = 'common.cancel';
  static const commonLoading = 'common.loading';
  static const commonError = 'common.error';
  static const commonSuccess = 'common.success';

  // Hologram Hub UI
  static const hubSubtitle = 'hub.subtitle';
  static const hubSwitchModule = 'hub.switchModule';
  static const hubManageDashboard = 'hub.manageDashboard';
  static const hubRefreshData = 'hub.refreshData';
  static const hubMyProfile = 'hub.myProfile';
  static const hubContinueSetup = 'hub.continueSetup';
  static const hubSetupIncompleteTitle = 'hub.setupIncompleteTitle';
  static const hubSetupIncompleteDesc = 'hub.setupIncompleteDesc';
  static const hubPlanningInProgress = 'hub.planningInProgress';
  static const hubAskAiPlan = 'hub.askAiPlan';
  static const hubCreateNewProject = 'hub.createNewProject';
  static const hubProjectNameLabel = 'hub.projectNameLabel';
  static const hubProjectNameHint = 'hub.projectNameHint';
  static const hubProjectDescLabel = 'hub.projectDescLabel';
  static const hubProjectDescHint = 'hub.projectDescHint';
  static const hubEnterProjectNameError = 'hub.enterProjectNameError';
  static const hubMissingInfoTitle = 'hub.missingInfoTitle';
  static const hubCreateProjectAction = 'hub.createProjectAction';
  static const hubSweepEnabled = 'hub.sweepEnabled';
  static const hubSweepDisabled = 'hub.sweepDisabled';

  // Strategy Lenses: Hub Modal
  static const strategyHubTitle = 'strategy.hubTitle';
  static const strategyHubSubtitle = 'strategy.hubSubtitle';
  static const strategyTabSwot = 'strategy.tabSwot';
  static const strategyTabBsc = 'strategy.tabBsc';
  static const strategyTabBscLocked = 'strategy.tabBscLocked';

  // Strategy Lenses: PESTEL
  static const pestelDimPolitical = 'pestel.dim.political';
  static const pestelDimEconomic = 'pestel.dim.economic';
  static const pestelDimSocial = 'pestel.dim.social';
  static const pestelDimTechnological = 'pestel.dim.technological';
  static const pestelDimEnvironmental = 'pestel.dim.environmental';
  static const pestelDimLegal = 'pestel.dim.legal';
  static const pestelCatchSignal = 'pestel.catchSignal';
  static const pestelMacroDimLabel = 'pestel.macroDimLabel';
  static const pestelSignalTitleLabel = 'pestel.signalTitleLabel';
  static const pestelSignalTitleHint = 'pestel.signalTitleHint';
  static const pestelContextLabel = 'pestel.contextLabel';
  static const pestelSaveSignal = 'pestel.saveSignal';
  static const pestelBannerDesc = 'pestel.bannerDesc';
  static const pestelAddTooltip = 'pestel.addTooltip';
  static const pestelEmpty = 'pestel.empty';
  static const pestelHypothesisCreated = 'pestel.hypothesisCreated';
  static const pestelGenerateHypothesis = 'pestel.generateHypothesis';

  // Strategy Lenses: SWOT
  static const swotTypeStrength = 'swot.type.strength';
  static const swotTypeWeakness = 'swot.type.weakness';
  static const swotTypeOpportunity = 'swot.type.opportunity';
  static const swotTypeThreat = 'swot.type.threat';
  static const swotAddTitle = 'swot.addTitle';
  static const swotTypeLabel = 'swot.typeLabel';
  static const swotContentLabel = 'swot.contentLabel';
  static const swotContentHint = 'swot.contentHint';
  static const swotSave = 'swot.save';
  static const swotHeader = 'swot.header';
  static const swotAddTooltip = 'swot.addTooltip';
  static const swotEmpty = 'swot.empty';

  // Strategy Lenses: TOWS
  static const towsTypeSo = 'tows.type.so';
  static const towsTypeWo = 'tows.type.wo';
  static const towsTypeSt = 'tows.type.st';
  static const towsTypeWt = 'tows.type.wt';
  static const towsCreateTitle = 'tows.createTitle';
  static const towsPairLabel = 'tows.pairLabel';
  static const towsStrategyNameLabel = 'tows.strategyNameLabel';
  static const towsStrategyNameHint = 'tows.strategyNameHint';
  static const towsDescLabel = 'tows.descLabel';
  static const towsSaveStrategy = 'tows.saveStrategy';
  static const towsEvalTitle = 'tows.evalTitle';
  static const towsImpactScore = 'tows.impactScore';
  static const towsDifficultyScore = 'tows.difficultyScore';
  static const towsRatingExplanation = 'tows.ratingExplanation';
  static const towsSaveEvaluation = 'tows.saveEvaluation';
  static const towsSelectTitle = 'tows.selectTitle';
  static const towsSelectDesc = 'tows.selectDesc';
  static const towsSelectReasonLabel = 'tows.selectReasonLabel';
  static const towsConfirmSelect = 'tows.confirmSelect';
  static const towsMatrixHeader = 'tows.matrixHeader';
  static const towsSelectionCount = 'tows.selectionCount';
  static const towsAddTooltip = 'tows.addTooltip';
  static const towsEmpty = 'tows.empty';
  static const towsSelected = 'tows.selected';
  static const towsScoreBtn = 'tows.scoreBtn';
  static const towsSelectBtn = 'tows.selectBtn';

  // Strategy Lenses: BSC
  static const bscPerspFinancial = 'bsc.persp.financial';
  static const bscPerspCustomer = 'bsc.persp.customer';
  static const bscPerspInternal = 'bsc.persp.internal';
  static const bscPerspLearning = 'bsc.persp.learning';
  static const bscTitle = 'bsc.title';
  static const bscHeaderDesc = 'bsc.headerDesc';
  static const bscReadOnlyDesc = 'bsc.readOnlyDesc';
  static const bscEmpty = 'bsc.empty';

  // Project Setup & Kickoff
  static const projectSetupTitle = 'project.setup.title';
  static const projectSetupSubtitle = 'project.setup.subtitle';
  static const projectSetupNameLabel = 'project.setup.nameLabel';
  static const projectSetupDescLabel = 'project.setup.descLabel';
  static const projectSetupSubmitButton = 'project.setup.submitButton';
  static const projectSetupSubmitting = 'project.setup.submitting';
  static const projectSetupCancelButton = 'project.setup.cancelButton';
  static const projectSetupLogoutButton = 'project.setup.logoutButton';
  static const projectSetupSwitchWorkspaceButton = 'project.setup.switchWorkspaceButton';
  static const projectSetupNameRequired = 'project.setup.nameRequired';
  static const projectSetupFailed = 'project.setup.failed';
  static const projectKickoffTitle = 'project.kickoff.title';
  static const projectKickoffSubtitle = 'project.kickoff.subtitle';
  static const projectKickoffAdvancedRoadmap = 'project.kickoff.advancedRoadmap';
  static const projectKickoffBack = 'project.kickoff.back';
  static const projectKickoffSettingsTooltip = 'project.kickoff.settingsTooltip';
  static const projectKickoffStepTab1 = 'project.kickoff.stepTab1';
  static const projectKickoffStepTab2 = 'project.kickoff.stepTab2';
  static const projectKickoffStepTab3 = 'project.kickoff.stepTab3';
  static const projectKickoffStep1Title = 'project.kickoff.step1Title';
  static const projectKickoffTargetCustomerLabel = 'project.kickoff.targetCustomerLabel';
  static const projectKickoffTargetCustomerHint = 'project.kickoff.targetCustomerHint';
  static const projectKickoffProblemStatementLabel = 'project.kickoff.problemStatementLabel';
  static const projectKickoffProblemStatementHint = 'project.kickoff.problemStatementHint';
  static const projectKickoffEvidenceLabel = 'project.kickoff.evidenceLabel';
  static const projectKickoffEvidenceNone = 'project.kickoff.evidenceNone';
  static const projectKickoffEvidenceOneToFour = 'project.kickoff.evidenceOneToFour';
  static const projectKickoffEvidenceFivePlus = 'project.kickoff.evidenceFivePlus';
  static const projectKickoffEvidencePrototypeOrRevenue = 'project.kickoff.evidencePrototypeOrRevenue';
  static const projectKickoffSaving = 'project.kickoff.saving';
  static const projectKickoffContinue = 'project.kickoff.continue';
  static const projectKickoffStep2Title = 'project.kickoff.step2Title';
  static const projectKickoffProposalP0 = 'project.kickoff.proposalP0';
  static const projectKickoffProposalP1 = 'project.kickoff.proposalP1';
  static const projectKickoffGoalP0 = 'project.kickoff.goalP0';
  static const projectKickoffGoalP1 = 'project.kickoff.goalP1';
  static const projectKickoffSelectStageLabel = 'project.kickoff.selectStageLabel';
  static const projectKickoffStageP0Title = 'project.kickoff.stageP0Title';
  static const projectKickoffStageP0Subtitle = 'project.kickoff.stageP0Subtitle';
  static const projectKickoffStageP1Title = 'project.kickoff.stageP1Title';
  static const projectKickoffStageP1Subtitle = 'project.kickoff.stageP1Subtitle';
  static const projectKickoffP1Warning = 'project.kickoff.p1Warning';
  static const projectKickoffCycleDurationLabel = 'project.kickoff.cycleDurationLabel';
  static const projectKickoffWeeksCount = 'project.kickoff.weeksCount';
  static const projectKickoffCycleStartDateLabel = 'project.kickoff.cycleStartDateLabel';
  static const projectKickoffDefaultNextMonday = 'project.kickoff.defaultNextMonday';
  static const projectKickoffStep3Title = 'project.kickoff.step3Title';
  static const projectKickoffRegenerateAiTooltip = 'project.kickoff.regenerateAiTooltip';
  static const projectKickoffStep3Context = 'project.kickoff.step3Context';
  static const projectKickoffFirstWeekOutcomeLabel = 'project.kickoff.firstWeekOutcomeLabel';
  static const projectKickoffFirstWeekOutcomeHint = 'project.kickoff.firstWeekOutcomeHint';
  static const projectKickoffFirstWeekOutcomeInputHint = 'project.kickoff.firstWeekOutcomeInputHint';
  static const projectKickoffFirstWeekActionsLabel = 'project.kickoff.firstWeekActionsLabel';
  static const projectKickoffActionsCount = 'project.kickoff.actionsCount';
  static const projectKickoffDeleteActionTooltip = 'project.kickoff.deleteActionTooltip';
  static const projectKickoffNewActionHint = 'project.kickoff.newActionHint';
  static const projectKickoffAddActionButton = 'project.kickoff.addActionButton';
  static const projectKickoffWeeklyReviewDayLabel = 'project.kickoff.weeklyReviewDayLabel';
  static const projectKickoffReviewScheduleText = 'project.kickoff.reviewScheduleText';
  static const projectKickoffActivating = 'project.kickoff.activating';
  static const projectKickoffConfirmCycle = 'project.kickoff.confirmCycle';
  static const weekdayMonday = 'common.weekday.monday';
  static const weekdayTuesday = 'common.weekday.tuesday';
  static const weekdayWednesday = 'common.weekday.wednesday';
  static const weekdayThursday = 'common.weekday.thursday';
  static const weekdayFriday = 'common.weekday.friday';
  static const weekdaySaturday = 'common.weekday.saturday';
  static const weekdaySunday = 'common.weekday.sunday';

  // Company Scope Switcher
  static const companyScopeGlobal = 'company.scope.global';
  static const companyScopeNarrow = 'company.scope.narrow';

  // Hologram Hub / Command Center UI
  static const hubPulseGoalsOnTrack = 'hub.pulse.goalsOnTrack';
  static const hubPulseActiveMissions = 'hub.pulse.activeMissions';
  static const hubPulseNeedsDecision = 'hub.pulse.needsDecision';
  static const hubPulseMajorRisks = 'hub.pulse.majorRisks';
  static const hubCofounderDiscuss = 'hub.cofounder.discuss';
  static const hubCofounderDefaultFocus = 'hub.cofounder.defaultFocus';
  static const hubCofounderFocusWithProject = 'hub.cofounder.focusWithProject';
  static const hubCofounderFocusNoProject = 'hub.cofounder.focusNoProject';
  static const hubCurrentCycleBadge = 'hub.cycle.currentCycleBadge';
  static const hubReviewScheduleBadge = 'hub.cycle.reviewScheduleBadge';
  static const hubFirstWeekOutcomePrefix = 'hub.cycle.firstWeekOutcomePrefix';
  static const hubTop3Title = 'hub.top3.title';
  static const hubTop3Empty = 'hub.top3.empty';
  static const hubFirstWeekActionsTitle = 'hub.top3.firstWeekActionsTitle';
  static const hubActionNoTimeSet = 'hub.top3.actionNoTimeSet';
  static const hubActionCategoryDecision = 'hub.action.category.decision';
  static const hubActionCategoryExperiment = 'hub.action.category.experiment';
  static const hubActionCategoryAction = 'hub.action.category.action';
  static const hubWaitingEmpty = 'hub.waiting.empty';
  static const hubWaitingTitle = 'hub.waiting.title';
  static const hubWaitingItemsCount = 'hub.waiting.itemsCount';
  static const hubDecisionMakeDecision = 'hub.decision.makeDecision';
  static const hubApprovalDefaultTitle = 'hub.approval.defaultTitle';
  static const hubApprovalReject = 'hub.approval.reject';
  static const hubApprovalApprove = 'hub.approval.approve';
  static const hubApprovalRejectDialogTitle = 'hub.approval.rejectDialogTitle';
  static const hubApprovalRejectReasonHint = 'hub.approval.rejectReasonHint';
  static const hubDecisionModalHeader = 'hub.decisionModal.header';
  static const hubDecisionModalAiRecHeader = 'hub.decisionModal.aiRecHeader';
  static const hubDecisionModalAiRecDefaultReason = 'hub.decisionModal.aiRecDefaultReason';
  static const hubDecisionModalSelectOption = 'hub.decisionModal.selectOption';
  static const hubDecisionModalFinancialImpact = 'hub.decisionModal.financialImpact';
  static const hubDecisionModalNotesHint = 'hub.decisionModal.notesHint';
  static const hubDecisionModalClose = 'hub.decisionModal.close';
  static const hubDecisionModalConfirm = 'hub.decisionModal.confirm';
  static const hubProposedPlanTitle = 'hub.proposedPlan.title';
  static const hubProposedPlanItemsCount = 'hub.proposedPlan.itemsCount';
  static const hubProposedPlanAcceptAll = 'hub.proposedPlan.acceptAll';
  static const hubProposedPlanDismiss = 'hub.proposedPlan.dismiss';
  static const hubProposedPlanMissingEvidence = 'hub.proposedPlan.missingEvidence';
  static const hubProposedPlanDropItemTooltip = 'hub.proposedPlan.dropItemTooltip';
  static const autonomyClassAuto = 'hub.autonomy.auto';
  static const autonomyClassNeedsApproval = 'hub.autonomy.needsApproval';
  static const autonomyClassFounderOnly = 'hub.autonomy.founderOnly';
  static const hubYourTasksTitle = 'hub.yourTasks.title';
  static const hubTaskBlocked = 'hub.yourTasks.blocked';
  static const hubTaskNeedsYou = 'hub.yourTasks.needsYou';
  static const hubTabCommandCenter = 'hub.tab.commandCenter';
  static const hubTabCommandCenterShort = 'hub.tab.commandCenterShort';
  static const hubTabWorkforce = 'hub.tab.workforce';
  static const hubTabWorkforceShort = 'hub.tab.workforceShort';
  static const hubPrematureMoreAlerts = 'hub.prematureAlerts.more';
  static const hubUpdateFailedToast = 'hub.updateFailedToast';

  // Sidebar Chrome
  static const sidebarDeveloperMode = 'sidebar.developerMode';
  static const sidebarLogout = 'sidebar.logout';
  static const sidebarBackToHub = 'sidebar.backToHub';

  // Common UI additions
  static const commonRefresh = 'common.refresh';
  static const commonRetry = 'common.retry';

  // Roadmap & Projects
  static const roadmapProjectsTitle = 'roadmap.projects.title';
  static const roadmapProjectsSubtitle = 'roadmap.projects.subtitle';
  static const roadmapManageTemplates = 'roadmap.manageTemplates';
  static const roadmapNewProject = 'roadmap.newProject';
  static const roadmapNoProjects = 'roadmap.noProjects';
  static const roadmapNoProjectsDesc = 'roadmap.noProjectsDesc';
  static const roadmapCreateNewProject = 'roadmap.createNewProject';
  static const roadmapWeeksCount = 'roadmap.weeksCount';
  static const roadmapFromDate = 'roadmap.fromDate';
  static const roadmapElapsedDays = 'roadmap.elapsedDays';
  static const roadmapOpenMarketingTooltip = 'roadmap.openMarketingTooltip';
  static const roadmapViewRoadmapTooltip = 'roadmap.viewRoadmapTooltip';
  static const roadmapAiGenerateTooltip = 'roadmap.aiGenerateTooltip';
  static const roadmapCreateDialogTitle = 'roadmap.createDialogTitle';
  static const roadmapCreateDialogSubtitle = 'roadmap.createDialogSubtitle';
  static const roadmapProjectNameLabel = 'roadmap.projectNameLabel';
  static const roadmapProjectNameHint = 'roadmap.projectNameHint';
  static const roadmapProjectDescLabel = 'roadmap.projectDescLabel';
  static const roadmapProjectDescHint = 'roadmap.projectDescHint';
  static const roadmapCreateButton = 'roadmap.createButton';

  // Strategy View
  static const strategyViewTitle = 'strategy.view.title';
  static const strategyViewSubtitle = 'strategy.view.subtitle';
  static const strategySettingsTooltip = 'strategy.settingsTooltip';
  static const strategyTabValidation = 'strategy.tab.validation';
  static const strategyTabLenses = 'strategy.tab.lenses';
  static const strategyTabAssumptions = 'strategy.tab.assumptions';
  static const strategyTabDecisions = 'strategy.tab.decisions';
  static const strategyTabStageGate = 'strategy.tab.stageGate';
  static const strategyTab12WyLoop = 'strategy.tab.12wyLoop';
  static const strategyTabWeeklyReview = 'strategy.tab.weeklyReview';

  // OKRs View
  static const okrsTitle = 'okrs.title';
  static const okrsSubtitle = 'okrs.subtitle';
  static const okrsCycleButton = 'okrs.cycleButton';
  static const okrsAiGenerating = 'okrs.aiGenerating';
  static const okrsAiGenerate = 'okrs.aiGenerate';
  static const okrsAddObjective = 'okrs.addObjective';

  // 12-Week Year View
  static const twelveWyTitle = 'twelveWy.title';
  static const twelveWySubtitle = 'twelveWy.subtitle';
  static const twelveWyTransitionCelebration = 'twelveWy.transitionCelebration';
  static const twelveWyCompileV10 = 'twelveWy.compileV10';
  static const twelveWyGovernance = 'twelveWy.governance';
  static const twelveWyAddWeek = 'twelveWy.addWeek';
  // 12WY Modals
  static const twelveWyCreatePlanTitle = 'twelveWy.modal.createPlan.title';
  static const twelveWyCreatePlanSubtitle = 'twelveWy.modal.createPlan.subtitle';
  static const twelveWyCreatePlanWeekNo = 'twelveWy.modal.createPlan.weekNo';
  static const twelveWyCreatePlanFocus = 'twelveWy.modal.createPlan.focus';
  static const twelveWyCreatePlanFocusHint = 'twelveWy.modal.createPlan.focusHint';
  static const twelveWyCreatePlanCancel = 'twelveWy.modal.createPlan.cancel';
  static const twelveWyCreatePlanSubmit = 'twelveWy.modal.createPlan.submit';
  static const twelveWyEditMissionTitle = 'twelveWy.modal.editMission.title';
  static const twelveWyEditMissionSubtitle = 'twelveWy.modal.editMission.subtitle';
  static const twelveWyEditMissionLabel = 'twelveWy.modal.editMission.label';
  static const twelveWyEditMissionHint = 'twelveWy.modal.editMission.hint';
  static const twelveWyEditMissionOutcome = 'twelveWy.modal.editMission.outcome';
  static const twelveWyEditMissionCancel = 'twelveWy.modal.editMission.cancel';
  static const twelveWyEditMissionSave = 'twelveWy.modal.editMission.save';
  static const twelveWyCompileTitle = 'twelveWy.modal.compile.title';
  static const twelveWyCompileSubtitle = 'twelveWy.modal.compile.subtitle';
  static const twelveWyCompileNoCycle = 'twelveWy.modal.compile.noCycle';
  static const twelveWyCompileNote = 'twelveWy.modal.compile.note';
  static const twelveWyCompileStatCommit = 'twelveWy.modal.compile.stat.commit';
  static const twelveWyCompileStatTasks = 'twelveWy.modal.compile.stat.tasks';
  static const twelveWyCompileStatMilestone = 'twelveWy.modal.compile.stat.milestone';
  static const twelveWyCompileCancel = 'twelveWy.modal.compile.cancel';
  static const twelveWyCompileStart = 'twelveWy.modal.compile.start';
  static const twelveWyReviewTitle = 'twelveWy.modal.review.title';
  static const twelveWyReviewSubtitle = 'twelveWy.modal.review.subtitle';
  static const twelveWyReviewExecScore = 'twelveWy.modal.review.execScore';
  static const twelveWyReviewOutcomeScore = 'twelveWy.modal.review.outcomeScore';
  static const twelveWyReviewRecommend = 'twelveWy.modal.review.recommend';
  static const twelveWyReviewEvidence = 'twelveWy.modal.review.evidence';
  static const twelveWyReviewEvidenceHint = 'twelveWy.modal.review.evidenceHint';
  static const twelveWyReviewSummary = 'twelveWy.modal.review.summary';
  static const twelveWyReviewSummaryHint = 'twelveWy.modal.review.summaryHint';
  static const twelveWyReviewCancel = 'twelveWy.modal.review.cancel';
  static const twelveWyReviewSave = 'twelveWy.modal.review.save';
  static const twelveWyTransitionTitle = 'twelveWy.modal.transition.title';
  static const twelveWyTransitionSubtitle = 'twelveWy.modal.transition.subtitle';
  static const twelveWyTransitionNoCycle = 'twelveWy.modal.transition.noCycle';
  static const twelveWyTransitionCelebTitle = 'twelveWy.modal.transition.celebTitle';
  static const twelveWyTransitionCelebTitleDefault = 'twelveWy.modal.transition.celebTitleDefault';
  static const twelveWyTransitionReadiness = 'twelveWy.modal.transition.readiness';
  static const twelveWyTransitionExecScore = 'twelveWy.modal.transition.execScore';
  static const twelveWyTransitionOkrScore = 'twelveWy.modal.transition.okrScore';
  static const twelveWyTransitionLearnings = 'twelveWy.modal.transition.learnings';
  static const twelveWyTransitionLearningsHint = 'twelveWy.modal.transition.learningsHint';
  static const twelveWyTransitionRewards = 'twelveWy.modal.transition.rewards';
  static const twelveWyTransitionRewardsDefault = 'twelveWy.modal.transition.rewardsDefault';
  static const twelveWyTransitionCancel = 'twelveWy.modal.transition.cancel';
  static const twelveWyTransitionFinalize = 'twelveWy.modal.transition.finalize';
  // 12WY Empty state
  static const twelveWyEmptyTitle = 'twelveWy.empty.title';
  static const twelveWyEmptyDesc = 'twelveWy.empty.desc';
  static const twelveWyEmptyCreate = 'twelveWy.empty.create';
  // Service error messages
  static const errNoWorkspace = 'err.noWorkspace';
  static const errRequestFailed = 'err.requestFailed';
  static const errNotFound = 'err.notFound';
  static const errBadFormat = 'err.badFormat';
  static const errParseFailed = 'err.parseFailed';

  // Resources & Funding View
  static const fundingTitle = 'funding.title';
  static const fundingSubtitle = 'funding.subtitle';
  static const fundingNoProjects = 'funding.noProjects';
  static const fundingSubNavMatches = 'funding.subNav.matches';
  static const fundingSubNavBenefits = 'funding.subNav.benefits';
  static const fundingSubNavWatchlist = 'funding.subNav.watchlist';
  static const fundingRunMatch = 'funding.runMatch';
  static const fundingProjectFallback = 'funding.projectFallback';
  // Matches tab - alerts & metrics
  static const fundingAlertsTitle = 'funding.alerts.title';
  static const fundingMetricReadiness = 'funding.metric.readiness';
  static const fundingMetricReadinessReady = 'funding.metric.readiness.ready';
  static const fundingMetricReadinessNeeds = 'funding.metric.readiness.needs';
  static const fundingMetricTech = 'funding.metric.tech';
  static const fundingMetricCategory = 'funding.metric.category';
  static const fundingMetricStageLabel = 'funding.metric.stageLabel';
  // Matches tab - sections
  static const fundingSectionMatches = 'funding.section.matches';
  static const fundingSectionMatchesEmpty = 'funding.section.matches.empty';
  static const fundingSectionMissing = 'funding.section.missing';
  static const fundingSectionMissingEmpty = 'funding.section.missing.empty';
  static const fundingProgramsFallback = 'funding.programs.fallback';
  static const fundingAuthorityFallback = 'funding.authority.fallback';
  static const fundingStatusEligible = 'funding.status.eligible';
  static const fundingStatusIneligible = 'funding.status.ineligible';
  static const fundingStatusPotential = 'funding.status.potential';
  static const fundingPillMatchScore = 'funding.pill.matchScore';
  static const fundingPillReadiness = 'funding.pill.readiness';
  static const fundingEvidenceFallback = 'funding.evidence.fallback';
  static const fundingAddTo12wy = 'funding.addTo12wy';
  static const fundingStackTitle = 'funding.stack.title';
  static const fundingStackDesc = 'funding.stack.desc';
  static const fundingCompanyStartup = 'funding.company.startup';
  static const fundingCompanyEnterprise = 'funding.company.enterprise';
  static const fundingMvpLabel = 'funding.mvp.label';
  // Catalog tab
  static const fundingCatalogTitle = 'funding.catalog.title';
  static const fundingCatalogCount = 'funding.catalog.count';
  static const fundingCatalogEmpty = 'funding.catalog.empty';
  static const fundingBenefitFallback = 'funding.benefit.fallback';
  static const fundingCatalogVerifiedActive = 'funding.catalog.verifiedActive';
  static const fundingCatalogVerifiedEnacted = 'funding.catalog.verifiedEnacted';
  static const fundingCatalogPending = 'funding.catalog.pending';
  static const fundingCatalogVerify = 'funding.catalog.verify';
  static const fundingItemsUnit = 'funding.items.unit';
  static const fundingProgramsUnit = 'funding.programs.unit';
  static const fundingCatalogDisclaimer = 'funding.catalog.disclaimer';
  static const fundingCatalogMaxFunding = 'funding.catalog.maxFunding';
  static const fundingCatalogClaimsLabel = 'funding.catalog.claimsLabel';
  static const fundingCatalogSourceLabel = 'funding.catalog.sourceLabel';
  static const fundingCatalogFounderVerify = 'funding.catalog.founderVerify';
  // Watchlist tab
  static const fundingWatchlistDisclaimer = 'funding.watchlist.disclaimer';
  static const fundingWatchlistEmpty = 'funding.watchlist.empty';
  static const fundingWatchlistBadge = 'funding.watchlist.badge';
  static const fundingWatchlistDraftFallback = 'funding.watchlist.draftFallback';
  // Verification modal
  static const fundingVerifyTitle = 'funding.verify.title';
  static const fundingVerifyRefSource = 'funding.verify.refSource';
  static const fundingVerifyClaimsSection = 'funding.verify.claimsSection';
  static const fundingVerifyOfficialInfo = 'funding.verify.officialInfo';
  static const fundingVerifyPortalLink = 'funding.verify.portalLink';
  static const fundingVerifyIssuingAuthority = 'funding.verify.issuingAuthority';
  static const fundingVerifyNotes = 'funding.verify.notes';
  static const fundingVerifyNotesHint = 'funding.verify.notesHint';
  static const fundingVerifyResult = 'funding.verify.result';
  static const fundingVerifyStatusActive = 'funding.verify.status.active';
  static const fundingVerifyStatusEnacted = 'funding.verify.status.enacted';
  static const fundingVerifyStatusInvalid = 'funding.verify.status.invalid';
  static const fundingVerifyCancel = 'funding.verify.cancel';
  static const fundingVerifySave = 'funding.verify.save';
  static const fundingVerifySuccessTitle = 'funding.verify.success.title';
  static const fundingVerifyErrorTitle = 'funding.verify.error.title';
  static const fundingProgramFallback = 'funding.program.fallback';

  // Template Library View
  static const templateLibTitle = 'templateLib.title';
  static const templateLibSubtitle = 'templateLib.subtitle';
  static const templateLibProvisionDefault = 'templateLib.provisionDefault';
  static const templateLibEmpty = 'templateLib.empty';

  // Tasks View
  static const tasksTitle = 'tasks.title';
  static const tasksSubtitle = 'tasks.subtitle';
  static const tasksAddTooltip = 'tasks.addTooltip';
  static const tasksTabOverview = 'tasks.tabOverview';
  static const tasksTabKanban = 'tasks.tabKanban';

  // Approvals View
  static const approvalsSubtitle = 'approvals.subtitle';
  static const approvalsTabPending = 'approvals.tabPending';
  static const approvalsTabHistory = 'approvals.tabHistory';

  // Agents View
  static const agentsSubtitle = 'agents.subtitle';
  static const agentsTabDirectory = 'agents.tabDirectory';
  static const agentsTabOrgChart = 'agents.tabOrgChart';
  static const agentsTabRuns = 'agents.tabRuns';
  static const agentsWorkProductsTooltip = 'agents.workProductsTooltip';
  static const agentsAdrTooltip = 'agents.adrTooltip';

  // Vault View
  static const vaultNewDoc = 'vault.newDoc';
  static const vaultEmpty = 'vault.empty';
  static const vaultCreateUpload = 'vault.createUpload';
  // Vault document states
  static const vaultStateDraft = 'vault.state.draft';
  static const vaultStateQueued = 'vault.state.queued';
  static const vaultStateValidating = 'vault.state.validating';
  static const vaultStateConverting = 'vault.state.converting';
  static const vaultStateReviewPending = 'vault.state.reviewPending';
  static const vaultStatePublished = 'vault.state.published';
  static const vaultStateRejected = 'vault.state.rejected';
  static const vaultStateFailed = 'vault.state.failed';
  static const vaultStateArchived = 'vault.state.archived';
  static const vaultStatePurgePending = 'vault.state.purgePending';
  static const vaultStatePurged = 'vault.state.purged';
  static const vaultStateUnknown = 'vault.state.unknown';

  // Marketing View
  static const marketingTitle = 'marketing.title';
  static const marketingSubtitle = 'marketing.subtitle';

  // Sales View
  static const salesTitle = 'sales.title';
  static const salesSubtitle = 'sales.subtitle';
  static const salesReloadTooltip = 'sales.reloadTooltip';

  // Finance View
  static const financeTitle = 'finance.title';
  static const financeSubtitle = 'finance.subtitle';
  static const financeRegimeTransition = 'finance.regimeTransition';
  static const financeRecordTransaction = 'finance.recordTransaction';

  // Legal View
  static const legalTitle = 'legal.title';
  static const legalSubtitle = 'legal.subtitle';
  static const legalReviewButton = 'legal.reviewButton';

  // Workflows View
  static const workflowsTitle = 'workflows.title';
  static const workflowsSubtitle = 'workflows.subtitle';

  // Organization View
  static const orgTitle = 'org.title';
  static const orgSubtitle = 'org.subtitle';
  static const orgHireAiButton = 'org.hireAiButton';

  // Workspace Runtime & Strategy Extensions
  static const workInspectorTitle = 'workInspector.title';
  static const workInspectorSubtitle = 'workInspector.subtitle';
  static const blockedWorkTitle = 'blockedWork.title';
  static const blockedWorkSubtitle = 'blockedWork.subtitle';
  static const needsYouTitle = 'needsYou.title';
  static const needsYouSubtitle = 'needsYou.subtitle';

  static const strategyFoundationTitle = 'strategyFoundation.title';
  static const strategyFoundationSubtitle = 'strategyFoundation.subtitle';
  static const strategyFoundationCreate = 'strategyFoundation.create';

  static const projectRoadmapAdvancedTitle = 'projectRoadmapAdvanced.title';
  static const projectRoadmapAdvancedSubtitle = 'projectRoadmapAdvanced.subtitle';
  static const projectRoadmapAdvancedBack = 'projectRoadmapAdvanced.back';

  static const projectStageWorkspaceTitle = 'projectStageWorkspace.title';
  static const projectStageWorkspaceSubtitle = 'projectStageWorkspace.subtitle';
  static const projectStageWorkspaceBack = 'projectStageWorkspace.back';

  // Founder Trial Board (R1)
  static const ftSectionStart = 'founderTrial.section.start';
  static const ftSectionThisWeek = 'founderTrial.section.thisWeek';
  static const ftSectionEvidence = 'founderTrial.section.evidence';
  static const ftSectionCash = 'founderTrial.section.cash';
  static const ftSectionDecision = 'founderTrial.section.decision';
  static const ftCycleUnset = 'founderTrial.cycle.unset';
  static const ftCycleSummary = 'founderTrial.cycle.summary';
  static const ftCycleDurationHint = 'founderTrial.cycle.durationHint';
  static const ftAssumptionsTitle = 'founderTrial.assumptions.title';
  static const ftExperimentsTitle = 'founderTrial.experiments.title';
  static const ftExperimentUnlinked = 'founderTrial.experiments.unlinked';
  static const ftEvidenceCounts = 'founderTrial.evidence.counts';
  static const ftEvidenceUnlinkedNote = 'founderTrial.evidence.unlinkedNote';
  static const ftProjectBudgetTitle = 'founderTrial.cash.projectBudget';
  static const ftWorkspaceLiquidityTitle = 'founderTrial.cash.workspaceLiquidity';
  static const ftWorkspaceLiquidityNote = 'founderTrial.cash.workspaceLiquidityNote';
  static const ftBriefTitle = 'founderTrial.brief.title';
  static const ftNextReviewFocus = 'founderTrial.brief.nextReviewFocus';
  static const ftDecisionsEmpty = 'founderTrial.decision.empty';
  static const ftStrategicAnalysis = 'founderTrial.strategicAnalysis.title';
  static const ftRetry = 'founderTrial.retry';
  static const ftNoProject = 'founderTrial.noProject';

  // COSA Automation MVP
  static const automationLibraryTitle = 'automation.library.title';
  static const automationLibrarySubtitle = 'automation.library.subtitle';
  static const automationInspectorTitle = 'automation.inspector.title';
  static const automationInspectorSubtitle = 'automation.inspector.subtitle';
  static const automationConfigure = 'automation.action.configure';
  static const automationConfigureTitle = 'automation.configure.title';
  static const automationRunNow = 'automation.action.runNow';
  static const automationSuspend = 'automation.action.suspend';
  static const automationCancelRun = 'automation.action.cancelRun';
  static const automationSaveConfiguration = 'automation.action.saveConfiguration';
  static const automationTriggerKind = 'automation.field.triggerKind';
  static const automationFieldRequired = 'automation.field.required';
  static const automationCardReady = 'automation.card.ready';
  static const automationCardSetupRequired = 'automation.card.setupRequired';
  static const automationCardSuspended = 'automation.card.suspended';
  static const automationCardUnavailable = 'automation.card.unavailable';
  static const automationCardForbidden = 'automation.card.forbidden';
  static const automationStateForbidden = 'automation.state.forbidden';
  static const automationStateUnavailable = 'automation.state.unavailable';
  static const automationStateFailed = 'automation.state.failed';
  static const automationStateEmpty = 'automation.state.empty';
  static const automationPinnedRevision = 'automation.inspector.pinnedRevision';
  static const automationRunState = 'automation.inspector.runState';
  static const automationSourceHealth = 'automation.inspector.sourceHealth';
  static const automationFailureReason = 'automation.inspector.failureReason';
  static const automationTimeline = 'automation.inspector.timeline';
  static const automationEvidence = 'automation.inspector.evidence';
  static const navAutomation = 'nav.item.automation';

  static const List<String> required = [
    appTitle,
    automationLibraryTitle,
    automationInspectorTitle,
    automationStateForbidden,
    automationStateUnavailable,
    navAutomation,
    profileLanguageTitle,
    profileLanguageVi,
    profileLanguageEn,
    profileLogout,
    chatNewConversation,
    chatComposerHint,
    moduleFinance,
    moduleLegal,
    moduleCrm,
    moduleTasks,
    settingsTitle,
    settingsSubtitle,
    settingsModulesTitle,
    settingsModulesSubtitle,
    settingsModuleUserVisible,
    settingsModuleWorkspaceEnabled,
    settingsModuleUpdateError,
    authIdentifierLabel,
    authPasswordLabel,
    authLoginButton,
    regStep1Title,
    regFullNameLabel,
    regEmailLabel,
    regContinue,
    projectSetupTitle,
    projectSetupSubtitle,
    projectSetupNameLabel,
    projectSetupDescLabel,
    projectSetupSubmitButton,
    projectSetupSubmitting,
    projectSetupCancelButton,
    projectSetupLogoutButton,
    projectSetupSwitchWorkspaceButton,
    projectSetupNameRequired,
    projectSetupFailed,
    projectKickoffTitle,
    projectKickoffSubtitle,
    projectKickoffAdvancedRoadmap,
    projectKickoffBack,
    projectKickoffSettingsTooltip,
    projectKickoffStepTab1,
    projectKickoffStepTab2,
    projectKickoffStepTab3,
    projectKickoffStep1Title,
    projectKickoffTargetCustomerLabel,
    projectKickoffTargetCustomerHint,
    projectKickoffProblemStatementLabel,
    projectKickoffProblemStatementHint,
    projectKickoffEvidenceLabel,
    projectKickoffEvidenceNone,
    projectKickoffEvidenceOneToFour,
    projectKickoffEvidenceFivePlus,
    projectKickoffEvidencePrototypeOrRevenue,
    projectKickoffSaving,
    projectKickoffContinue,
    projectKickoffStep2Title,
    projectKickoffProposalP0,
    projectKickoffProposalP1,
    projectKickoffGoalP0,
    projectKickoffGoalP1,
    projectKickoffSelectStageLabel,
    projectKickoffStageP0Title,
    projectKickoffStageP0Subtitle,
    projectKickoffStageP1Title,
    projectKickoffStageP1Subtitle,
    projectKickoffP1Warning,
    projectKickoffCycleDurationLabel,
    projectKickoffWeeksCount,
    projectKickoffCycleStartDateLabel,
    projectKickoffDefaultNextMonday,
    projectKickoffStep3Title,
    projectKickoffRegenerateAiTooltip,
    projectKickoffStep3Context,
    projectKickoffFirstWeekOutcomeLabel,
    projectKickoffFirstWeekOutcomeHint,
    projectKickoffFirstWeekOutcomeInputHint,
    projectKickoffFirstWeekActionsLabel,
    projectKickoffActionsCount,
    projectKickoffDeleteActionTooltip,
    projectKickoffNewActionHint,
    projectKickoffAddActionButton,
    projectKickoffWeeklyReviewDayLabel,
    projectKickoffReviewScheduleText,
    projectKickoffActivating,
    projectKickoffConfirmCycle,
    weekdayMonday,
    weekdayTuesday,
    weekdayWednesday,
    weekdayThursday,
    weekdayFriday,
    weekdaySaturday,
    weekdaySunday,
    companyScopeGlobal,
    companyScopeNarrow,
    hubPulseGoalsOnTrack,
    hubPulseActiveMissions,
    hubPulseNeedsDecision,
    hubPulseMajorRisks,
    hubCofounderDiscuss,
    hubCofounderDefaultFocus,
    hubCofounderFocusWithProject,
    hubCofounderFocusNoProject,
    hubCurrentCycleBadge,
    hubReviewScheduleBadge,
    hubFirstWeekOutcomePrefix,
    hubTop3Title,
    hubTop3Empty,
    hubFirstWeekActionsTitle,
    hubActionNoTimeSet,
    hubActionCategoryDecision,
    hubActionCategoryExperiment,
    hubActionCategoryAction,
    hubWaitingEmpty,
    hubWaitingTitle,
    hubWaitingItemsCount,
    hubDecisionMakeDecision,
    hubApprovalDefaultTitle,
    hubApprovalReject,
    hubApprovalApprove,
    hubApprovalRejectDialogTitle,
    hubApprovalRejectReasonHint,
    hubDecisionModalHeader,
    hubDecisionModalAiRecHeader,
    hubDecisionModalAiRecDefaultReason,
    hubDecisionModalSelectOption,
    hubDecisionModalFinancialImpact,
    hubDecisionModalNotesHint,
    hubDecisionModalClose,
    hubDecisionModalConfirm,
    hubProposedPlanTitle,
    hubProposedPlanItemsCount,
    hubProposedPlanAcceptAll,
    hubProposedPlanDismiss,
    hubProposedPlanMissingEvidence,
    hubProposedPlanDropItemTooltip,
    autonomyClassAuto,
    autonomyClassNeedsApproval,
    autonomyClassFounderOnly,
    hubYourTasksTitle,
    hubTaskBlocked,
    hubTaskNeedsYou,
    hubTabCommandCenter,
    hubTabCommandCenterShort,
    hubTabWorkforce,
    hubTabWorkforceShort,
    hubPrematureMoreAlerts,
    hubUpdateFailedToast,
    sidebarDeveloperMode,
    sidebarLogout,
    sidebarBackToHub,
    commonRefresh,
    commonRetry,
    roadmapProjectsTitle,
    roadmapProjectsSubtitle,
    roadmapManageTemplates,
    roadmapNewProject,
    roadmapNoProjects,
    roadmapNoProjectsDesc,
    roadmapCreateNewProject,
    roadmapWeeksCount,
    roadmapFromDate,
    roadmapElapsedDays,
    roadmapOpenMarketingTooltip,
    roadmapViewRoadmapTooltip,
    roadmapAiGenerateTooltip,
    roadmapCreateDialogTitle,
    roadmapCreateDialogSubtitle,
    roadmapProjectNameLabel,
    roadmapProjectNameHint,
    roadmapProjectDescLabel,
    roadmapProjectDescHint,
    roadmapCreateButton,
    strategyViewTitle,
    strategyViewSubtitle,
    strategySettingsTooltip,
    strategyTabValidation,
    strategyTabLenses,
    strategyTabAssumptions,
    strategyTabDecisions,
    strategyTabStageGate,
    strategyTab12WyLoop,
    strategyTabWeeklyReview,
    okrsTitle,
    okrsSubtitle,
    okrsCycleButton,
    okrsAiGenerating,
    okrsAiGenerate,
    okrsAddObjective,
    twelveWyTitle,
    twelveWySubtitle,
    twelveWyTransitionCelebration,
    twelveWyCompileV10,
    twelveWyGovernance,
    twelveWyAddWeek,
    fundingTitle,
    fundingSubtitle,
    fundingNoProjects,
    templateLibTitle,
    templateLibSubtitle,
    templateLibProvisionDefault,
    templateLibEmpty,
    tasksTitle,
    tasksSubtitle,
    tasksAddTooltip,
    tasksTabOverview,
    tasksTabKanban,
    approvalsSubtitle,
    approvalsTabPending,
    approvalsTabHistory,
    agentsSubtitle,
    agentsTabDirectory,
    agentsTabOrgChart,
    agentsTabRuns,
    agentsWorkProductsTooltip,
    agentsAdrTooltip,
    vaultNewDoc,
    vaultEmpty,
    vaultCreateUpload,
    marketingTitle,
    marketingSubtitle,
    salesTitle,
    salesSubtitle,
    salesReloadTooltip,
    financeTitle,
    financeSubtitle,
    financeRegimeTransition,
    financeRecordTransaction,
    legalTitle,
    legalSubtitle,
    legalReviewButton,
    workflowsTitle,
    workflowsSubtitle,
    orgTitle,
    orgSubtitle,
    orgHireAiButton,
    workInspectorTitle,
    workInspectorSubtitle,
    blockedWorkTitle,
    blockedWorkSubtitle,
    needsYouTitle,
    needsYouSubtitle,
    strategyFoundationTitle,
    strategyFoundationSubtitle,
    strategyFoundationCreate,
    projectRoadmapAdvancedTitle,
    projectRoadmapAdvancedSubtitle,
    projectRoadmapAdvancedBack,
    projectStageWorkspaceTitle,
    projectStageWorkspaceSubtitle,
    projectStageWorkspaceBack,
  ];
}

class AppTranslations extends Translations {
  @override
  Map<String, Map<String, String>> get keys => {
        'vi_VN': vi,
        'en_US': en,
      };

  static final Map<String, String> vi = {
    ...viCommon,
    ...viAuth,
    ...viChat,
    ...viSettings,
    ...viStrategy,
    ...viTasks,
    ...viAutomation,
  };

  static final Map<String, String> en = {
    ...enCommon,
    ...enAuth,
    ...enChat,
    ...enSettings,
    ...enStrategy,
    ...enTasks,
    ...enAutomation,
  };
}
