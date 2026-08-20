"""
COSA Task Executors Core Contracts
Executor là hạ tầng thực thi bên ngoài (Claude Code, Codex, Sandboxed Shell, MCP, n8n)
Executor KHÔNG phải là Agent Runtime (CLAUDE.md Mục 7 & Structure.md Mục 31, 32, 33).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class BuildSpec(BaseModel):
    """Bản đặc tả kỹ thuật cho các tác vụ lập trình / tự động hóa lớn (Structure.md Mục 33)"""
    task_id: str = Field(..., description="Mã định danh tác vụ")
    project_name: str = Field(..., description="Tên dự án liên quan")
    objective: str = Field(..., description="Mục tiêu cụ thể cần đạt được")
    requirements: List[str] = Field(default_factory=list, description="Danh sách yêu cầu kỹ thuật chi tiết")
    constraints: List[str] = Field(default_factory=list, description="Ràng buộc bắt buộc tuân thủ")
    allowed_paths: List[str] = Field(default_factory=list, description="Các thư mục/file được phép chỉnh sửa")
    forbidden_paths: List[str] = Field(default_factory=list, description="Các thư mục/file nghiêm cấm can thiệp")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Tiêu chuẩn nghiệm thu")
    tests_to_run: List[str] = Field(default_factory=list, description="Các lệnh kiểm thử cần chạy")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Thông tin mở rộng")


class ExecutorResult(BaseModel):
    """Kết quả thực thi tác vụ từ Executor"""
    status: Literal["success", "error", "aborted"]
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    artifacts_created: List[str] = Field(default_factory=list, description="Danh sách file/artifact vừa sinh")
    diff_patch: Optional[str] = Field(default=None, description="Code diff chi tiết (nếu có)")
    duration_ms: int = 0


class BaseExecutor(ABC):
    """Giao diện trừu tượng cơ sở cho toàn bộ Executors"""
    id: str
    name: str

    @abstractmethod
    async def execute(self, spec: BuildSpec, workspace_path: str) -> ExecutorResult:
        """Hàm nhận BuildSpec và thực thi tác vụ trong Workspace an toàn"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Kiểm tra tính sẵn sàng của Executor (ví dụ: CLI binary, API endpoint)"""
        pass
