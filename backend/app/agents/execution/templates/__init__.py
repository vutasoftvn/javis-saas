from pathlib import Path


def get_sales_analysis_script() -> str:
    script_path = Path(__file__).parent / "analyze_sales.py"
    return script_path.read_text(encoding="utf-8")


def get_finance_analysis_script() -> str:
    script_path = Path(__file__).parent / "analyze_finance.py"
    return script_path.read_text(encoding="utf-8")
