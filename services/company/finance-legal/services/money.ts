import { APIError } from "encore.dev/api";

export interface Money {
  minor: string;
  currency: string;
}

/**
 * Validate that two Money objects share the same currency.
 */
function assertSameCurrency(a: Money, b: Money, operation: string): void {
  if (a.currency.toUpperCase() !== b.currency.toUpperCase()) {
    throw APIError.invalidArgument(
      `Cannot ${operation} money with different currencies: ${a.currency} and ${b.currency}`
    );
  }
}

/**
 * Cộng 2 khoản tiền cùng currency.
 * Throws APIError nếu khác currency.
 */
export function addMoney(a: Money, b: Money): Money {
  assertSameCurrency(a, b, "add");
  const sum = BigInt(a.minor) + BigInt(b.minor);
  return {
    minor: sum.toString(),
    currency: a.currency.toUpperCase(),
  };
}

/**
 * Trừ 2 khoản tiền cùng currency (a - b).
 * Throws APIError nếu khác currency.
 */
export function subtractMoney(a: Money, b: Money): Money {
  assertSameCurrency(a, b, "subtract");
  const diff = BigInt(a.minor) - BigInt(b.minor);
  return {
    minor: diff.toString(),
    currency: a.currency.toUpperCase(),
  };
}

/**
 * So sánh 2 khoản tiền cùng currency.
 * Trả về -1 (a < b), 0 (a === b), hoặc 1 (a > b).
 * Throws APIError nếu khác currency.
 */
export function compareMoney(a: Money, b: Money): number {
  assertSameCurrency(a, b, "compare");
  const aVal = BigInt(a.minor);
  const bVal = BigInt(b.minor);
  if (aVal < bVal) return -1;
  if (aVal > bVal) return 1;
  return 0;
}

/**
 * Tạo số tiền 0 cho currency chỉ định.
 */
export function zeroMoney(currency: string): Money {
  return {
    minor: "0",
    currency: currency.toUpperCase(),
  };
}

/**
 * Chuyển đổi số decimal (ví dụ "1500000.50") thành Money minor units.
 * Mặc định decimals = 0 cho VND, 2 cho USD/EUR/...
 */
export function parseDecimalToMoney(
  amountDecimal: string | number,
  currency: string,
  customDecimals?: number
): Money {
  const curr = currency.toUpperCase();
  const decimals = customDecimals !== undefined ? customDecimals : (curr === "VND" ? 0 : 2);
  const str = String(amountDecimal).trim();
  
  if (!/^-?\d+(\.\d+)?$/.test(str)) {
    throw APIError.invalidArgument(`Invalid decimal amount: ${amountDecimal}`);
  }

  const isNegative = str.startsWith("-");
  const absStr = isNegative ? str.slice(1) : str;
  const [whole, fraction = ""] = absStr.split(".");
  const paddedFraction = fraction.padEnd(decimals, "0").slice(0, decimals);
  const minorStr = whole + paddedFraction;
  const minorBig = BigInt(minorStr);
  const signedMinor = isNegative ? -minorBig : minorBig;

  return {
    minor: signedMinor.toString(),
    currency: curr,
  };
}

/**
 * Định dạng Money minor units thành chuỗi decimal.
 */
export function formatMoneyToDecimal(money: Money, customDecimals?: number): string {
  const curr = money.currency.toUpperCase();
  const decimals = customDecimals !== undefined ? customDecimals : (curr === "VND" ? 0 : 2);
  const minorBig = BigInt(money.minor);
  const isNegative = minorBig < 0n;
  const absMinor = isNegative ? -minorBig : minorBig;
  const absStr = absMinor.toString();

  if (decimals === 0) {
    return (isNegative ? "-" : "") + absStr;
  }

  const padded = absStr.padStart(decimals + 1, "0");
  const whole = padded.slice(0, -decimals);
  const fraction = padded.slice(-decimals);
  return (isNegative ? "-" : "") + `${whole}.${fraction}`;
}
