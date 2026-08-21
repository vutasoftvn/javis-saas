import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class StructuredWorkProductOutput(BaseModel):
    title: str
    product_type: str
    summary: str
    content_markdown: str
    artifacts: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class WorkProductTransformer:
    """Chuyển đổi chuỗi phản hồi thô (raw text output) của Agent thành Work Product có cấu trúc."""

    @classmethod
    def transform(
        cls,
        raw_content: str,
        task_title: Optional[str] = None,
        agent_key: Optional[str] = None,
    ) -> StructuredWorkProductOutput:
        lines = [line for line in raw_content.strip().splitlines()]
        
        # 1. Trích xuất Title
        title = task_title or "Sản phẩm bàn giao tác vụ"
        for line in lines[:5]:
            clean = line.strip()
            if clean.startswith("# "):
                title = clean[2:].strip()
                break
            elif clean.startswith("## "):
                title = clean[3:].strip()
                break

        # 2. Xác định Loại sản phẩm (Product Type)
        product_type = "DOCUMENT"
        upper_content = raw_content.upper()
        if "BÁO CÁO TÀI CHÍNH" in upper_content or "DOANH THU" in upper_content or "FINANCIAL" in upper_content:
            product_type = "FINANCIAL_REPORT"
        elif "DECISION RECORD" in upper_content or "ADR" in upper_content:
            product_type = "DECISION_RECORD"
        elif "TACTIC" in upper_content or "12WY" in upper_content:
            product_type = "TACTIC_DELIVERABLE"
        elif "```diff" in raw_content or "```python" in raw_content or "```sql" in raw_content:
            product_type = "CODE_DIFF"

        # 3. Trích xuất Executive Summary
        summary = ""
        summary_match = re.search(r"(?:Tóm tắt|Summary|Tổng quan)[:\n\s]+([^\n#]+(?:\n[^\n#]+){0,2})", raw_content, re.IGNORECASE)
        if summary_match:
            summary = summary_match.group(1).strip()
        else:
            # Lấy 2 dòng văn bản đầu tiên không phải tiêu đề
            non_heading = [l for l in lines if not l.startswith("#") and l.strip()]
            summary = " ".join(non_heading[:2])[:250] if non_heading else "Hoàn thành tác vụ theo đúng đặc tả."

        # 4. Trích xuất Artifacts / Code Blocks
        artifacts = []
        code_blocks = re.findall(r"```([a-zA-Z0-9_\-]+)?\n(.*?)```", raw_content, re.DOTALL)
        for idx, (lang, code) in enumerate(code_blocks, start=1):
            artifacts.append({
                "index": idx,
                "type": "code_snippet",
                "language": lang or "text",
                "content_preview": code.strip()[:100] + ("..." if len(code.strip()) > 100 else ""),
                "size_bytes": len(code.encode("utf-8")),
            })

        return StructuredWorkProductOutput(
            title=title,
            product_type=product_type,
            summary=summary,
            content_markdown=raw_content,
            artifacts=artifacts,
            metadata={
                "agent_key": agent_key,
                "raw_length": len(raw_content),
                "has_code_artifacts": len(artifacts) > 0,
            },
        )
