"""
COSA Tools Core Interface & Presenter Contracts
Mọi công cụ tác vụ (Tool) trong hệ thống đều phải tuân thủ hợp đồng này (Structure.md Mục 10, 11, 12, 27).
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Mức độ rủi ro của Tool (CLAUDE.md Mục 11 & Structure.md Mục 27)"""
    LOW = "LOW"             # Tự động thực thi (ví dụ: web.search, filesystem.read nội bộ)
    MEDIUM = "MEDIUM"       # Ghi log, có thể thực thi theo chính sách (ví dụ: crm.create_lead)
    HIGH = "HIGH"           # BẮT BUỘC Founder Approval (ví dụ: deploy staging, shell command, mass email)
    CRITICAL = "CRITICAL"   # BẮT BUỘC Admin Approval 2 lớp (ví dụ: delete database, deploy production)


class ToolResult(BaseModel):
    """Hợp đồng đầu ra chuẩn hóa cho mọi Tool (Structure.md Mục 11)"""
    status: Literal["success", "error", "pending_approval"]
    data: Any = Field(default=None, description="Dữ liệu kết quả thực thi")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Thông tin metadata thực thi: duration_ms, cost_estimate, token_count"
    )
    error: Optional[str] = Field(default=None, description="Thông điệp lỗi nếu thất bại")
    presenter_payload: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Dữ liệu format sẵn cho Hologram Hub UI Presenter (không trả raw JSON)"
    )


class BasePresenter(ABC):
    """Giao diện Presenter định dạng hiển thị cho Hologram Hub (Structure.md Mục 12)"""

    @abstractmethod
    def format_timeline(self, result: ToolResult) -> Dict[str, Any]:
        """Format hiển thị ngắn gọn trên Live Trajectory Timeline"""
        pass

    @abstractmethod
    def format_inspector(self, result: ToolResult) -> Dict[str, Any]:
        """Format hiển thị chi tiết trong Artifacts / Details Inspector panel"""
        pass


class BaseTool(ABC):
    """Giao diện trừu tượng cơ sở cho toàn bộ Tools trong COSA (Structure.md Mục 10)"""
    id: str
    description: str
    risk_level: RiskLevel = RiskLevel.LOW
    permissions_required: List[str] = []
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """Hàm thực thi hành động tất định"""
        pass

    def format_presenter(self, result_data: Any) -> Dict[str, Any]:
        """Định dạng dữ liệu mặc định cho Presenter (có thể override trong subclass)"""
        return {
            "title": self.id,
            "status": "completed",
            "summary": str(result_data)[:200] if result_data else "No data returned"
        }
