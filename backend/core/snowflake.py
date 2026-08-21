import os
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, Union

# Epoch khởi tạo tùy chỉnh: 2026-01-01 00:00:00 UTC (in milliseconds)
CUSTOM_EPOCH = 1767225600000

# Cấu hình bit: 41 bits timestamp, 10 bits node id, 12 bits sequence
NODE_ID_BITS = 10
SEQUENCE_BITS = 12

MAX_NODE_ID = (1 << NODE_ID_BITS) - 1        # 1023
MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1      # 4095

TIMESTAMP_SHIFT = NODE_ID_BITS + SEQUENCE_BITS  # 22
NODE_ID_SHIFT = SEQUENCE_BITS                   # 12


class SnowflakeGenerator:
    """Bộ sinh Snowflake ID 64-bit chuẩn hiệu năng cao, thread-safe (§106, §167).

    Cấu trúc:
    - 1 bit sign (luôn bằng 0 cho số nguyên dương 64-bit)
    - 41 bits timestamp mili-giây kể từ Custom Epoch (hoạt động liên tục ~69.7 năm)
    - 10 bits Node/Worker ID (tối đa 1024 nodes phân tán)
    - 12 bits Sequence counter (tối đa 4096 IDs/mili-giây trên mỗi node)
    """

    def __init__(self, node_id: int = 1, epoch: int = CUSTOM_EPOCH):
        if not (0 <= node_id <= MAX_NODE_ID):
            raise ValueError(f"Node ID phải nằm trong khoảng từ 0 đến {MAX_NODE_ID}")
        self.node_id = node_id
        self.epoch = epoch
        self.sequence = 0
        self.last_timestamp = -1
        self._lock = threading.Lock()

    def _current_timestamp_ms(self) -> int:
        return int(time.time() * 1000)

    def _wait_next_millis(self, last_timestamp: int) -> int:
        timestamp = self._current_timestamp_ms()
        while timestamp <= last_timestamp:
            time.sleep(0.0001)
            timestamp = self._current_timestamp_ms()
        return timestamp

    def generate(self) -> int:
        with self._lock:
            timestamp = self._current_timestamp_ms()

            if timestamp < self.last_timestamp:
                # Đồng hồ máy chủ bị lùi (Clock drift/NTP step) - đợi để đồng bộ
                time_diff = self.last_timestamp - timestamp
                if time_diff < 5000:
                    time.sleep(time_diff / 1000.0)
                    timestamp = self._current_timestamp_ms()
                else:
                    raise RuntimeError(f"Phát hiện đồng hồ lùi quá lớn ({time_diff}ms)")

            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & MAX_SEQUENCE
                if self.sequence == 0:
                    # Tràn sequence trong cùng 1 mili-giây -> đợi sang mili-giây kế tiếp
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            # Ghép các trường bit thành số nguyên 64-bit
            snowflake_id = (
                ((timestamp - self.epoch) << TIMESTAMP_SHIFT)
                | (self.node_id << NODE_ID_SHIFT)
                | self.sequence
            )
            return snowflake_id


def _get_default_node_id() -> int:
    try:
        node_env = os.environ.get("NODE_ID") or os.environ.get("WORKER_ID")
        if node_env:
            return int(node_env) & MAX_NODE_ID
    except Exception:
        pass
    return 1


_global_generator = SnowflakeGenerator(node_id=_get_default_node_id())


def generate_snowflake_id() -> int:
    """Sinh Snowflake ID 64-bit dạng số nguyên dương."""
    return _global_generator.generate()


def generate_snowflake_str() -> str:
    """Sinh Snowflake ID dạng chuỗi (String) an toàn cho REST JSON & Flutter Web."""
    return str(_global_generator.generate())


def parse_snowflake(snowflake_id: Union[int, str], epoch: int = CUSTOM_EPOCH) -> Dict[str, Any]:
    """Phân tích và trích xuất các thành phần từ một Snowflake ID."""
    num_id = int(snowflake_id)
    sequence = num_id & MAX_SEQUENCE
    node_id = (num_id >> NODE_ID_SHIFT) & MAX_NODE_ID
    timestamp_ms = (num_id >> TIMESTAMP_SHIFT) + epoch
    dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)

    return {
        "id": num_id,
        "id_str": str(num_id),
        "timestamp_ms": timestamp_ms,
        "datetime_utc": dt.isoformat(),
        "node_id": node_id,
        "sequence": sequence,
    }


def snowflake_to_datetime(snowflake_id: Union[int, str], epoch: int = CUSTOM_EPOCH) -> datetime:
    """Chuyển đổi Snowflake ID thành datetime UTC mà không cần truy vấn cột created_at."""
    num_id = int(snowflake_id)
    timestamp_ms = (num_id >> TIMESTAMP_SHIFT) + epoch
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
