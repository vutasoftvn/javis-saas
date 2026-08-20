"""
COSA Skills Core Contracts
Skill là kiến thức/hướng dẫn để agent biết cách thực hiện một năng lực (Structure.md Mục 9).
Skill KHÔNG phải agent.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    """Khai báo metadata và định nghĩa của một Skill"""
    id: str = Field(..., description="Mã định danh duy nhất của Skill (ví dụ: market-research, tt58-audit)")
    name: str = Field(..., description="Tên kỹ năng")
    domain: str = Field(..., description="Lĩnh vực chuyên môn: startup, marketing, sales, finance, legal, management")
    description: str = Field(default="", description="Mô tả kỹ năng")
    instruction_path: Optional[str] = Field(default=None, description="Đường dẫn file Markdown chứa hướng dẫn chi tiết")
    required_tools: List[str] = Field(default_factory=list, description="Danh sách mã Tools cần thiết để thực hiện Skill")
    version: str = Field(default="1.0.0", description="Phiên bản của Skill")


class BaseSkill(ABC):
    """Giao diện trừu tượng cơ sở cho Skill Execution Engine"""
    definition: SkillDefinition

    @abstractmethod
    async def load_instructions(self) -> str:
        """Nạp nội dung hướng dẫn nghiệp vụ của Skill từ local files (Markdown)"""
        pass

    @abstractmethod
    def validate_prerequisites(self, available_tools: List[str]) -> bool:
        """Kiểm tra xem Runtime có đủ Tools cần thiết để thực thi Skill này hay không"""
        pass
