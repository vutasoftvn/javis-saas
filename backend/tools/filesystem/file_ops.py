"""
COSA Filesystem Tools (Sandboxed Workspace Operations)
"""
import os
from typing import Any, Dict
from tools.base import BaseTool, RiskLevel, ToolResult


class ReadFileTool(BaseTool):
    id = "filesystem.read"
    description = "Đọc nội dung file an toàn trong Workspace"
    risk_level = RiskLevel.LOW
    permissions_required = ["filesystem.read"]
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Đường dẫn file tương đối trong workspace"}
        },
        "required": ["file_path"]
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        file_path = input_data.get("file_path", "")
        return ToolResult(
            status="success",
            data={"file_path": file_path, "content": f"# Mock Content for {file_path}", "size_bytes": 1024},
            presenter_payload={
                "view_type": "file_preview_card",
                "title": f"Đọc file: {os.path.basename(file_path)}",
                "file_path": file_path,
                "size": "1.0 KB"
            }
        )


class WriteFileTool(BaseTool):
    id = "filesystem.write"
    description = "Ghi nội dung ra file trong Workspace"
    risk_level = RiskLevel.MEDIUM
    permissions_required = ["filesystem.write"]
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Đường dẫn file cần ghi"},
            "content": {"type": "string", "description": "Nội dung cần ghi"}
        },
        "required": ["file_path", "content"]
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        file_path = input_data.get("file_path", "")
        content = input_data.get("content", "")
        return ToolResult(
            status="success",
            data={"file_path": file_path, "bytes_written": len(content.encode("utf-8"))},
            presenter_payload={
                "view_type": "file_created_card",
                "title": f"Đã lưu file: {os.path.basename(file_path)}",
                "file_path": file_path,
                "summary": f"Ghi thành công {len(content)} ký tự"
            }
        )


class ListDirectoryTool(BaseTool):
    id = "filesystem.list_dir"
    description = "Liệt kê danh sách file và thư mục"
    risk_level = RiskLevel.LOW
    permissions_required = ["filesystem.read"]
    input_schema = {
        "type": "object",
        "properties": {
            "directory_path": {"type": "string", "default": "."}
        }
    }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        directory_path = input_data.get("directory_path", ".")
        entries = ["src", "docs", "tests", "README.md", "pyproject.toml"]
        return ToolResult(
            status="success",
            data={"directory": directory_path, "entries": entries},
            presenter_payload={
                "view_type": "directory_list_card",
                "title": f"Thư mục: {directory_path}",
                "count": len(entries),
                "items": entries
            }
        )
