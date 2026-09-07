import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_vi.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('vi'),
  ];

  /// Main application title
  ///
  /// In en, this message translates to:
  /// **'COSA - AI Enterprise Operating System'**
  String get appTitle;

  /// No description provided for @navHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get navHome;

  /// No description provided for @navCommandCenter.
  ///
  /// In en, this message translates to:
  /// **'COSA Command Center'**
  String get navCommandCenter;

  /// No description provided for @navStrategy.
  ///
  /// In en, this message translates to:
  /// **'Strategy'**
  String get navStrategy;

  /// No description provided for @navProjects.
  ///
  /// In en, this message translates to:
  /// **'Projects'**
  String get navProjects;

  /// No description provided for @navOkrs.
  ///
  /// In en, this message translates to:
  /// **'OKRs'**
  String get navOkrs;

  /// No description provided for @navTwelveWy.
  ///
  /// In en, this message translates to:
  /// **'12-Week Year'**
  String get navTwelveWy;

  /// No description provided for @navFunding.
  ///
  /// In en, this message translates to:
  /// **'Resources & Funding'**
  String get navFunding;

  /// No description provided for @navTasks.
  ///
  /// In en, this message translates to:
  /// **'Tasks'**
  String get navTasks;

  /// No description provided for @navApprovals.
  ///
  /// In en, this message translates to:
  /// **'Approvals'**
  String get navApprovals;

  /// No description provided for @navNeedsYou.
  ///
  /// In en, this message translates to:
  /// **'Needs Your Attention'**
  String get navNeedsYou;

  /// No description provided for @navBlockedWork.
  ///
  /// In en, this message translates to:
  /// **'Blocked Work'**
  String get navBlockedWork;

  /// No description provided for @navWorkInspector.
  ///
  /// In en, this message translates to:
  /// **'Work Inspector'**
  String get navWorkInspector;

  /// No description provided for @navAgents.
  ///
  /// In en, this message translates to:
  /// **'AI Agents Team'**
  String get navAgents;

  /// No description provided for @navLegal.
  ///
  /// In en, this message translates to:
  /// **'Legal & AI Contracts'**
  String get navLegal;

  /// No description provided for @navMarketing.
  ///
  /// In en, this message translates to:
  /// **'Marketing & Lead Gen'**
  String get navMarketing;

  /// No description provided for @navCrm.
  ///
  /// In en, this message translates to:
  /// **'Sales & CRM'**
  String get navCrm;

  /// No description provided for @navSkills.
  ///
  /// In en, this message translates to:
  /// **'AI Skill Registry'**
  String get navSkills;

  /// No description provided for @navFinance.
  ///
  /// In en, this message translates to:
  /// **'Accounting & Finance'**
  String get navFinance;

  /// No description provided for @navVault.
  ///
  /// In en, this message translates to:
  /// **'Knowledge Vault'**
  String get navVault;

  /// No description provided for @navOrgChart.
  ///
  /// In en, this message translates to:
  /// **'Organization Chart'**
  String get navOrgChart;

  /// No description provided for @navWorkflows.
  ///
  /// In en, this message translates to:
  /// **'Workflows'**
  String get navWorkflows;

  /// No description provided for @navTemplates.
  ///
  /// In en, this message translates to:
  /// **'Template Management'**
  String get navTemplates;

  /// No description provided for @navSettings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get navSettings;

  /// No description provided for @settingsTitle.
  ///
  /// In en, this message translates to:
  /// **'System Settings'**
  String get settingsTitle;

  /// No description provided for @settingsSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Configure account, AI Gateway & cost optimization'**
  String get settingsSubtitle;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @languageVietnamese.
  ///
  /// In en, this message translates to:
  /// **'Tiếng Việt'**
  String get languageVietnamese;

  /// No description provided for @languageEnglish.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get languageEnglish;

  /// No description provided for @selectLanguage.
  ///
  /// In en, this message translates to:
  /// **'Select Language'**
  String get selectLanguage;

  /// No description provided for @optionalModules.
  ///
  /// In en, this message translates to:
  /// **'Workspace Modules'**
  String get optionalModules;

  /// No description provided for @optionalModulesSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Enable or customize visibility of specialized business modules'**
  String get optionalModulesSubtitle;

  /// No description provided for @moduleFinance.
  ///
  /// In en, this message translates to:
  /// **'Accounting & Finance'**
  String get moduleFinance;

  /// No description provided for @moduleLegal.
  ///
  /// In en, this message translates to:
  /// **'Legal & AI Contracts'**
  String get moduleLegal;

  /// No description provided for @moduleCrm.
  ///
  /// In en, this message translates to:
  /// **'Sales & CRM'**
  String get moduleCrm;

  /// No description provided for @moduleDisabledByWorkspace.
  ///
  /// In en, this message translates to:
  /// **'Disabled at workspace level'**
  String get moduleDisabledByWorkspace;

  /// No description provided for @workspaceModuleConfig.
  ///
  /// In en, this message translates to:
  /// **'Workspace Module Policy'**
  String get workspaceModuleConfig;

  /// No description provided for @personalModulePreference.
  ///
  /// In en, this message translates to:
  /// **'Personal Module Visibility'**
  String get personalModulePreference;

  /// No description provided for @save.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get save;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @enabled.
  ///
  /// In en, this message translates to:
  /// **'Enabled'**
  String get enabled;

  /// No description provided for @disabled.
  ///
  /// In en, this message translates to:
  /// **'Disabled'**
  String get disabled;

  /// No description provided for @visible.
  ///
  /// In en, this message translates to:
  /// **'Visible'**
  String get visible;

  /// No description provided for @hidden.
  ///
  /// In en, this message translates to:
  /// **'Hidden'**
  String get hidden;

  /// No description provided for @loading.
  ///
  /// In en, this message translates to:
  /// **'Loading...'**
  String get loading;

  /// No description provided for @error.
  ///
  /// In en, this message translates to:
  /// **'Error'**
  String get error;

  /// No description provided for @success.
  ///
  /// In en, this message translates to:
  /// **'Success'**
  String get success;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'vi'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'vi':
      return AppLocalizationsVi();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
