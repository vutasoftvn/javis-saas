"""
COSA Business Core - Base Domain Contracts
Pure Python Domain Entity & Repository abstractions.
Nghiêm cấm import bất kỳ AI/LLM dependencies nào trong package này (CLAUDE.md Rule 5 & Structure.md Rule 5).
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import uuid4
from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseDomainEntity(BaseModel):
    """Lớp cơ sở cho tất cả thực thể nghiệp vụ của COSA (Company, Project, Task, OKR, CRM...)"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True


class BaseValueObject(BaseModel):
    """Lớp cơ sở cho các Value Objects bất biến trong Domain"""
    class Config:
        frozen = True


class IRepository(ABC, Generic[T]):
    """Giao diện Repository trừu tượng cho tầng Persistence"""

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Lấy thực thể theo ID"""
        pass

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Lấy danh sách thực thể có phân trang"""
        pass

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Lưu hoặc cập nhật thực thể"""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Xóa thực thể"""
        pass
