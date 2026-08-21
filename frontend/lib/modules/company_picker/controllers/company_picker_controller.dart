import 'package:get/get.dart';
import '../../auth/services/auth_service.dart';
import '../../../core/routing/app_routes.dart';

class CompanyPickerController extends GetxController {
  final AuthService _authService = AuthService();

  late final String platformToken;
  late final List<CompanyMembershipInfo> companies;

  final isLoading = false.obs;
  final errorMessage = ''.obs;
  final selectingCompanyId = Rxn<String>();

  @override
  void onInit() {
    super.onInit();
    final args = (Get.arguments as Map?) ?? const {};
    platformToken = args['platformToken'] as String? ?? '';
    companies = (args['companies'] as List<CompanyMembershipInfo>?) ?? const [];
  }

  Future<void> selectCompany(String companyId) async {
    if (platformToken.isEmpty) {
      errorMessage.value = 'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.';
      return;
    }

    isLoading.value = true;
    errorMessage.value = '';
    selectingCompanyId.value = companyId;

    final ok = await _authService.finishAuthentication(platformToken: platformToken, companyId: companyId);

    isLoading.value = false;
    selectingCompanyId.value = null;

    if (ok) {
      Get.offAllNamed(AppRoutes.hub);
    } else {
      errorMessage.value = 'Đồng bộ dữ liệu công ty thất bại. Vui lòng thử lại.';
    }
  }
}
