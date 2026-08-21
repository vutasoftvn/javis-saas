"""Standalone Finance CSV Data Analysis script executed inside isolated sandbox.

Reads: /input/finance.csv
Writes:
  - /output/finance_summary.json
  - /output/finance_report.md
"""

import csv
import json
import os
import sys
from pathlib import Path


def analyze_finance(csv_path: str = "/input/finance.csv", output_dir: str = "/output") -> None:
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(csv_path):
        csv_files = list(Path("/input").glob("*.csv")) if os.path.exists("/input") else []
        if csv_files:
            csv_path = str(csv_files[0])
        else:
            summary = {
                "status": "error",
                "error": f"Input file not found at {csv_path}",
                "total_income": 0.0,
                "total_expense": 0.0,
            }
            with open(os.path.join(output_dir, "finance_summary.json"), "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            with open(os.path.join(output_dir, "finance_report.md"), "w", encoding="utf-8") as f:
                f.write("# Báo cáo phân tích tài chính\n\nKhông tìm thấy file dữ liệu đầu vào `/input/finance.csv`.\n")
            return

    total_transactions = 0
    total_income = 0.0
    total_expense = 0.0
    category_breakdown = {}

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_transactions += 1

            amount = 0.0
            for k in ["amount", "value", "total", "money"]:
                if k in row and row[k]:
                    try:
                        amount = float(str(row[k]).replace(",", "").replace("$", "").replace("VND", "").strip())
                        break
                    except ValueError:
                        pass

            tx_type = (row.get("type") or row.get("transaction_type") or "expense").strip().lower()
            category = (row.get("category") or "general").strip()
            category_breakdown[category] = category_breakdown.get(category, 0.0) + amount

            if tx_type in ["income", "revenue", "inflow", "credit"]:
                total_income += amount
            else:
                total_expense += amount

    net_cashflow = total_income - total_expense
    monthly_burn = total_expense if total_expense > 0 else 1.0

    summary = {
        "status": "success",
        "total_transactions": total_transactions,
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "net_cashflow": round(net_cashflow, 2),
        "monthly_burn": round(monthly_burn, 2),
        "category_breakdown": {k: round(v, 2) for k, v in category_breakdown.items()},
    }

    # 1. Output structured JSON
    json_path = os.path.join(output_dir, "finance_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # 2. Output Markdown report
    md_path = os.path.join(output_dir, "finance_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Báo cáo Phân tích Tài chính (Financial Analysis Report)\n\n")
        f.write(f"- **Tổng số giao dịch:** {total_transactions:,}\n")
        f.write(f"- **Tổng thu (Income/Revenue):** {total_income:,.0f} VND\n")
        f.write(f"- **Tổng chi (Expenses/Burn):** {total_expense:,.0f} VND\n")
        f.write(f"- **Dòng tiền ròng (Net Cashflow):** {net_cashflow:,.0f} VND\n\n")
        f.write("### Chi tiết theo danh mục (Category Breakdown)\n\n")
        for cat, amt in sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True):
            f.write(f"- **{cat}**: {amt:,.0f} VND\n")

    print(f"Finance analysis completed: {total_transactions} txs, net cashflow {net_cashflow:,.0f} VND.")


if __name__ == "__main__":
    analyze_finance()
