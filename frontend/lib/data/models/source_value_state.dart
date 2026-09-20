import 'package:flutter/foundation.dart';

/// Provenance-aware state for DTO fields.
/// Exactly three states: present, unavailable, invalid.
enum SourceValueState {
  present,
  unavailable,
  invalid,
}

/// Server decimal string representation of money.
/// Avoids IEEE-754 binary floating-point rounding errors.
@immutable
class MonetaryAmount {
  final String decimal;
  final String currency;

  const MonetaryAmount({
    required this.decimal,
    this.currency = 'VND',
  });

  /// Parse double safely if numeric operations needed for charts/calculations
  double? toDoubleOrNull() => double.tryParse(decimal);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is MonetaryAmount &&
          runtimeType == other.runtimeType &&
          decimal == other.decimal &&
          currency == other.currency;

  @override
  int get hashCode => Object.hash(decimal, currency);

  @override
  String toString() => '$decimal $currency';
}

@immutable
class ParsedValue<T> {
  final T? value;
  final SourceValueState state;

  const ParsedValue({required this.value, required this.state});
}

ParsedValue<DateTime> parseSourceDate(Object? raw) {
  if (raw == null) {
    return const ParsedValue(value: null, state: SourceValueState.unavailable);
  }
  final str = raw.toString().trim();
  if (str.isEmpty) {
    return const ParsedValue(value: null, state: SourceValueState.unavailable);
  }
  final parsed = DateTime.tryParse(str);
  if (parsed != null) {
    return ParsedValue(value: parsed, state: SourceValueState.present);
  }
  return const ParsedValue(value: null, state: SourceValueState.invalid);
}

ParsedValue<MonetaryAmount> parseSourceAmount(Object? raw, {String currency = 'VND'}) {
  if (raw == null) {
    return const ParsedValue(value: null, state: SourceValueState.unavailable);
  }
  if (raw is num) {
    if (raw.isNaN || raw.isInfinite) {
      return const ParsedValue(value: null, state: SourceValueState.invalid);
    }
    return ParsedValue(
      value: MonetaryAmount(decimal: raw.toString(), currency: currency),
      state: SourceValueState.present,
    );
  }
  final str = raw.toString().trim();
  if (str.isEmpty) {
    return const ParsedValue(value: null, state: SourceValueState.unavailable);
  }
  final parsed = num.tryParse(str);
  if (parsed != null && !parsed.isNaN && !parsed.isInfinite) {
    return ParsedValue(
      value: MonetaryAmount(decimal: str, currency: currency),
      state: SourceValueState.present,
    );
  }
  return const ParsedValue(value: null, state: SourceValueState.invalid);
}

ParsedValue<double> parseSourceDouble(Object? raw) {
  if (raw == null) {
    return const ParsedValue(value: null, state: SourceValueState.unavailable);
  }
  if (raw is num) {
    if (raw.isNaN || raw.isInfinite) {
      return const ParsedValue(value: null, state: SourceValueState.invalid);
    }
    return ParsedValue(value: raw.toDouble(), state: SourceValueState.present);
  }
  final str = raw.toString().trim();
  if (str.isEmpty) {
    return const ParsedValue(value: null, state: SourceValueState.unavailable);
  }
  final parsed = double.tryParse(str);
  if (parsed != null && !parsed.isNaN && !parsed.isInfinite) {
    return ParsedValue(value: parsed, state: SourceValueState.present);
  }
  return const ParsedValue(value: null, state: SourceValueState.invalid);
}
