import 'package:get/get.dart';

abstract final class L10nKey {
  static const profileLanguageTitle = 'profile.language.title';
  static const profileLanguageVi = 'profile.language.vi';
  static const profileLanguageEn = 'profile.language.en';
  static const chatNewConversation = 'chat.newConversation';
  static const moduleFinance = 'module.finance';
  static const moduleLegal = 'module.legal';
  static const moduleCrm = 'module.crm';
  static const moduleTasks = 'module.tasks';
  static const settingsModulesTitle = 'settings.modules.title';
  static const settingsModulesSubtitle = 'settings.modules.subtitle';
  static const settingsModuleUserVisible = 'settings.modules.userVisible';
  static const settingsModuleWorkspaceEnabled = 'settings.modules.workspaceEnabled';
  static const settingsModuleUpdateError = 'settings.modules.updateError';

  static const List<String> required = [
    profileLanguageTitle,
    profileLanguageVi,
    profileLanguageEn,
    chatNewConversation,
    moduleFinance,
    moduleLegal,
    moduleCrm,
    moduleTasks,
    settingsModulesTitle,
    settingsModulesSubtitle,
    settingsModuleUserVisible,
    settingsModuleWorkspaceEnabled,
    settingsModuleUpdateError,
  ];
}

class AppTranslations extends Translations {
  @override
  Map<String, Map<String, String>> get keys => {
        'vi_VN': vi,
        'en_US': en,
      };

  static const Map<String, String> vi = {
    L10nKey.profileLanguageTitle: 'Ngôn ngữ',
    L10nKey.profileLanguageVi: 'Tiếng Việt',
    L10nKey.profileLanguageEn: 'English',
    L10nKey.chatNewConversation: 'Cuộc trò chuyện mới',
    L10nKey.moduleFinance: 'Tài chính',
    L10nKey.moduleLegal: 'Pháp lý',
    L10nKey.moduleCrm: 'Khách hàng (CRM)',
    L10nKey.moduleTasks: 'Nhiệm vụ',
    L10nKey.settingsModulesTitle: 'Mô-đun tùy chọn',
    L10nKey.settingsModulesSubtitle: 'Quản lý hiển thị và kích hoạt các mô-đun nghiệp vụ',
    L10nKey.settingsModuleUserVisible: 'Hiển thị trên menu của tôi',
    L10nKey.settingsModuleWorkspaceEnabled: 'Kích hoạt cho toàn workspace',
    L10nKey.settingsModuleUpdateError: 'Cập nhật trạng thái mô-đun thất bại',
  };

  static const Map<String, String> en = {
    L10nKey.profileLanguageTitle: 'Language',
    L10nKey.profileLanguageVi: 'Tiếng Việt',
    L10nKey.profileLanguageEn: 'English',
    L10nKey.chatNewConversation: 'New Conversation',
    L10nKey.moduleFinance: 'Finance',
    L10nKey.moduleLegal: 'Legal',
    L10nKey.moduleCrm: 'CRM',
    L10nKey.moduleTasks: 'Tasks',
    L10nKey.settingsModulesTitle: 'Optional Modules',
    L10nKey.settingsModulesSubtitle: 'Manage visibility and workspace enablement of business modules',
    L10nKey.settingsModuleUserVisible: 'Show on my navigation',
    L10nKey.settingsModuleWorkspaceEnabled: 'Enable for workspace',
    L10nKey.settingsModuleUpdateError: 'Failed to update module setting',
  };
}
