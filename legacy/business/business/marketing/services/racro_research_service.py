"""
COSA RACRO Research Service.
Hiện thực hóa 3 Capabilities của Khối RESEARCH:
1. Market Intelligence
2. Competitor Intelligence
3. Demand Intelligence
Và cầu nối Evidence Graph Bridge: Signal -> EvidenceItem -> Assumption.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from business.marketing.schemas.racro_contracts import MarketingSignal
from business.marketing.adapters.search_adapter import SearchProviderAdapter, DefaultSearchAdapter
from founder_os.strategy.models import EvidenceItem
from core.snowflake import generate_snowflake_id


class RACROResearchService:
    def __init__(self, search_adapter: Optional[SearchProviderAdapter] = None):
        self.search_adapter = search_adapter or DefaultSearchAdapter()

    async def analyze_market_intelligence(
        self,
        workspace_id: int,
        topic: str,
        project_id: Optional[int] = None,
        industry: Optional[str] = None,
    ) -> List[MarketingSignal]:
        """Nghiên cứu quy mô thị trường, phân khúc khách hàng và Jobs-to-be-Done (§3.1 Spec)."""
        search_results = await self.search_adapter.search(f"market size trend {topic} {industry or ''}")
        
        signals: List[MarketingSignal] = []
        for idx, item in enumerate(search_results):
            sig_id = f"sig_mkt_{generate_snowflake_id()}"
            signals.append(
                MarketingSignal(
                    id=sig_id,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    source_type="market_report",
                    source_url=item.url,
                    title=f"Báo cáo thị trường: {topic}",
                    summary=item.snippet,
                    confidence=item.score,
                    related_segment=industry or "General Market",
                    observed_at=datetime.utcnow(),
                    raw_payload={"query": topic, "provider": item.source},
                )
            )
        return signals

    async def analyze_competitor_intelligence(
        self,
        workspace_id: int,
        competitor_name: str,
        project_id: Optional[int] = None,
        competitor_url: Optional[str] = None,
    ) -> List[MarketingSignal]:
        """Theo dõi động thái, giá bán, chiến dịch và cấu trúc offer của đối thủ (§3.2 Spec)."""
        search_results = await self.search_adapter.search(f"pricing offer features {competitor_name}")
        
        signals: List[MarketingSignal] = []
        for idx, item in enumerate(search_results):
            sig_id = f"sig_cmp_{generate_snowflake_id()}"
            signals.append(
                MarketingSignal(
                    id=sig_id,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    source_type="competitor",
                    source_url=competitor_url or item.url,
                    title=f"Tín hiệu đối thủ: {competitor_name}",
                    summary=f"Quan sát về chính sách giá/offer của đối thủ {competitor_name}: {item.snippet}",
                    confidence=0.85,
                    related_hypothesis=f"Đối thủ {competitor_name} đang tập trung phân khúc tương tự",
                    observed_at=datetime.utcnow(),
                    raw_payload={"competitor": competitor_name, "url": competitor_url},
                )
            )
        return signals

    async def detect_demand_signals(
        self,
        workspace_id: int,
        keywords: List[str],
        project_id: Optional[int] = None,
    ) -> List[MarketingSignal]:
        """Thu thập tín hiệu nhu cầu thực tế (Demand Signals) từ tìm kiếm và thị trường (§3.3 Spec)."""
        signals: List[MarketingSignal] = []
        for kw in keywords:
            search_results = await self.search_adapter.search(f"high intent search {kw}")
            for item in search_results:
                sig_id = f"sig_dmd_{generate_snowflake_id()}"
                signals.append(
                    MarketingSignal(
                        id=sig_id,
                        workspace_id=workspace_id,
                        project_id=project_id,
                        source_type="search",
                        source_url=item.url,
                        title=f"Nhu cầu tăng đối với '{kw}'",
                        summary=f"Phát hiện xu hướng tìm kiếm và nhu cầu giải pháp: {kw}. {item.snippet}",
                        confidence=0.9,
                        related_segment="In-market Buyers",
                        observed_at=datetime.utcnow(),
                        raw_payload={"keyword": kw},
                    )
                )
        return signals

    def promote_signal_to_evidence(
        self,
        signal: MarketingSignal,
        user_id: int,
        db: Session,
    ) -> EvidenceItem:
        """Cầu nối Evidence-First: Founder phê duyệt chuyển MarketingSignal thành EvidenceItem chính thức (§9 Spec)."""
        evidence = EvidenceItem(
            id=generate_snowflake_id(),
            workspace_id=signal.workspace_id,
            title=signal.title,
            summary=signal.summary,
            source_type=signal.source_type if signal.source_type in ["customer_interview", "market_report", "internal_metric", "regulation", "competitor", "note"] else "market_report",
            source_url_or_vault_uri=signal.source_url,
            published_at=signal.observed_at,
            captured_at=datetime.utcnow(),
            reliability="high" if signal.confidence >= 0.8 else "medium",
            tags={
                "signal_id": signal.id,
                "confidence": signal.confidence,
                "related_segment": signal.related_segment,
                "related_hypothesis": signal.related_hypothesis,
                "project_id": signal.project_id,
            },
            created_by=user_id,
        )
        db.add(evidence)
        db.flush()
        
        # Ghi nhận id của Evidence vào signal
        signal.evidence_id = evidence.id
        return evidence
