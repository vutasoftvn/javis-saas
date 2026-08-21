import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from core.snowflake import generate_snowflake_id
from business.legal.models import LegalChecklistItem, LegalObligation
from workforce.memory.models import AgentMemoryEntry


def analyze_contract_risks(
    contract_text: str,
    contract_type: str = "COMMERCIAL_SERVICE",
) -> Dict[str, Any]:
    """Phân tích rủi ro điều khoản hợp đồng bằng thuật toán AI Legal Specialist."""
    text_lower = contract_text.lower()
    risks: List[Dict[str, Any]] = []
    recommendations: List[str] = []

    # 1. Rủi ro Phạt vi phạm (Penalty Risks)
    penalty_match = re.search(r"phạt\s+(\d+[\.,]?\d*)\s*%", text_lower)
    if penalty_match:
        penalty_val = float(penalty_match.group(1).replace(",", "."))
        if penalty_val > 8.0:
            risks.append({
                "category": "PENALTY",
                "severity": "HIGH",
                "clause_snippet": f"Mức phạt vi phạm {penalty_val}% giá trị hợp đồng",
                "issue": f"Mức phạt {penalty_val}% vượt quá trần 8% theo Điều 301 Luật Thương Mại Việt Nam (trừ hợp đồng xây dựng).",
                "recommendation": "Điều chỉnh mức phạt vi phạm tối đa không quá 8% phần nghĩa vụ hợp đồng bị vi phạm.",
            })
    elif "phạt không giới hạn" in text_lower or "bồi thường toàn bộ thiệt hại gián tiếp" in text_lower:
        risks.append({
            "category": "PENALTY",
            "severity": "HIGH",
            "clause_snippet": "Bồi thường thiệt hại gián tiếp không giới hạn",
            "issue": "Trách nhiệm bồi thường vô hạn có thể đe dọa dòng tiền và sự tồn vong của doanh nghiệp.",
            "recommendation": "Giới hạn trần trách nhiệm bồi thường (Liability Cap) ở mức 100% tổng giá trị hợp đồng.",
        })

    # 2. Rủi ro Thanh toán (Payment Terms)
    if "thanh toán sau 90 ngày" in text_lower or "thanh toán sau 120 ngày" in text_lower:
        risks.append({
            "category": "PAYMENT",
            "severity": "MEDIUM",
            "clause_snippet": "Thời hạn thanh toán dài (90-120 ngày)",
            "issue": "Thời hạn thanh toán quá dài ảnh hưởng trực tiếp đến chỉ số Runway và dòng tiền hoạt động.",
            "recommendation": "Đàm phán rút ngắn thời hạn thanh toán xuống 15-30 ngày kể từ ngày nghiệm thu hoặc chia nhỏ thành từng đợt tạm ứng.",
        })

    # 3. Rủi ro Quyền Sở hữu trí tuệ (Intellectual Property - IP)
    if "chuyển giao toàn bộ quyền tác giả" in text_lower or "toàn quyền sở hữu mọi mã nguồn và công nghệ gốc" in text_lower:
        risks.append({
            "category": "INTELLECTUAL_PROPERTY",
            "severity": "HIGH",
            "clause_snippet": "Chuyển giao toàn bộ quyền công nghệ gốc",
            "issue": "Nguy cơ mất quyền sở hữu đối với các thư viện cốt lõi hoặc nền tảng SaaS dùng chung.",
            "recommendation": "Quy định rõ khách hàng chỉ sở hữu sản phẩm tùy biến riêng biệt; toàn bộ nền tảng cốt lõi (Core IP) thuộc quyền sở hữu độc quyền của công ty.",
        })

    # 4. Rủi ro Đơn phương chấm dứt hợp đồng (Termination)
    if "chấm dứt bất kỳ lúc nào mà không cần báo trước" in text_lower:
        risks.append({
            "category": "TERMINATION",
            "severity": "HIGH",
            "clause_snippet": "Quyền chấm dứt không cần báo trước",
            "issue": "Gây bất lợi lớn cho việc phân bổ nhân sự và chi phí hạ tầng đã cam kết trước.",
            "recommendation": "Quy định thời hạn thông báo trước bằng văn bản tối thiểu 30 ngày và thanh toán đầy đủ các phần việc đã hoàn thành.",
        })

    # 5. Rủi ro Tài phán & Giải quyết tranh chấp (Jurisdiction)
    if "tòa án nước ngoài" in text_lower or "trọng tài quốc tế siac" in text_lower:
        risks.append({
            "category": "JURISDICTION",
            "severity": "MEDIUM",
            "clause_snippet": "Giải quyết tranh chấp tại trọng tài/tòa án nước ngoài",
            "issue": "Chi phí theo kiện quốc tế rất tốn kém cho doanh nghiệp siêu nhỏ/startup.",
            "recommendation": "Ưu tiên chọn Trung tâm Trọng tài Quốc tế Việt Nam (VIAC) hoặc Tòa án nhân dân có thẩm quyền tại Việt Nam.",
        })

    # Tính điểm an toàn pháp lý (Safety Score: 0 - 100)
    high_count = sum(1 for r in risks if r["severity"] == "HIGH")
    med_count = sum(1 for r in risks if r["severity"] == "MEDIUM")
    base_score = 100 - (high_count * 25) - (med_count * 10)
    safety_score = max(20, min(100, base_score))

    if not risks:
        recommendations.append("Hợp đồng chưa phát hiện các điều khoản xung đột nghiêm trọng với pháp luật thương mại hiện hành.")
        recommendations.append("Đảm bảo chữ ký số hợp lệ và đầy đủ phụ lục kỹ thuật/SLA đính kèm.")
    else:
        for r in risks:
            recommendations.append(r["recommendation"])

    return {
        "status": "success",
        "contract_type": contract_type,
        "safety_score": safety_score,
        "risk_level": "CAO" if safety_score < 60 else ("TRUNG BÌNH" if safety_score < 85 else "AN TOÀN"),
        "total_risks_found": len(risks),
        "risks": risks,
        "recommendations": recommendations,
        "reviewed_at": datetime.utcnow().isoformat(),
    }


def list_legal_checklist(db: Session, workspace_id: int) -> List[Dict[str, Any]]:
    """Lấy danh sách các hạng mục tuân thủ pháp lý của workspace."""
    items = (
        db.query(LegalChecklistItem)
        .filter(LegalChecklistItem.workspace_id == workspace_id)
        .order_by(LegalChecklistItem.created_at.desc())
        .all()
    )

    results = []
    for it in items:
        results.append({
            "id": str(it.id),
            "title": it.title,
            "status": it.status,
            "created_at": it.created_at.isoformat() if it.created_at else None,
        })
    return results


def list_legal_obligations(db: Session, workspace_id: int) -> List[Dict[str, Any]]:
    """Lấy danh sách nghĩa vụ pháp lý có thời hạn."""
    obligations = (
        db.query(LegalObligation)
        .filter(LegalObligation.workspace_id == workspace_id)
        .order_by(LegalObligation.due_at.asc().nullslast())
        .all()
    )

    results = []
    for ob in obligations:
        results.append({
            "id": str(ob.id),
            "title": ob.title,
            "description": ob.description,
            "due_at": ob.due_at.isoformat() if ob.due_at else None,
            "status": ob.status,
        })
    return results


def record_l4_pattern_lesson(
    db: Session,
    workspace_id: int,
    domain: str,
    lesson_text: str,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Ghi nhận một bài học kinh nghiệm vào L4 Pattern Learning Memory."""
    mem_id = generate_snowflake_id()
    mem = AgentMemoryEntry(
        id=mem_id,
        workspace_id=workspace_id,
        layer="L4_LEARNING",
        key=f"pattern:{domain}:{mem_id}",
        value_jsonb={
            "domain": domain,
            "lesson": lesson_text,
            "tags": tags or [],
            "recorded_at": datetime.utcnow().isoformat(),
        },
        relevance_score=1.0,
    )
    db.add(mem)
    db.commit()
    db.refresh(mem)

    return {
        "status": "success",
        "memory_id": str(mem.id),
        "layer": "L4",
        "domain": domain,
        "lesson": lesson_text,
    }
