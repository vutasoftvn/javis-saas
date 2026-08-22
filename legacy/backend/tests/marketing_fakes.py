"""Session giả cho test Marketing OS.

Model marketing dùng JSONB nên không dựng được SQLite in-memory; còn `MagicMock()` trần
thì mọi `db.query(...)` đều trả về cùng một đối tượng nên không phân biệt được truy vấn
theo Brain, Campaign hay Approval - đúng loại lỗi tenancy cần test. FakeDb dispatch theo
model class và áp default của cột khi flush/commit để bản ghi giống hàng đã insert thật.
"""
from core.snowflake import generate_snowflake_id
from typing import Any, Dict, List, Type

from sqlalchemy import inspect as sa_inspect


class FakeQuery:
    def __init__(self, results: List[Any]):
        self._results = list(results)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, n: int):
        self._results = self._results[:n]
        return self

    def all(self) -> List[Any]:
        return list(self._results)

    def first(self):
        return self._results[0] if self._results else None

    def count(self) -> int:
        return len(self._results)


class FakeDb:
    def __init__(self, data: Dict[Type, List[Any]] | None = None):
        self.data: Dict[Type, List[Any]] = {k: list(v) for k, v in (data or {}).items()}
        self.added: List[Any] = []
        self.deleted: List[Any] = []
        self.commits = 0

    # --- SQLAlchemy Session surface used by the marketing module ---

    def query(self, model):
        return FakeQuery(self.data.get(model, []))

    def add(self, obj):
        self.added.append(obj)
        self.data.setdefault(type(obj), []).append(obj)

    def delete(self, obj):
        self.deleted.append(obj)
        bucket = self.data.get(type(obj), [])
        if obj in bucket:
            bucket.remove(obj)

    def flush(self):
        for obj in self.added:
            self._apply_defaults(obj)

    def commit(self):
        self.commits += 1
        self.flush()

    def refresh(self, obj):
        self._apply_defaults(obj)

    # --- helpers ---

    @staticmethod
    def _apply_defaults(obj):
        try:
            mapper = sa_inspect(type(obj))
        except Exception:
            return
        # mapper.columns được khoá theo TÊN THUỘC TÍNH ORM, không phải tên cột - quan
        # trọng vì marketing map meta_data->metadata và current_value->metric_value.
        for attr_name, column in mapper.columns.items():
            if getattr(obj, attr_name, None) is not None:
                continue
            default = column.default
            if default is None:
                continue
            value = default.arg
            setattr(obj, attr_name, value(None) if callable(value) else value)

    def of_type(self, model) -> List[Any]:
        return [o for o in self.added if isinstance(o, model)]


def new_id() -> int:
    return generate_snowflake_id()
