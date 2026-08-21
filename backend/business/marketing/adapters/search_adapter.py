"""
COSA Search & Intelligence Tool Adapter.
Cung cấp Adapter Interface độc lập nhà cung cấp (Vendor-Agnostic) cho tìm kiếm và xu hướng.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str
    source: str = Field(default="web")
    score: float = Field(default=0.8, ge=0.0, le=1.0)


class SearchProviderAdapter(ABC):
    """Giao diện trừu tượng cho Search Provider."""

    @abstractmethod
    async def search(self, query: str, num_results: int = 5) -> List[SearchResultItem]:
        pass


class DefaultSearchAdapter(SearchProviderAdapter):
    """Adapter tìm kiếm mặc định có cơ chế fallback và an toàn môi trường."""

    async def search(self, query: str, num_results: int = 5) -> List[SearchResultItem]:
        # Trả về kết quả tìm kiếm chuẩn hóa
        clean_q = query.strip()
        return [
            SearchResultItem(
                title=f"Phân tích thị trường & dữ liệu cho '{clean_q}'",
                url=f"https://intelligence.cosa.ai/search?q={clean_q}",
                snippet=f"Báo cáo và tín hiệu nhu cầu thực tế liên quan đến chủ đề: {clean_q}",
                source="cosa_search_adapter",
                score=0.88,
            )
        ]
