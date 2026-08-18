import pytest
from pathlib import Path
from app.workforce.skills.skill_loader import DynamicSkillLoader, PhysicalSkillDocument


def test_physical_skills_scanning():
    skills_dir = Path(__file__).parent.parent / "workforce" / "skills"
    loader = DynamicSkillLoader(None, str(skills_dir))
    skills = loader.scan_physical_skills()

    assert len(skills) >= 6
    skill_ids = [s.skill_id for s in skills]
    assert "sales.lead_qualification" in skill_ids
    assert "sales.sales_follow_up" in skill_ids
    assert "marketing.campaign_planning" in skill_ids
    assert "finance.circular_58_vn" in skill_ids
    assert "legal.contract_review_vn" in skill_ids
    assert "engineering.code_review" in skill_ids


def test_on_demand_skill_injection():
    skills_dir = Path(__file__).parent.parent / "workforce" / "skills"
    loader = DynamicSkillLoader(None, str(skills_dir))

    # Test legal query
    legal_skills = loader.load_relevant_skills_for_task(
        "Rà soát hợp đồng kinh tế và kiểm tra điều khoản phạt vi phạm theo luật thương mại VN",
        department="legal"
    )
    assert len(legal_skills) > 0
    assert legal_skills[0].skill_id == "legal.contract_review_vn"

    # Test finance query
    finance_skills = loader.load_relevant_skills_for_task(
        "Định khoản hóa đơn GTGT và kiểm tra chi phí hợp lý theo thông tư kế toán",
        department="finance"
    )
    assert len(finance_skills) > 0
    assert finance_skills[0].skill_id == "finance.circular_58_vn"
