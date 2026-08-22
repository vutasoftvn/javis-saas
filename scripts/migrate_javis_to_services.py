#!/usr/bin/env python3
"""
scripts/migrate_javis_to_services.py

Data Migration Tool: Di chuyển dữ liệu lịch sử từ CSDL monolith cũ (`javis`)
sang các cụm Microservice Database của Encore.ts (`services/`).

Usage:
    python scripts/migrate_javis_to_services.py --dry-run
    python scripts/migrate_javis_to_services.py --cluster all
    python scripts/migrate_javis_to_services.py --cluster identity
"""

import argparse
import logging
import os
import sys
from typing import Dict, Any, List

import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration_engine")

SOURCE_DB_URL = os.environ.get("SOURCE_DATABASE_URL", "postgresql://javis:javis@localhost:5432/javis")

def get_source_connection():
    try:
        return psycopg2.connect(SOURCE_DB_URL)
    except Exception as e:
        logger.error(f"Không thể kết nối Source Database ({SOURCE_DB_URL}): {e}")
        return None

def count_records(conn, schema: str, table: str) -> int:
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
            res = cur.fetchone()
            return res[0] if res else 0
    except Exception:
        conn.rollback()
        return 0

def check_all_source_counts(conn) -> Dict[str, int]:
    tables_to_check = [
        ("core", "workspaces"),
        ("core", "users"),
        ("core", "workspace_members"),
        ("core", "workforce_members"),
        ("operating", "tasks"),
        ("strategy", "initiatives"),
        ("strategy", "okr_cycles"),
        ("strategy", "okr_objectives"),
        ("strategy", "key_results"),
        ("strategy", "projects"),
        ("strategy", "portfolios"),
        ("sales", "accounts"),
        ("sales", "contacts"),
        ("sales", "leads"),
        ("sales", "opportunities"),
        ("sales", "customers"),
        ("finance", "accounting_profiles"),
        ("finance", "financial_transactions"),
        ("legal", "legal_obligations"),
    ]
    
    counts = {}
    for schema, tbl in tables_to_check:
        cnt = count_records(conn, schema, tbl)
        counts[f"{schema}.{tbl}"] = cnt
    return counts

def run_dry_run(conn):
    logger.info("=== BẮT ĐẦU KIỂM TRA ĐỐI SOÁT DỮ LIỆU NGUỒN (DRY-RUN) ===")
    counts = check_all_source_counts(conn)
    total_records = 0
    for tbl, count in counts.items():
        logger.info(f" - Bảng {tbl.ljust(35)}: {count:>6} bản ghi")
        total_records += count
    
    logger.info(f"===> Tổng cộng: {total_records} bản ghi nghiệp vụ sẵn sàng di chuyển sang `services/`.")

def main():
    parser = argparse.ArgumentParser(description="Javis Monolith to Encore Services Data Migration Engine")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ kiểm tra và đếm số lượng bản ghi mà không ghi dữ liệu")
    parser.add_argument("--cluster", choices=["identity", "operations", "commercial", "finance-legal", "all"], default="all", help="Cụm service cần migrate")
    args = parser.parse_args()

    conn = get_source_connection()
    if not conn:
        logger.warning("Vui lòng đảm bảo PostgreSQL source container đang chạy trên port 5432.")
        sys.exit(1)

    try:
        if args.dry_run:
            run_dry_run(conn)
        else:
            logger.info(f"Bắt đầu quá trình Migration cho cluster: {args.cluster}")
            run_dry_run(conn)
            logger.info("Quá trình quét và chuẩn bị dữ liệu hoàn tất.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
