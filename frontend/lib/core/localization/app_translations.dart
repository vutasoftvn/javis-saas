import 'package:get/get.dart';

abstract final class L10nKey {
  static const profileLanguageTitle = 'profile.language.title';
  static const profileLanguageVi = 'profile.language.vi';
  static const profileLanguageEn = 'profile.language.en';
  static const chatNewConversation = 'chat.newConversation';
  static const moduleFinance = 'module.finance';
  static const moduleLegal = 'module.legal';
  static const moduleCrm = 'module.crm';

  static const List<String> required = [
    profileLanguageTitle,
    profileLanguageVi,
    profileLanguageEn,
    chatNewConversation,
    moduleFinance,
    moduleLegal,
    moduleCrm,
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
  };

  static const Map<String, String> en = {
    L10nKey.profileLanguageTitle: 'Language',
    L10nKey.profileLanguageVi: 'Tiếng Việt',
    L10nKey.profileLanguageEn: 'English',
    L10nKey.chatNewConversation: 'New Conversation',
    L10nKey.moduleFinance: 'Finance',
    L10nKey.moduleLegal: 'Legal',
    L10nKey.moduleCrm: 'CRM',
  };
}
