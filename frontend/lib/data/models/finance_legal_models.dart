import 'package:flutter/foundation.dart';
import 'source_value_state.dart';

@immutable
class AccountingProfileModel {
  final String id;
  final String mode; // 'standard', 'simplified', 'micro'
  final bool active;
  final DateTime? createdAt;
  final SourceValueState createdAtState;

  const AccountingProfileModel({
    required this.id,
    required this.mode,
    this.active = true,
    this.createdAt,
    this.createdAtState = SourceValueState.unavailable,
  });

  factory AccountingProfileModel.fromJson(Map<String, dynamic> json) {
    final parsedCreated = parseSourceDate(json['created_at'] ?? json['createdAt']);
    return AccountingProfileModel(
      id: json['id']?.toString() ?? '',
      mode: json['mode']?.toString() ?? 'standard',
      active: json['active'] == true || json['is_active'] == true,
      createdAt: parsedCreated.value,
      createdAtState: parsedCreated.state,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'mode': mode,
      'active': active,
      'created_at': createdAt?.toIso8601String(),
    };
  }

  AccountingProfileModel copyWith({
    String? id,
    String? mode,
    bool? active,
    DateTime? createdAt,
    SourceValueState? createdAtState,
  }) {
    return AccountingProfileModel(
      id: id ?? this.id,
      mode: mode ?? this.mode,
      active: active ?? this.active,
      createdAt: createdAt ?? this.createdAt,
      createdAtState: createdAtState ?? this.createdAtState,
    );
  }
}

@immutable
class AccountingPeriodModel {
  final String id;
  final DateTime? startDate;
  final SourceValueState startDateState;
  final DateTime? endDate;
  final SourceValueState endDateState;
  final String status; // 'open', 'closed', 'locked'
  final bool isLocked;

  const AccountingPeriodModel({
    required this.id,
    this.startDate,
    this.startDateState = SourceValueState.unavailable,
    this.endDate,
    this.endDateState = SourceValueState.unavailable,
    this.status = 'open',
    this.isLocked = false,
  });

  factory AccountingPeriodModel.fromJson(Map<String, dynamic> json) {
    final parsedStart = parseSourceDate(json['start_date'] ?? json['startDate']);
    final parsedEnd = parseSourceDate(json['end_date'] ?? json['endDate']);
    return AccountingPeriodModel(
      id: json['id']?.toString() ?? '',
      startDate: parsedStart.value,
      startDateState: parsedStart.state,
      endDate: parsedEnd.value,
      endDateState: parsedEnd.state,
      status: json['status']?.toString() ?? 'open',
      isLocked: json['is_locked'] == true || json['isLocked'] == true || json['status'] == 'locked',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'start_date': startDate?.toIso8601String(),
      'end_date': endDate?.toIso8601String(),
      'status': status,
      'is_locked': isLocked,
    };
  }
}

@immutable
class FinancialTransactionModel {
  final String id;
  final String type; // 'income', 'expense', 'transfer'
  final MonetaryAmount? amount;
  final SourceValueState amountState;
  final String currency;
  final String category;
  final String description;
  final DateTime? transactionDate;
  final SourceValueState transactionDateState;
  final String? evidenceUrl;
  final String? accountCode;

  const FinancialTransactionModel({
    required this.id,
    required this.type,
    this.amount,
    this.amountState = SourceValueState.unavailable,
    this.currency = 'VND',
    required this.category,
    this.description = '',
    this.transactionDate,
    this.transactionDateState = SourceValueState.unavailable,
    this.evidenceUrl,
    this.accountCode,
  });

  factory FinancialTransactionModel.fromJson(Map<String, dynamic> json) {
    final currency = json['currency']?.toString() ?? 'VND';
    final parsedAmount = parseSourceAmount(json['amount'] ?? json['value'], currency: currency);
    final parsedDate = parseSourceDate(
      json['transaction_date'] ?? json['transactionDate'] ?? json['date'],
    );

    return FinancialTransactionModel(
      id: json['id']?.toString() ?? '',
      type: json['type']?.toString() ?? 'expense',
      amount: parsedAmount.value,
      amountState: parsedAmount.state,
      currency: currency,
      category: json['category']?.toString() ?? 'general',
      description: json['description']?.toString() ?? '',
      transactionDate: parsedDate.value,
      transactionDateState: parsedDate.state,
      evidenceUrl: json['evidence_url']?.toString() ?? json['evidenceUrl']?.toString(),
      accountCode: json['account_code']?.toString() ?? json['accountCode']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type,
      'amount': amount?.decimal,
      'currency': currency,
      'category': category,
      'description': description,
      'transaction_date': transactionDate?.toIso8601String(),
      'evidence_url': evidenceUrl,
      'account_code': accountCode,
    };
  }
}

@immutable
class FinanceSnapshotModel {
  final String periodId;
  final MonetaryAmount? totalIncome;
  final SourceValueState totalIncomeState;
  final MonetaryAmount? totalExpense;
  final SourceValueState totalExpenseState;
  final MonetaryAmount? netCashflow;
  final SourceValueState netCashflowState;
  final double? runwayMonths;
  final SourceValueState runwayMonthsState;
  final DateTime? generatedAt;
  final SourceValueState generatedAtState;
  final String currency;

  const FinanceSnapshotModel({
    required this.periodId,
    this.totalIncome,
    this.totalIncomeState = SourceValueState.unavailable,
    this.totalExpense,
    this.totalExpenseState = SourceValueState.unavailable,
    this.netCashflow,
    this.netCashflowState = SourceValueState.unavailable,
    this.runwayMonths,
    this.runwayMonthsState = SourceValueState.unavailable,
    this.generatedAt,
    this.generatedAtState = SourceValueState.unavailable,
    this.currency = 'VND',
  });

  factory FinanceSnapshotModel.fromJson(Map<String, dynamic> json) {
    final currency = json['currency']?.toString() ?? 'VND';
    final parsedIncome = parseSourceAmount(
      json['total_income'] ?? json['totalIncome'],
      currency: currency,
    );
    final parsedExpense = parseSourceAmount(
      json['total_expense'] ?? json['totalExpense'],
      currency: currency,
    );
    final parsedCashflow = parseSourceAmount(
      json['net_cashflow'] ?? json['netCashflow'],
      currency: currency,
    );
    final parsedRunway = parseSourceDouble(
      json['runway_months'] ?? json['runwayMonths'],
    );
    final parsedGen = parseSourceDate(
      json['generated_at'] ?? json['generatedAt'],
    );

    return FinanceSnapshotModel(
      periodId: json['period_id']?.toString() ?? json['periodId']?.toString() ?? '',
      totalIncome: parsedIncome.value,
      totalIncomeState: parsedIncome.state,
      totalExpense: parsedExpense.value,
      totalExpenseState: parsedExpense.state,
      netCashflow: parsedCashflow.value,
      netCashflowState: parsedCashflow.state,
      runwayMonths: parsedRunway.value,
      runwayMonthsState: parsedRunway.state,
      generatedAt: parsedGen.value,
      generatedAtState: parsedGen.state,
      currency: currency,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'period_id': periodId,
      'total_income': totalIncome?.decimal,
      'total_expense': totalExpense?.decimal,
      'net_cashflow': netCashflow?.decimal,
      'runway_months': runwayMonths,
      'generated_at': generatedAt?.toIso8601String(),
    };
  }
}

@immutable
class LegalObligationModel {
  final String id;
  final String title;
  final String category; // 'tax', 'corporate', 'labor', 'compliance'
  final DateTime? dueDate;
  final SourceValueState dueDateState;
  final String status; // 'pending', 'in_progress', 'completed', 'overdue'
  final String? penaltyRisk;

  const LegalObligationModel({
    required this.id,
    required this.title,
    required this.category,
    this.dueDate,
    this.dueDateState = SourceValueState.unavailable,
    this.status = 'pending',
    this.penaltyRisk,
  });

  factory LegalObligationModel.fromJson(Map<String, dynamic> json) {
    final parsedDue = parseSourceDate(json['due_date'] ?? json['dueDate']);
    return LegalObligationModel(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      category: json['category']?.toString() ?? 'compliance',
      dueDate: parsedDue.value,
      dueDateState: parsedDue.state,
      status: json['status']?.toString() ?? 'pending',
      penaltyRisk: json['penalty_risk']?.toString() ?? json['penaltyRisk']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'category': category,
      'due_date': dueDate?.toIso8601String(),
      'status': status,
      'penalty_risk': penaltyRisk,
    };
  }
}

@immutable
class LegalChecklistItemModel {
  final String id;
  final String obligationId;
  final String content;
  final bool isCompleted;
  final String? verifiedBy;

  const LegalChecklistItemModel({
    required this.id,
    required this.obligationId,
    required this.content,
    this.isCompleted = false,
    this.verifiedBy,
  });

  factory LegalChecklistItemModel.fromJson(Map<String, dynamic> json) {
    return LegalChecklistItemModel(
      id: json['id']?.toString() ?? '',
      obligationId: json['obligation_id']?.toString() ?? json['obligationId']?.toString() ?? '',
      content: json['content']?.toString() ?? '',
      isCompleted: json['is_completed'] == true || json['isCompleted'] == true,
      verifiedBy: json['verified_by']?.toString() ?? json['verifiedBy']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'obligation_id': obligationId,
      'content': content,
      'is_completed': isCompleted,
      'verified_by': verifiedBy,
    };
  }
}
