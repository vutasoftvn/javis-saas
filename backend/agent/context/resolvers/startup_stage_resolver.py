"""
COSA Startup Stage Context Resolver
Giai đoạn khởi nghiệp là ngữ cảnh quan trọng định hướng lời khuyên của Agent (Structure.md Mục 46).
"""
from typing import Any, Dict


class StartupStageResolver:
    """Nạp thông tin giai đoạn phát triển của Startup (IDEA, MVP, PMF, GROWTH)"""

    @staticmethod
    async def resolve(stage_name: str = "MVP") -> Dict[str, Any]:
        stages_guide = {
            "IDEA": "Tập trung khám phá vấn đề (Problem Discovery) & phỏng vấn khách hàng JTBD.",
            "MVP": "Tập trung xây dựng giải pháp cốt lõi và kiểm chứng tính khả thi.",
            "PMF": "Tập trung đo lường độ gắn kết (Retention), NPS và sẵn sàng trả tiền.",
            "GROWTH": "Tập trung mở rộng kênh Acquisition, tối ưu CAC/LTV và tuyển dụng."
        }
        return {
            "current_stage": stage_name,
            "strategic_focus": stages_guide.get(stage_name.upper(), "Tập trung tạo giá trị cốt lõi."),
            "prohibited_actions": "Không áp dụng chiến thuật Growth quy mô lớn cho giai đoạn tiền PMF."
        }
