import 'dart:convert';

import '../../../core/network/api_client.dart';
import '../../../core/services/secure_storage_service.dart';
import 'finance_service.dart';

class FinanceTT58Service {
  Future<String?> _workspaceId() => SecureStorageService.read('workspace_id');

  String _scopedPath(String path, String workspaceId) {
    if (path.contains('workspaceId=') || path.contains('workspace_id=')) {
      return path;
    }
    final separator = path.contains('?') ? '&' : '?';
    return '$path${separator}workspace_id=${Uri.encodeQueryComponent(workspaceId)}';
  }

  Future<dynamic> _getJson(String path) async {
    final workspaceId = await _workspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;
    final response = await ApiClient.get(_scopedPath(path, workspaceId));
    if (response.statusCode < 200 || response.statusCode >= 300) return null;
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  Future<dynamic> _postJson(String path, Map<String, dynamic> body) async {
    final workspaceId = await _workspaceId();
    if (workspaceId == null || workspaceId.isEmpty) return null;
    final response = await ApiClient.post(
      _scopedPath(path, workspaceId),
      body: body,
    );
    if (response.statusCode < 200 || response.statusCode >= 300) return null;
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  Future<Map<String, dynamic>?> getReport(
    String legalEntityId,
    String periodId,
    String reportCode,
  ) async {
    final data = await _postJson('/finance/reports/generate', {
      'legalEntityId': legalEntityId,
      'periodId': periodId,
      'reportCode': reportCode,
    });
    if (data == null) return null;
    return _transformReport(reportCode, data as Map<String, dynamic>);
  }

  Map<String, dynamic> _transformReport(
    String reportCode,
    Map<String, dynamic> report,
  ) {
    final lines = ((report['lines'] as List<dynamic>?) ?? [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    num byCode(String code) {
      final match = lines.where((l) => l['lineCode'] == code);
      if (match.isEmpty) return 0;
      return num.tryParse(match.first['amountMinor']?.toString() ?? '0') ?? 0;
    }

    if (reportCode == 'B01') {
      final cash = byCode('TS');
      final receivable = byCode('PHAI_THU');
      final inventory = byCode('TON_KHO');
      final loan = byCode('NO_VAY');
      final capital = byCode('VON_GOP');
      final retainedEarnings = byCode('LOI_NHUAN_GIU_LAI');
      final totalAssets = cash + receivable + inventory;
      final ownerEquity = capital + retainedEarnings;
      return {
        'assets': {
          'total_assets': totalAssets,
          'cash_and_equivalents': cash,
          'accounts_receivable': receivable,
          'inventories': inventory,
        },
        'capital_and_liabilities': {
          'total_capital': loan + ownerEquity,
          'total_liabilities': loan,
          'owner_equity': ownerEquity,
        },
        'is_balanced': totalAssets == (loan + ownerEquity),
        'status': report['status'],
        'issues': report['issues'],
      };
    }

    return {
      'items': {
        'net_revenue': byCode('DOANH_THU_THUAN'),
        'cost_of_goods_sold': byCode('GIA_VON'),
        'gross_profit': byCode('LOI_NHUAN_GOP'),
        'operating_expenses': byCode('CHI_PHI_HDKD'),
        'corporate_income_tax': byCode('THUE_TNDN'),
        'net_profit_after_tax': byCode('LOI_NHUAN_SAU_THUE'),
      },
      'status': report['status'],
      'issues': report['issues'],
    };
  }

  /// B03 — thuyết minh chế độ kế toán.
  ///
  /// `is_statutory_required` luôn `true`: với doanh nghiệp siêu nhỏ theo TT58
  /// đây là một sự kiện pháp lý cố định, không suy ra từ việc đã có dòng
  /// `accounting_policies` trong DB hay chưa. Trước đây khi founder chưa
  /// cấu hình chính sách (trạng thái khởi đầu rất phổ biến, vì
  /// `setAccountingPolicyService` đòi thao tác tường minh), hàm này trả `null`
  /// và card đọc thành "không bắt buộc theo luật" — ngược hẳn sự thật.
  ///
  /// Chỉ trả `null` khi bản thân lời gọi HTTP thất bại. Khi chưa có chính
  /// sách, trả về đúng bộ giá trị mặc định mà bảng `accounting_policies` tự
  /// đặt (xem migration 45).
  Future<Map<String, dynamic>?> getAccountingPolicy(
    String legalEntityId,
  ) async {
    final data = await _getJson(
      '/finance/accounting-policies?legalEntityId=$legalEntityId',
    );
    if (data == null) return null;
    final policy = data['policy'] != null
        ? Map<String, dynamic>.from(data['policy'] as Map)
        : null;
    return {
      'is_statutory_required': true,
      'compliance_note':
          'Chế độ kế toán đang áp dụng theo Thông tư 58/2026/TT-BTC.',
      'accounting_policies': {
        'currency': 'VND (Đồng Việt Nam)',
        'inventory_valuation':
            policy?['inventoryValuationMethod'] ?? 'weighted_average',
        'depreciation_method':
            policy?['depreciationMethod'] ?? 'straight_line',
        'revenue_recognition': policy?['revenueRecognitionMethod'] ??
            'Ghi nhận khi hoàn thành chuyển giao dịch vụ/hàng hóa',
      },
    };
  }

  Future<Map<String, dynamic>?> getTaxObligations(
    String legalEntityId,
    String periodId,
  ) async {
    // Đồng bộ thuế TNDN là hành động RIÊNG, tường minh (không phải side-effect
    // của đọc) — gọi trước, bỏ qua kết quả trả về nếu lỗi (không chặn việc đọc
    // dữ liệu đã có sẵn khi sync tạm thời thất bại).
    await _postJson('/finance/tax-obligations/sync', {
      'legalEntityId': legalEntityId,
      'periodId': periodId,
    });
    final data = await _getJson(
      '/finance/tax-obligations?legalEntityId=$legalEntityId&periodId=$periodId',
    );
    if (data == null) return null;
    final taxesRaw = (data['taxes'] as List<dynamic>?) ?? [];
    return {
      'taxes': taxesRaw.map((t) {
        final m = Map<String, dynamic>.from(t as Map);
        return {
          'tax_name': m['taxName'],
          'incurred': num.tryParse(m['incurredMinor']?.toString() ?? '0') ?? 0,
          'paid': num.tryParse(m['paidMinor']?.toString() ?? '0') ?? 0,
          'closing_debt':
              num.tryParse(m['closingDebtMinor']?.toString() ?? '0') ?? 0,
        };
      }).toList(),
      'total_balance_due':
          num.tryParse(data['totalBalanceDueMinor']?.toString() ?? '0') ?? 0,
    };
  }

  Future<Map<String, dynamic>?> getFounderLiteMetrics(
    String legalEntityId,
    String periodId,
  ) async {
    final service = FinanceService();
    final snapshots = await service.getFinancialSnapshots();
    final b02 = await getReport(legalEntityId, periodId, 'B02');

    final latestSnapshot = snapshots.isNotEmpty
        ? Map<String, dynamic>.from(snapshots.first as Map)
        : null;
    final cashBalance =
        num.tryParse(latestSnapshot?['currentCash']?.toString() ?? '') ?? 0;
    final runwayMonths = latestSnapshot?['runwayMonths'] == null
        ? null
        : num.tryParse(latestSnapshot!['runwayMonths'].toString());
    final monthlyBurn =
        num.tryParse(latestSnapshot?['monthlyNetBurn']?.toString() ?? '') ?? 0;
    final cashFlowPositive =
        latestSnapshot?['cashFlowPositive'] as bool? ?? true;

    final items = b02?['items'] as Map<String, dynamic>? ?? {};
    final revenue = (items['net_revenue'] as num?) ?? 0;
    final cogs = (items['cost_of_goods_sold'] as num?) ?? 0;
    final opex = (items['operating_expenses'] as num?) ?? 0;
    final netProfit = (items['net_profit_after_tax'] as num?) ?? 0;

    String healthStatus;
    if (!cashFlowPositive && (runwayMonths == null || runwayMonths < 1) ||
        cashBalance < 0) {
      healthStatus = 'CRITICAL';
    } else if (!cashFlowPositive && runwayMonths != null && runwayMonths < 3) {
      healthStatus = 'WARNING';
    } else {
      healthStatus = 'HEALTHY';
    }

    return {
      'cash_and_bank_balance': cashBalance,
      'total_revenue_period': revenue,
      'total_expense_period': cogs + opex,
      'estimated_net_profit': netProfit,
      'runway_months': runwayMonths ?? 0,
      'monthly_burn_rate': monthlyBurn,
      'health_status': healthStatus,
    };
  }
}
