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

  static const List<String> required = [
    appTitle,
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
  };

  static final Map<String, String> en = {
    ...enCommon,
    ...enAuth,
    ...enChat,
    ...enSettings,
    ...enStrategy,
  };
}
