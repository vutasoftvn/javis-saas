import 'package:get/get.dart';

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
  ];
}

class AppTranslations extends Translations {
  @override
  Map<String, Map<String, String>> get keys => {
        'vi_VN': vi,
        'en_US': en,
      };

  static const Map<String, String> vi = {
    // App
    L10nKey.appTitle: 'COSA - Hệ điều hành doanh nghiệp AI',

    // Navigation Groups
    L10nKey.navGroupConversation: 'Hội thoại & Trung tâm',
    L10nKey.navGroupCycle: 'Chu kỳ & Chiến lược',
    L10nKey.navGroupOperations: 'Công việc & Vận hành',
    L10nKey.navGroupAi: 'Đội ngũ AI & Nghiệp vụ',
    L10nKey.navGroupFinanceVault: 'Tài chính & Tri thức',
    L10nKey.navGroupOrganization: 'Tổ chức & Cài đặt',
    L10nKey.navGroupExperimental: 'Tính năng thử nghiệm',

    // Navigation Items
    L10nKey.navCommandCenter: 'COSA Command Center',
    L10nKey.navStrategy: 'Chiến lược',
    L10nKey.navProjects: 'Dự án',
    L10nKey.navOkrs: 'OKRs',
    L10nKey.navTwelveWy: 'Kế hoạch 12WY',
    L10nKey.navFunding: 'Nguồn lực & Tài trợ',
    L10nKey.navTasks: 'Nhiệm vụ',
    L10nKey.navApprovals: 'Phê duyệt',
    L10nKey.navNeedsYou: 'Cần bạn xử lý',
    L10nKey.navBlockedWork: 'Công việc tắc nghẽn',
    L10nKey.navWorkInspector: 'Giám sát công việc',
    L10nKey.navAiAgents: 'Đội ngũ AI Agents',
    L10nKey.navLegal: 'Pháp lý',
    L10nKey.navMarketing: 'Marketing & Lead Gen',
    L10nKey.navCrm: 'Bán hàng & CRM',
    L10nKey.navSkillRegistry: 'Kỹ năng AI (Skill Registry)',
    L10nKey.navFinance: 'Tài chính',
    L10nKey.navVault: 'Kho tri thức',
    L10nKey.navOrgChart: 'Sơ đồ tổ chức',
    L10nKey.navWorkflows: 'Quy trình',
    L10nKey.navTemplates: 'Quản trị Template',
    L10nKey.navSettings: 'Cài đặt',
    L10nKey.navAdvancedWorkflows: 'Quy trình nâng cao',
    L10nKey.navAdvancedOrgChart: 'Sơ đồ tổ chức chi tiết',

    // Modules
    L10nKey.moduleFinance: 'Tài chính',
    L10nKey.moduleLegal: 'Pháp lý',
    L10nKey.moduleCrm: 'Khách hàng (CRM)',
    L10nKey.moduleTasks: 'Nhiệm vụ',

    // Chat UI
    L10nKey.chatNewConversation: 'Cuộc trò chuyện mới',
    L10nKey.chatHistory: 'Lịch sử trò chuyện',
    L10nKey.chatNoConversations: 'Chưa có cuộc trò chuyện nào',
    L10nKey.chatStartNew: 'Bắt đầu cuộc trò chuyện mới',
    L10nKey.chatComposerHint: 'Nhập tin nhắn hoặc hỏi bất cứ điều gì...',
    L10nKey.chatReconnecting: 'Đang kết nối lại...',
    L10nKey.chatAgentOsTitle: 'AgentOS Chat',
    L10nKey.chatAdvisoryDomain: 'Trợ lý Doanh nghiệp',

    // Profile UI
    L10nKey.profileTitle: 'Hồ sơ cá nhân',
    L10nKey.profileLanguageTitle: 'Ngôn ngữ',
    L10nKey.profileLanguageVi: 'Tiếng Việt',
    L10nKey.profileLanguageEn: 'English',
    L10nKey.profileUnnamed: 'Chưa đặt tên',
    L10nKey.profileEmail: 'Email',
    L10nKey.profileFullName: 'Họ và tên',
    L10nKey.profileSaveName: 'Lưu tên',
    L10nKey.profilePhone: 'Số điện thoại',
    L10nKey.profileNoPhone: 'Chưa cập nhật số điện thoại',
    L10nKey.profileSavePhone: 'Lưu số điện thoại',
    L10nKey.profileLogout: 'Đăng xuất',

    // Auth UI
    L10nKey.authIdentifierLabel: 'Số điện thoại hoặc Email',
    L10nKey.authIdentifierHint: 'Nhập SĐT hoặc Email',
    L10nKey.authPasswordLabel: 'Mật khẩu',
    L10nKey.authRememberMe: 'Ghi nhớ tài khoản này',
    L10nKey.authLoginButton: 'Đăng Nhập',
    L10nKey.authNoAccount: 'Chưa có tài khoản?',
    L10nKey.authCreateAccount: 'Tạo tài khoản mới',
    L10nKey.authLanguageSwitchTooltip: 'Chuyển đổi ngôn ngữ',

    // Register UI
    L10nKey.regStep1Title: 'Tạo Tài Khoản Mới',
    L10nKey.regStep2Title: 'Thiết Lập Công Ty',
    L10nKey.regStep1Subtitle: 'Khởi tạo tài khoản danh tính COSA Platform',
    L10nKey.regStep2Subtitle: 'Tạo hoặc tham gia công ty để đồng bộ dữ liệu Brain về COSA Local',
    L10nKey.regStepAccount: 'Tài khoản',
    L10nKey.regStepCompany: 'Công ty',
    L10nKey.regFullNameLabel: 'Họ và tên',
    L10nKey.regEmailLabel: 'Email',
    L10nKey.regEmailHint: 'Ví dụ: ban@congty.com',
    L10nKey.regPasswordLabel: 'Mật khẩu (8–128 ký tự)',
    L10nKey.regConfirmPasswordLabel: 'Xác nhận mật khẩu',
    L10nKey.regCreatingAccount: 'Đang khởi tạo tài khoản...',
    L10nKey.regContinue: 'Tiếp tục',
    L10nKey.regTabCreateCompany: 'Tạo mới',
    L10nKey.regTabJoinCompany: 'Tham gia',
    L10nKey.regInvitationTokenLabel: 'Mã lời mời workspace',
    L10nKey.regInvitationTokenHint: 'Dán mã lời mời được gửi cho bạn qua email',
    L10nKey.regInvitationTokenHelper: 'Dán mã lời mời do founder/admin của workspace gửi cho bạn qua email.',
    L10nKey.regCompanyNameLabel: 'Tên công ty / Tổ chức',
    L10nKey.regCompanyNameHint: 'Ví dụ: VutaSoft, Acme Corp',
    L10nKey.regCompanyNameHelper: 'Bạn sẽ là Founder sở hữu công ty này.',
    L10nKey.regInitializingBrain: 'Đang khởi tạo Brain...',
    L10nKey.regInitialize: 'Khởi tạo',
    L10nKey.regBackToStep1: 'Quay lại bước 1',
    L10nKey.regAlreadyHaveAccount: 'Đã có tài khoản?',
    L10nKey.regLoginNow: 'Đăng nhập ngay',

    // Settings UI
    L10nKey.settingsTitle: 'Cài đặt hệ thống',
    L10nKey.settingsSubtitle: 'Cấu hình tài khoản, AI Gateway & tối ưu hóa chi phí',
    L10nKey.settingsModulesTitle: 'Mô-đun tùy chọn',
    L10nKey.settingsModulesSubtitle: 'Quản lý hiển thị và kích hoạt các mô-đun nghiệp vụ',
    L10nKey.settingsModuleUserVisible: 'Hiển thị trên menu của tôi',
    L10nKey.settingsModuleWorkspaceEnabled: 'Kích hoạt cho toàn workspace',
    L10nKey.settingsModuleUpdateError: 'Cập nhật trạng thái mô-đun thất bại',

    // Common
    L10nKey.commonAdd: 'Thêm',
    L10nKey.commonEdit: 'Sửa',
    L10nKey.commonSave: 'Lưu',
    L10nKey.commonCancel: 'Hủy',
    L10nKey.commonLoading: 'Đang tải...',
    L10nKey.commonError: 'Lỗi',
    // Hologram Hub UI
    L10nKey.hubSubtitle: 'Hệ điều hành doanh nghiệp AI',
    L10nKey.hubSwitchModule: 'Chuyển module',
    L10nKey.hubManageDashboard: 'Quản trị Dashboard',
    L10nKey.hubRefreshData: 'Làm mới dữ liệu',
    L10nKey.hubMyProfile: 'Hồ sơ của tôi',
    L10nKey.hubContinueSetup: 'Tiếp tục thiết lập',
    L10nKey.hubSetupIncompleteTitle: 'Hoàn tất thiết lập vòng khởi đầu',
    L10nKey.hubSetupIncompleteDesc: 'Dự án của bạn chưa hoàn thành 3 bước thiết lập mục tiêu và hành động tuần đầu.',
    L10nKey.hubPlanningInProgress: 'Đang lập...',
    L10nKey.hubAskAiPlan: 'Nhờ AI lập kế hoạch',
    L10nKey.hubCreateNewProject: 'Khởi tạo dự án mới',
    L10nKey.hubProjectNameLabel: 'Tên dự án *',
    L10nKey.hubProjectNameHint: 'Ví dụ: Nền tảng B2B SaaS cho Doanh nghiệp',
    L10nKey.hubProjectDescLabel: 'Mô tả bài toán / JTBD',
    L10nKey.hubProjectDescHint: 'Mô tả ngắn gọn ý tưởng, vấn đề cần giải quyết...',
    L10nKey.hubEnterProjectNameError: 'Vui lòng nhập tên dự án',
    L10nKey.hubMissingInfoTitle: 'Thiếu thông tin',
    L10nKey.hubCreateProjectAction: 'Khởi tạo dự án',
    L10nKey.hubSweepEnabled: 'AI tự chạy việc trong quyền hạn',
    L10nKey.hubSweepDisabled: 'Đã tạm dừng AI tự chạy việc',

    // Strategy Lenses: Hub Modal
    L10nKey.strategyHubTitle: 'Khung 4 Lăng Kính Chiến Lược (Strategy Lenses Hub)',
    L10nKey.strategyHubSubtitle: 'Phân tích định hướng chuẩn COSA: PESTEL -> SWOT -> TOWS -> Balanced Scorecard',
    L10nKey.strategyTabSwot: 'SWOT Có Bằng Chứng (@count)',
    L10nKey.strategyTabBsc: 'Balanced Scorecard (@count)',
    L10nKey.strategyTabBscLocked: 'Balanced Scorecard (Khóa)',

    // Strategy Lenses: PESTEL
    L10nKey.pestelDimPolitical: 'Chính trị (Political)',
    L10nKey.pestelDimEconomic: 'Kinh tế (Economic)',
    L10nKey.pestelDimSocial: 'Xã hội (Social)',
    L10nKey.pestelDimTechnological: 'Công nghệ (Technological)',
    L10nKey.pestelDimEnvironmental: 'Môi trường (Environmental)',
    L10nKey.pestelDimLegal: 'Pháp lý (Legal)',
    L10nKey.pestelCatchSignal: 'Bắt Tín Hiệu Vĩ Mô PESTEL',
    L10nKey.pestelMacroDimLabel: 'Chiều vĩ mô',
    L10nKey.pestelSignalTitleLabel: 'Tiêu đề tín hiệu (*)',
    L10nKey.pestelSignalTitleHint: 'Ví dụ: Lãi suất tăng, AI Small Models phát triển...',
    L10nKey.pestelContextLabel: 'Mô tả & Bối cảnh diễn biến',
    L10nKey.pestelSaveSignal: 'Lưu Tín Hiệu',
    L10nKey.pestelBannerDesc: 'Lăng kính PESTEL quét 6 chiều vĩ mô để phát hiện cơ hội và rủi ro. Bạn có thể 1-click chuyển đổi tín hiệu thành Giả định cần kiểm chứng (Hypothesis).',
    L10nKey.pestelAddTooltip: 'Thêm tín hiệu @dim',
    L10nKey.pestelEmpty: 'Chưa có tín hiệu',
    L10nKey.pestelHypothesisCreated: 'Đã Tạo Giả Định',
    L10nKey.pestelGenerateHypothesis: 'Sinh Giả Định',

    // Strategy Lenses: SWOT
    L10nKey.swotTypeStrength: 'Điểm Mạnh (S)',
    L10nKey.swotTypeWeakness: 'Điểm Yếu (W)',
    L10nKey.swotTypeOpportunity: 'Cơ Hội (O)',
    L10nKey.swotTypeThreat: 'Thách Thức (T)',
    L10nKey.swotAddTitle: 'Thêm Yếu Tố SWOT',
    L10nKey.swotTypeLabel: 'Phân loại SWOT',
    L10nKey.swotContentLabel: 'Nội dung nhận định (*)',
    L10nKey.swotContentHint: 'Ví dụ: Tỷ lệ giữ chân khách hàng 92% nhờ tính năng Agentic AI...',
    L10nKey.swotSave: 'Lưu SWOT',
    L10nKey.swotHeader: 'Ma trận SWOT có Bằng Chứng: Điểm Mạnh/Yếu BẮT BUỘC gắn với dữ liệu thực tế (Evidence Refs) để loại bỏ thiên vị chủ quan.',
    L10nKey.swotAddTooltip: 'Thêm @type',
    L10nKey.swotEmpty: 'Chưa có nội dung',

    // Strategy Lenses: TOWS
    L10nKey.towsTypeSo: 'Chiến Lược SO (Tận Dụng Đột Phá)',
    L10nKey.towsTypeWo: 'Chiến Lược WO (Khắc Phục Nắm Bắt)',
    L10nKey.towsTypeSt: 'Chiến Lược ST (Dùng Mạnh Hóa Giải)',
    L10nKey.towsTypeWt: 'Chiến Lược WT (Phòng Thủ Sinh Tồn)',
    L10nKey.towsCreateTitle: 'Tạo Chiến Lược TOWS',
    L10nKey.towsPairLabel: 'Cặp ghép chiến lược TOWS',
    L10nKey.towsStrategyNameLabel: 'Tên chiến lược (*)',
    L10nKey.towsStrategyNameHint: 'Ví dụ: Ra mắt gói Starter AI giá thấp...',
    L10nKey.towsDescLabel: 'Mô tả cơ chế ghép cặp & Đánh đổi (Trade-offs)',
    L10nKey.towsSaveStrategy: 'Lưu Chiến Lược',
    L10nKey.towsEvalTitle: 'Đánh giá chiến lược: @title',
    L10nKey.towsImpactScore: 'Điểm tác động (1-5):',
    L10nKey.towsDifficultyScore: 'Độ khó / rào cản (1-5):',
    L10nKey.towsRatingExplanation: 'Giải thích xếp hạng',
    L10nKey.towsSaveEvaluation: 'Lưu đánh giá',
    L10nKey.towsSelectTitle: 'Chọn chiến lược: @title',
    L10nKey.towsSelectDesc: 'Chiến lược được chọn sẽ trở thành căn cứ xây dựng Kế hoạch Hành động (Initiative).',
    L10nKey.towsSelectReasonLabel: 'Lý do lựa chọn (*)',
    L10nKey.towsConfirmSelect: 'Xác nhận chọn',
    L10nKey.towsMatrixHeader: 'Ma trận TOWS: Ghép nối yếu tố bên trong và bên ngoài để ra quyết định chiến lược.',
    L10nKey.towsSelectionCount: '@count / @limit chiến lược đã chọn',
    L10nKey.towsAddTooltip: 'Thêm chiến lược @name',
    L10nKey.towsEmpty: 'Chưa có chiến lược',
    L10nKey.towsSelected: 'ĐÃ CHỌN',
    L10nKey.towsScoreBtn: 'Chấm điểm (1-5)',
    L10nKey.towsSelectBtn: 'Chọn',

    // Strategy Lenses: BSC
    L10nKey.bscPerspFinancial: 'Tài Chính (Financial)',
    L10nKey.bscPerspCustomer: 'Khách Hàng (Customer)',
    L10nKey.bscPerspInternal: 'Vận Hành Nội Bộ (Internal Operations)',
    L10nKey.bscPerspLearning: 'Năng Lực & Con Người (Learning & Growth)',
    L10nKey.bscTitle: 'Thẻ điểm Cân bằng BSC (Balanced Scorecard)',
    L10nKey.bscHeaderDesc: 'Thẻ điểm BSC phản ánh các Mục tiêu & Kết quả then chốt (OKRs) đã được phê duyệt và công bố.\nCác chỉ số sẽ tự động đồng bộ theo từng trụ cột khi OKR chu kỳ được xuất bản.',
    L10nKey.bscReadOnlyDesc: 'Thẻ điểm Balanced Scorecard (Chỉ xem): Tổng hợp các mục tiêu & chỉ số đo lường đã công bố trên 4 trụ cột chiến lược.',
    L10nKey.bscEmpty: 'Chưa có chỉ số xuất bản',
  };

  static const Map<String, String> en = {
    // App
    L10nKey.appTitle: 'COSA - AI Enterprise Operating System',

    // Navigation Groups
    L10nKey.navGroupConversation: 'Conversation & Center',
    L10nKey.navGroupCycle: 'Cycle & Strategy',
    L10nKey.navGroupOperations: 'Work & Operations',
    L10nKey.navGroupAi: 'AI Team & Business',
    L10nKey.navGroupFinanceVault: 'Finance & Knowledge',
    L10nKey.navGroupOrganization: 'Organization & Settings',
    L10nKey.navGroupExperimental: 'Experimental Features',

    // Navigation Items
    L10nKey.navCommandCenter: 'COSA Command Center',
    L10nKey.navStrategy: 'Strategy',
    L10nKey.navProjects: 'Projects',
    L10nKey.navOkrs: 'OKRs',
    L10nKey.navTwelveWy: '12-Week Year',
    L10nKey.navFunding: 'Resources & Funding',
    L10nKey.navTasks: 'Tasks',
    L10nKey.navApprovals: 'Approvals',
    L10nKey.navNeedsYou: 'Needs Your Attention',
    L10nKey.navBlockedWork: 'Blocked Work',
    L10nKey.navWorkInspector: 'Work Inspector',
    L10nKey.navAiAgents: 'AI Agents Team',
    L10nKey.navLegal: 'Legal & Contracts',
    L10nKey.navMarketing: 'Marketing & Lead Gen',
    L10nKey.navCrm: 'Sales & CRM',
    L10nKey.navSkillRegistry: 'AI Skill Registry',
    L10nKey.navFinance: 'Finance',
    L10nKey.navVault: 'Knowledge Vault',
    L10nKey.navOrgChart: 'Organization Chart',
    L10nKey.navWorkflows: 'Workflows',
    L10nKey.navTemplates: 'Template Management',
    L10nKey.navSettings: 'Settings',
    L10nKey.navAdvancedWorkflows: 'Advanced Workflows',
    L10nKey.navAdvancedOrgChart: 'Detailed Org Chart',

    // Modules
    L10nKey.moduleFinance: 'Finance',
    L10nKey.moduleLegal: 'Legal',
    L10nKey.moduleCrm: 'CRM',
    L10nKey.moduleTasks: 'Tasks',

    // Chat UI
    L10nKey.chatNewConversation: 'New Conversation',
    L10nKey.chatHistory: 'Chat History',
    L10nKey.chatNoConversations: 'No conversations yet',
    L10nKey.chatStartNew: 'Start a new conversation',
    L10nKey.chatComposerHint: 'Type your message or ask anything...',
    L10nKey.chatReconnecting: 'Reconnecting...',
    L10nKey.chatAgentOsTitle: 'AgentOS Chat',
    L10nKey.chatAdvisoryDomain: 'Enterprise AI Assistant',

    // Profile UI
    L10nKey.profileTitle: 'Personal Profile',
    L10nKey.profileLanguageTitle: 'Language',
    L10nKey.profileLanguageVi: 'Tiếng Việt',
    L10nKey.profileLanguageEn: 'English',
    L10nKey.profileUnnamed: 'Unnamed',
    L10nKey.profileEmail: 'Email',
    L10nKey.profileFullName: 'Full Name',
    L10nKey.profileSaveName: 'Save name',
    L10nKey.profilePhone: 'Phone number',
    L10nKey.profileNoPhone: 'Phone number not set',
    L10nKey.profileSavePhone: 'Save phone',
    L10nKey.profileLogout: 'Logout',

    // Auth UI
    L10nKey.authIdentifierLabel: 'Phone number or Email',
    L10nKey.authIdentifierHint: 'Enter phone or email',
    L10nKey.authPasswordLabel: 'Password',
    L10nKey.authRememberMe: 'Remember this account',
    L10nKey.authLoginButton: 'Log In',
    L10nKey.authNoAccount: 'Don\'t have an account?',
    L10nKey.authCreateAccount: 'Create new account',
    L10nKey.authLanguageSwitchTooltip: 'Switch language',

    // Register UI
    L10nKey.regStep1Title: 'Create New Account',
    L10nKey.regStep2Title: 'Set Up Company',
    L10nKey.regStep1Subtitle: 'Initialize your identity account for COSA Platform',
    L10nKey.regStep2Subtitle: 'Create or join a company to sync Brain data to COSA Local',
    L10nKey.regStepAccount: 'Account',
    L10nKey.regStepCompany: 'Company',
    L10nKey.regFullNameLabel: 'Full Name',
    L10nKey.regEmailLabel: 'Email',
    L10nKey.regEmailHint: 'E.g., you@company.com',
    L10nKey.regPasswordLabel: 'Password (8–128 characters)',
    L10nKey.regConfirmPasswordLabel: 'Confirm Password',
    L10nKey.regCreatingAccount: 'Creating account...',
    L10nKey.regContinue: 'Continue',
    L10nKey.regTabCreateCompany: 'Create New',
    L10nKey.regTabJoinCompany: 'Join',
    L10nKey.regInvitationTokenLabel: 'Workspace Invitation Code',
    L10nKey.regInvitationTokenHint: 'Paste the invitation code sent to your email',
    L10nKey.regInvitationTokenHelper: 'Paste the invitation code provided by the workspace founder/admin via email.',
    L10nKey.regCompanyNameLabel: 'Company / Organization Name',
    L10nKey.regCompanyNameHint: 'E.g., VutaSoft, Acme Corp',
    L10nKey.regCompanyNameHelper: 'You will be the Founder and owner of this company.',
    L10nKey.regInitializingBrain: 'Initializing Brain...',
    L10nKey.regInitialize: 'Initialize',
    L10nKey.regBackToStep1: 'Back to step 1',
    L10nKey.regAlreadyHaveAccount: 'Already have an account?',
    L10nKey.regLoginNow: 'Log in now',

    // Settings UI
    L10nKey.settingsTitle: 'System Settings',
    L10nKey.settingsSubtitle: 'Configure account, AI Gateway & cost optimization',
    L10nKey.settingsModulesTitle: 'Optional Modules',
    L10nKey.settingsModulesSubtitle: 'Manage visibility and workspace enablement of business modules',
    L10nKey.settingsModuleUserVisible: 'Show on my navigation',
    L10nKey.settingsModuleWorkspaceEnabled: 'Enable for workspace',
    L10nKey.settingsModuleUpdateError: 'Failed to update module setting',

    // Common
    L10nKey.commonAdd: 'Add',
    L10nKey.commonEdit: 'Edit',
    L10nKey.commonSave: 'Save',
    L10nKey.commonCancel: 'Cancel',
    L10nKey.commonLoading: 'Loading...',
    L10nKey.commonError: 'Error',
    // Hologram Hub UI
    L10nKey.hubSubtitle: 'AI Enterprise Operating System',
    L10nKey.hubSwitchModule: 'Switch module',
    L10nKey.hubManageDashboard: 'Manage Dashboard',
    L10nKey.hubRefreshData: 'Refresh data',
    L10nKey.hubMyProfile: 'My profile',
    L10nKey.hubContinueSetup: 'Continue setup',
    L10nKey.hubSetupIncompleteTitle: 'Complete initial setup',
    L10nKey.hubSetupIncompleteDesc: 'Your project has not completed the 3-step setup for goals and first-week actions.',
    L10nKey.hubPlanningInProgress: 'Planning...',
    L10nKey.hubAskAiPlan: 'Ask AI to plan',
    L10nKey.hubCreateNewProject: 'Create new project',
    L10nKey.hubProjectNameLabel: 'Project name *',
    L10nKey.hubProjectNameHint: 'E.g., B2B SaaS Platform for Enterprises',
    L10nKey.hubProjectDescLabel: 'Problem description / JTBD',
    L10nKey.hubProjectDescHint: 'Briefly describe your idea or problem to solve...',
    L10nKey.hubEnterProjectNameError: 'Please enter a project name',
    L10nKey.hubMissingInfoTitle: 'Missing information',
    L10nKey.hubCreateProjectAction: 'Create project',
    L10nKey.hubSweepEnabled: 'AI auto-runs work within its authority',
    L10nKey.hubSweepDisabled: 'AI auto-run is paused',

    // Strategy Lenses: Hub Modal
    L10nKey.strategyHubTitle: 'Strategy Lenses Hub (4 Frameworks)',
    L10nKey.strategyHubSubtitle: 'Standard COSA alignment: PESTEL -> SWOT -> TOWS -> Balanced Scorecard',
    L10nKey.strategyTabSwot: 'Evidence-based SWOT (@count)',
    L10nKey.strategyTabBsc: 'Balanced Scorecard (@count)',
    L10nKey.strategyTabBscLocked: 'Balanced Scorecard (Locked)',

    // Strategy Lenses: PESTEL
    L10nKey.pestelDimPolitical: 'Political',
    L10nKey.pestelDimEconomic: 'Economic',
    L10nKey.pestelDimSocial: 'Social',
    L10nKey.pestelDimTechnological: 'Technological',
    L10nKey.pestelDimEnvironmental: 'Environmental',
    L10nKey.pestelDimLegal: 'Legal',
    L10nKey.pestelCatchSignal: 'Capture PESTEL Macro Signal',
    L10nKey.pestelMacroDimLabel: 'Macro dimension',
    L10nKey.pestelSignalTitleLabel: 'Signal title (*)',
    L10nKey.pestelSignalTitleHint: 'E.g., Interest rate hike, AI Small Models rising...',
    L10nKey.pestelContextLabel: 'Description & Context',
    L10nKey.pestelSaveSignal: 'Save Signal',
    L10nKey.pestelBannerDesc: 'PESTEL scans 6 macro dimensions to spot opportunities and risks. Convert any signal to a testable hypothesis with 1-click.',
    L10nKey.pestelAddTooltip: 'Add signal @dim',
    L10nKey.pestelEmpty: 'No signals yet',
    L10nKey.pestelHypothesisCreated: 'Hypothesis Created',
    L10nKey.pestelGenerateHypothesis: 'Generate Hypothesis',

    // Strategy Lenses: SWOT
    L10nKey.swotTypeStrength: 'Strengths (S)',
    L10nKey.swotTypeWeakness: 'Weaknesses (W)',
    L10nKey.swotTypeOpportunity: 'Opportunities (O)',
    L10nKey.swotTypeThreat: 'Threats (T)',
    L10nKey.swotAddTitle: 'Add SWOT Factor',
    L10nKey.swotTypeLabel: 'SWOT Category',
    L10nKey.swotContentLabel: 'Statement content (*)',
    L10nKey.swotContentHint: 'E.g., 92% customer retention rate due to Agentic AI features...',
    L10nKey.swotSave: 'Save SWOT',
    L10nKey.swotHeader: 'Evidence-based SWOT Matrix: Strengths/Weaknesses MUST link to empirical data (Evidence Refs) to eliminate bias.',
    L10nKey.swotAddTooltip: 'Add @type',
    L10nKey.swotEmpty: 'No content yet',

    // Strategy Lenses: TOWS
    L10nKey.towsTypeSo: 'SO Strategy (Maxi-Maxi: Strengths-Opportunities)',
    L10nKey.towsTypeWo: 'WO Strategy (Mini-Maxi: Weaknesses-Opportunities)',
    L10nKey.towsTypeSt: 'ST Strategy (Maxi-Mini: Strengths-Threats)',
    L10nKey.towsTypeWt: 'WT Strategy (Mini-Mini: Weaknesses-Threats)',
    L10nKey.towsCreateTitle: 'Create TOWS Strategy',
    L10nKey.towsPairLabel: 'TOWS Strategic Pair',
    L10nKey.towsStrategyNameLabel: 'Strategy name (*)',
    L10nKey.towsStrategyNameHint: 'E.g., Launch low-cost Starter AI tier...',
    L10nKey.towsDescLabel: 'Pairing mechanism & Trade-offs description',
    L10nKey.towsSaveStrategy: 'Save Strategy',
    L10nKey.towsEvalTitle: 'Evaluate strategy: @title',
    L10nKey.towsImpactScore: 'Impact score (1-5):',
    L10nKey.towsDifficultyScore: 'Difficulty / barrier score (1-5):',
    L10nKey.towsRatingExplanation: 'Rating explanation',
    L10nKey.towsSaveEvaluation: 'Save evaluation',
    L10nKey.towsSelectTitle: 'Select strategy: @title',
    L10nKey.towsSelectDesc: 'Selected strategy will become the baseline for building Action Initiatives.',
    L10nKey.towsSelectReasonLabel: 'Reason for selection (*)',
    L10nKey.towsConfirmSelect: 'Confirm Selection',
    L10nKey.towsMatrixHeader: 'TOWS Matrix: Pair internal & external factors to drive strategic decisions.',
    L10nKey.towsSelectionCount: '@count / @limit strategies selected',
    L10nKey.towsAddTooltip: 'Add strategy @name',
    L10nKey.towsEmpty: 'No strategies yet',
    L10nKey.towsSelected: 'SELECTED',
    L10nKey.towsScoreBtn: 'Score (1-5)',
    L10nKey.towsSelectBtn: 'Select',

    // Strategy Lenses: BSC
    L10nKey.bscPerspFinancial: 'Financial',
    L10nKey.bscPerspCustomer: 'Customer',
    L10nKey.bscPerspInternal: 'Internal Operations',
    L10nKey.bscPerspLearning: 'Learning & Growth',
    L10nKey.bscTitle: 'Balanced Scorecard (BSC)',
    L10nKey.bscHeaderDesc: 'BSC scorecard reflects approved and published Objectives & Key Results (OKRs).\nMetrics automatically sync by pillar once cycle OKRs are published.',
    L10nKey.bscReadOnlyDesc: 'Balanced Scorecard (Read-only): Summary of published objectives & metrics across the 4 strategic pillars.',
    L10nKey.bscEmpty: 'No published metrics yet',
  };
}
