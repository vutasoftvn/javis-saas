import concurrent.futures
import time
from datetime import datetime, timezone
import pytest

from core.snowflake import (
    SnowflakeGenerator,
    generate_snowflake_id,
    generate_snowflake_str,
    parse_snowflake,
    snowflake_to_datetime,
    CUSTOM_EPOCH,
)


def test_snowflake_uniqueness():
    generator = SnowflakeGenerator(node_id=1)
    ids = set()
    total_count = 10000

    for _ in range(total_count):
        new_id = generator.generate()
        assert new_id > 0
        ids.add(new_id)

    assert len(ids) == total_count, "Phải sinh đủ 10,000 IDs duy nhất không trùng lặp"


def test_snowflake_monotonicity_k_ordered():
    generator = SnowflakeGenerator(node_id=2)
    last_id = 0

    for _ in range(5000):
        new_id = generator.generate()
        assert new_id > last_id, f"Snowflake ID phải tăng dần theo thời gian ({new_id} > {last_id})"
        last_id = new_id


def test_snowflake_multithreaded_concurrency():
    generator = SnowflakeGenerator(node_id=3)
    num_threads = 8
    ids_per_thread = 2000
    all_ids = []

    def worker():
        local_ids = []
        for _ in range(ids_per_thread):
            local_ids.append(generator.generate())
        return local_ids

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker) for _ in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            all_ids.extend(f.result())

    assert len(all_ids) == num_threads * ids_per_thread
    assert len(set(all_ids)) == len(all_ids), "Không được có bất kỳ ID nào bị trùng khi sinh đa luồng"


def test_snowflake_parse_and_datetime():
    node_id = 42
    generator = SnowflakeGenerator(node_id=node_id)
    
    before_ms = int(time.time() * 1000)
    sf_id = generator.generate()
    after_ms = int(time.time() * 1000)

    parsed = parse_snowflake(sf_id)
    assert parsed["id"] == sf_id
    assert parsed["id_str"] == str(sf_id)
    assert parsed["node_id"] == node_id
    assert before_ms <= parsed["timestamp_ms"] <= after_ms

    dt = snowflake_to_datetime(sf_id)
    assert isinstance(dt, datetime)
    assert dt.tzinfo == timezone.utc


def test_generate_snowflake_str_convenience():
    id_str = generate_snowflake_str()
    assert isinstance(id_str, str)
    assert id_str.isdigit()
    assert len(id_str) >= 15  # Chuỗi 64-bit ID thường dài từ 17-19 ký tự số
