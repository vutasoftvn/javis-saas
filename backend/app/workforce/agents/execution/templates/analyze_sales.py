"""Standalone Sales CSV Data Analysis script executed inside isolated sandbox.

Reads: /input/sales.csv
Writes:
  - /output/sales_summary.json
  - /output/sales_report.md
"""

import csv
import json
import os
import sys
from pathlib import Path


def analyze_sales(csv_path: str = "/input/sales.csv", output_dir: str = "/output") -> None:
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(csv_path):
        # Check if any .csv file in /input
        csv_files = list(Path("/input").glob("*.csv")) if os.path.exists("/input") else []
        if csv_files:
            csv_path = str(csv_files[0])
        else:
            summary = {
                "status": "error",
                "error": f"Input file not found at {csv_path}",
                "total_deals": 0,
                "total_revenue": 0.0,
            }
            with open(os.path.join(output_dir, "sales_summary.json"), "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            with open(os.path.join(output_dir, "sales_report.md"), "w", encoding="utf-8") as f:
                f.write("# Báo cáo phân tích bán hàng\n\nKhông tìm thấy file dữ liệu đầu vào `/input/sales.csv`.\n")
            return

    total_deals = 0
    won_deals = 0
    lost_deals = 0
    open_deals = 0
    total_pipeline_value = 0.0
    won_revenue = 0.0
    stage_breakdown = {}

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_deals += 1
            
            # Extract deal value
            val = 0.0
            for k in ["deal_value", "value", "amount", "revenue", "price"]:
                if k in row and row[k]:
                    try:
                        val = float(str(row[k]).replace(",", "").replace("$", "").replace("VND", "").strip())
                        break
                    except ValueError:
                        pass
            
            total_pipeline_value += val

            # Extract status/stage
            stage = (row.get("stage") or row.get("status") or "new").strip().lower()
            stage_breakdown[stage] = stage_breakdown.get(stage, 0) + 1

            if stage in ["won", "closed_won", "success"]:
                won_deals += 1
                won_revenue += val
            elif stage in ["lost", "closed_lost", "failed"]:
                lost_deals += 1
            else:
                open_deals += 1

    win_rate = (won_deals / total_deals * 100.0) if total_deals > 0 else 0.0
    avg_deal_size = (won_revenue / won_deals) if won_deals > 0 else 0.0

    summary = {
        "status": "success",
        "total_deals": total_deals,
        "won_deals": won_deals,
        "lost_deals": lost_deals,
        "open_deals": open_deals,
        "win_rate_percent": round(win_rate, 2),
        "total_pipeline_value": round(total_pipeline_value, 2),
        "won_revenue": round(won_revenue, 2),
        "avg_deal_size": round(avg_deal_size, 2),
        "stage_breakdown": stage_breakdown,
    }

    # 1. Output structured JSON
    json_path = os.path.join(output_dir, "sales_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # 2. Output Markdown report
    md_path = os.path.join(output_dir, "sales_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Báo cáo Phân tích Dữ liệu Bán hàng (Sales Data Analysis)\n\n")
        f.write(f"- **Tổng số cơ hội / Deal:** {total_deals:,}\n")
        f.write(f"- **Số deal thành công (Won):** {won_deals:,} ({win_rate:.1f}% Win Rate)\n")
        f.write(f"- **Tổng doanh thu chốt:** {won_revenue:,.0f} VND\n")
        f.write(f"- **Giá trị trung bình mỗi deal:** {avg_deal_size:,.0f} VND\n")
        f.write(f"- **Tổng giá trị pipeline:** {total_pipeline_value:,.0f} VND\n\n")
        f.write("### Phân bổ theo giai đoạn (Stage Breakdown)\n\n")
        for stg, count in sorted(stage_breakdown.items(), key=lambda x: x[1], reverse=True):
            f.write(f"- **{stg.upper()}**: {count} deals\n")

    print(f"Sales analysis completed: {total_deals} deals analyzed, won revenue {won_revenue:,.0f} VND.")


if __name__ == "__main__":
    analyze_sales()
