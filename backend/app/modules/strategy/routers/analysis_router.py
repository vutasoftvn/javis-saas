import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import (
    WorkspaceMember,
    ContextPack,
    StrategyAnalysis,
    PestelItem,
    SwotItem,
    TowsOption,
    StrategicDecision,
    PromptTemplate,
    StrategyCanvas,
    StrategyFoundation,
    CoreValue,
    Project,
)
from app.integrations.anthropic_client import AnthropicClient
from app.modules.chat.ai_router import ChatTurn
from app.modules.strategy.assisted_analyzer import AssistedAnalyzerService
from app.core.feature_flags import require_flag, FLAG_ASSISTED_TERRA_V12
from app.modules.strategy.schemas.analysis_schemas import (
    PestelItemCreate,
    PestelItemUpdate,
    SwotItemCreate,
    SwotItemUpdate,
    TowsOptionCreate,
    TowsOptionUpdate,
    PromptTemplateUpdate,
    AiAnalysisRequest,
    AnalysisExportRequest,
    AnalysisImportRequest,
)
from app.modules.strategy.services.analysis_prompts import (
    DEFAULT_STRATEGY_PROMPT_TEMPLATE,
    build_dynamic_json_example,
    generate_fallback_mock_analysis,
)

router = APIRouter()


def _serialize_pestel(item: PestelItem) -> dict:
    return {
        "id": str(item.id),
        "factor": item.factor,
        "statement": item.statement,
        "impact": item.impact,
        "horizon": item.horizon,
        "confidence": item.confidence,
        "evidence_status": item.evidence_status,
    }


def _serialize_swot(item: SwotItem) -> dict:
    return {
        "id": str(item.id),
        "category": item.category,
        "statement": item.statement,
        "impact": item.impact,
        "likelihood": item.likelihood,
        "confidence": item.confidence,
        "evidence_status": item.evidence_status,
    }


def _serialize_tows(item: TowsOption) -> dict:
    return {
        "id": str(item.id),
        "quadrant": item.quadrant,
        "title": item.title,
        "tradeoffs": item.tradeoffs,
        "expected_impact": item.expected_impact,
        "confidence": item.confidence,
        "status": item.status,
    }


def _serialize_decision(item: StrategicDecision) -> dict:
    return {
        "id": str(item.id),
        "decision": item.decision,
        "status": item.status,
        "tows_option_id": str(item.tows_option_id) if item.tows_option_id else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _get_or_create_analysis(db: Session, workspace_id: int, kind: str) -> StrategyAnalysis:
    analysis = db.query(StrategyAnalysis).filter(
        StrategyAnalysis.workspace_id == workspace_id,
        StrategyAnalysis.kind == kind
    ).first()
    if not analysis:
        pack = db.query(ContextPack).filter(ContextPack.workspace_id == workspace_id).first()
        if not pack:
            pack = ContextPack(workspace_id=workspace_id, status="draft")
            db.add(pack)
            db.flush()
        analysis = StrategyAnalysis(
            workspace_id=workspace_id,
            context_pack_id=pack.id,
            kind=kind,
            status="draft"
        )
        db.add(analysis)
        db.flush()
    return analysis


@router.get("/analyses/pestel")
def list_pestel_items(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    items = db.query(PestelItem).filter(PestelItem.workspace_id == workspace_id).all()
    return {"items": [_serialize_pestel(i) for i in items]}


@router.post("/analyses/pestel")
def create_pestel_item(
    workspace_id: int,
    data: PestelItemCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    analysis = _get_or_create_analysis(db, workspace_id, "PESTEL")
    item = PestelItem(
        workspace_id=workspace_id,
        analysis_id=analysis.id,
        factor=data.factor,
        statement=data.statement,
        impact=data.impact or "Medium",
        horizon=data.horizon or "medium_term",
        confidence=data.confidence or "medium",
        evidence_status=data.evidence_status or "hypothesized",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_pestel(item)


@router.put("/analyses/pestel/{item_id}")
def update_pestel_item(
    item_id: int,
    workspace_id: int,
    data: PestelItemUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    item = db.query(PestelItem).filter(PestelItem.id == item_id, PestelItem.workspace_id == workspace_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="PESTEL item not found")
    if data.factor is not None:
        item.factor = data.factor
    if data.statement is not None:
        item.statement = data.statement
    if data.impact is not None:
        item.impact = data.impact
    if data.horizon is not None:
        item.horizon = data.horizon
    if data.confidence is not None:
        item.confidence = data.confidence
    if data.evidence_status is not None:
        item.evidence_status = data.evidence_status
    db.commit()
    db.refresh(item)
    return _serialize_pestel(item)


@router.delete("/analyses/pestel/{item_id}")
def delete_pestel_item(
    item_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    item = db.query(PestelItem).filter(PestelItem.id == item_id, PestelItem.workspace_id == workspace_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="PESTEL item not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": str(item_id)}


@router.get("/analyses/swot")
def list_swot_items(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    items = db.query(SwotItem).filter(SwotItem.workspace_id == workspace_id).all()
    return {"items": [_serialize_swot(i) for i in items]}


@router.post("/analyses/swot")
def create_swot_item(
    workspace_id: int,
    data: SwotItemCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    analysis = _get_or_create_analysis(db, workspace_id, "SWOT")
    item = SwotItem(
        workspace_id=workspace_id,
        analysis_id=analysis.id,
        category=data.category,
        statement=data.statement,
        impact=data.impact or "High",
        likelihood=data.likelihood or "High",
        confidence=data.confidence or "High",
        evidence_status=data.evidence_status or "hypothesized",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_swot(item)


@router.put("/analyses/swot/{item_id}")
def update_swot_item(
    item_id: int,
    workspace_id: int,
    data: SwotItemUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    item = db.query(SwotItem).filter(SwotItem.id == item_id, SwotItem.workspace_id == workspace_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="SWOT item not found")
    if data.category is not None:
        item.category = data.category
    if data.statement is not None:
        item.statement = data.statement
    if data.impact is not None:
        item.impact = data.impact
    if data.likelihood is not None:
        item.likelihood = data.likelihood
    if data.confidence is not None:
        item.confidence = data.confidence
    if data.evidence_status is not None:
        item.evidence_status = data.evidence_status
    db.commit()
    db.refresh(item)
    return _serialize_swot(item)


@router.delete("/analyses/swot/{item_id}")
def delete_swot_item(
    item_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    item = db.query(SwotItem).filter(SwotItem.id == item_id, SwotItem.workspace_id == workspace_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="SWOT item not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": str(item_id)}


@router.get("/analyses/tows")
def list_tows_options(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    items = db.query(TowsOption).filter(TowsOption.workspace_id == workspace_id).all()
    return {"items": [_serialize_tows(i) for i in items]}


@router.post("/analyses/tows")
def create_tows_option(
    workspace_id: int,
    data: TowsOptionCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    analysis = _get_or_create_analysis(db, workspace_id, "TOWS")
    item = TowsOption(
        workspace_id=workspace_id,
        analysis_id=analysis.id,
        quadrant=data.quadrant,
        title=data.title,
        tradeoffs=data.tradeoffs,
        expected_impact=data.expected_impact or "High",
        confidence=data.confidence or "High",
        status=data.status or "draft",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_tows(item)


@router.put("/analyses/tows/{option_id}")
def update_tows_option(
    option_id: int,
    workspace_id: int,
    data: TowsOptionUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    item = db.query(TowsOption).filter(TowsOption.id == option_id, TowsOption.workspace_id == workspace_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="TOWS option not found")
    if data.quadrant is not None:
        item.quadrant = data.quadrant
    if data.title is not None:
        item.title = data.title
    if data.tradeoffs is not None:
        item.tradeoffs = data.tradeoffs
    if data.expected_impact is not None:
        item.expected_impact = data.expected_impact
    if data.confidence is not None:
        item.confidence = data.confidence
    if data.status is not None:
        item.status = data.status
    db.commit()
    db.refresh(item)
    return _serialize_tows(item)


@router.delete("/analyses/tows/{option_id}")
def delete_tows_option(
    option_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    item = db.query(TowsOption).filter(TowsOption.id == option_id, TowsOption.workspace_id == workspace_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="TOWS option not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted", "id": str(option_id)}


@router.get("/analyses/prompt-template")
def get_prompt_template(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    try:
        try:
            PromptTemplate.__table__.create(bind=db.get_bind(), checkfirst=True)
        except Exception:
            pass

        tmpl = db.query(PromptTemplate).filter(
            PromptTemplate.workspace_id == workspace_id,
            PromptTemplate.feature_key == "STRATEGY_ANALYSIS"
        ).first()
        
        if not tmpl:
            tmpl = PromptTemplate(
                workspace_id=workspace_id,
                brain_id=getattr(member, 'brain_id', None),
                feature_key="STRATEGY_ANALYSIS",
                name="Phân tích Chiến lược (PESTEL, SWOT, TOWS)",
                template_content=DEFAULT_STRATEGY_PROMPT_TEMPLATE,
                config_jsonb={
                    "pestel_items_per_factor": 3,
                    "swot_items_per_category": 3,
                    "tows_items_per_quadrant": 2
                },
                is_default=True
            )
            db.add(tmpl)
            try:
                db.commit()
                db.refresh(tmpl)
            except Exception as commit_err:
                db.rollback()
                print(f"Commit seed error in get_prompt_template: {commit_err}")
                return {
                    "workspace_id": str(workspace_id),
                    "is_customized": False,
                    "template_content": DEFAULT_STRATEGY_PROMPT_TEMPLATE,
                    "config": {
                        "pestel_items_per_factor": 3,
                        "swot_items_per_category": 3,
                        "tows_items_per_quadrant": 2
                    }
                }
        
        config = (tmpl.config_jsonb if tmpl else {}) or {}
        return {
            "id": str(tmpl.id) if tmpl and tmpl.id else None,
            "workspace_id": str(workspace_id),
            "is_customized": not (tmpl.is_default if tmpl else True),
            "template_content": (tmpl.template_content if tmpl and tmpl.template_content else None) or DEFAULT_STRATEGY_PROMPT_TEMPLATE,
            "config": {
                "pestel_items_per_factor": config.get("pestel_items_per_factor", 3),
                "swot_items_per_category": config.get("swot_items_per_category", 3),
                "tows_items_per_quadrant": config.get("tows_items_per_quadrant", 2)
            }
        }
    except Exception as e:
        print(f"Error in get_prompt_template: {e}")
        db.rollback()
        return {
            "workspace_id": str(workspace_id),
            "is_customized": False,
            "template_content": DEFAULT_STRATEGY_PROMPT_TEMPLATE,
            "config": {
                "pestel_items_per_factor": 3,
                "swot_items_per_category": 3,
                "tows_items_per_quadrant": 2
            }
        }


@router.put("/analyses/prompt-template")
def update_prompt_template(
    workspace_id: int,
    data: PromptTemplateUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    try:
        try:
            PromptTemplate.__table__.create(bind=db.get_bind(), checkfirst=True)
        except Exception:
            pass

        tmpl = db.query(PromptTemplate).filter(
            PromptTemplate.workspace_id == workspace_id,
            PromptTemplate.feature_key == "STRATEGY_ANALYSIS"
        ).first()
        
        if not tmpl:
            tmpl = PromptTemplate(
                workspace_id=workspace_id,
                brain_id=getattr(member, 'brain_id', None),
                feature_key="STRATEGY_ANALYSIS",
                name="Phân tích Chiến lược (PESTEL, SWOT, TOWS)",
                template_content=data.template_content or DEFAULT_STRATEGY_PROMPT_TEMPLATE,
                config_jsonb={
                    "pestel_items_per_factor": data.pestel_items_per_factor if data.pestel_items_per_factor is not None else 3,
                    "swot_items_per_category": data.swot_items_per_category if data.swot_items_per_category is not None else 3,
                    "tows_items_per_quadrant": data.tows_items_per_quadrant if data.tows_items_per_quadrant is not None else 2
                },
                is_default=False
            )
            db.add(tmpl)
        else:
            if data.template_content is not None:
                tmpl.template_content = data.template_content
            curr_config = tmpl.config_jsonb or {}
            if data.pestel_items_per_factor is not None:
                curr_config["pestel_items_per_factor"] = data.pestel_items_per_factor
            if data.swot_items_per_category is not None:
                curr_config["swot_items_per_category"] = data.swot_items_per_category
            if data.tows_items_per_quadrant is not None:
                curr_config["tows_items_per_quadrant"] = data.tows_items_per_quadrant
            tmpl.config_jsonb = curr_config
            tmpl.is_default = False
        
        db.commit()
        db.refresh(tmpl)
        config = tmpl.config_jsonb or {}
        return {
            "id": str(tmpl.id),
            "workspace_id": str(workspace_id),
            "is_customized": not tmpl.is_default,
            "template_content": tmpl.template_content,
            "config": {
                "pestel_items_per_factor": config.get("pestel_items_per_factor", 3),
                "swot_items_per_category": config.get("swot_items_per_category", 3),
                "tows_items_per_quadrant": config.get("tows_items_per_quadrant", 2)
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update prompt template: {str(e)}")


@router.post("/analyses/prompt-template/reset")
def reset_prompt_template(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    tmpl = db.query(PromptTemplate).filter(
        PromptTemplate.workspace_id == workspace_id,
        PromptTemplate.feature_key == "STRATEGY_ANALYSIS"
    ).first()
    if tmpl:
        tmpl.template_content = DEFAULT_STRATEGY_PROMPT_TEMPLATE,
        tmpl.config_jsonb = {
            "pestel_items_per_factor": 3,
            "swot_items_per_category": 3,
            "tows_items_per_quadrant": 2
        }
        tmpl.is_default = True
        db.commit()
        db.refresh(tmpl)
    return {"status": "reset", "workspace_id": str(workspace_id)}


@router.post("/analyses/generate-ai")
async def generate_ai_analysis(
    workspace_id: int,
    data: Optional[AiAnalysisRequest] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    req_data = data or AiAnalysisRequest()

    db_tmpl = db.query(PromptTemplate).filter(
        PromptTemplate.workspace_id == workspace_id,
        PromptTemplate.feature_key == "STRATEGY_ANALYSIS"
    ).first()
    tmpl_config = (db_tmpl.config_jsonb if db_tmpl else {}) or {}

    pestel_count = req_data.pestel_items_per_factor or tmpl_config.get("pestel_items_per_factor", 3)
    swot_count = req_data.swot_items_per_category or tmpl_config.get("swot_items_per_category", 3)
    tows_count = req_data.tows_items_per_quadrant or tmpl_config.get("tows_items_per_quadrant", 2)
    template_str = (db_tmpl.template_content if db_tmpl and db_tmpl.template_content else None) or DEFAULT_STRATEGY_PROMPT_TEMPLATE

    pestel_analysis = _get_or_create_analysis(db, workspace_id, "PESTEL")
    swot_analysis = _get_or_create_analysis(db, workspace_id, "SWOT")
    tows_analysis = _get_or_create_analysis(db, workspace_id, "TOWS")

    if req_data.clear_existing is not False:
        db.query(PestelItem).filter(PestelItem.workspace_id == workspace_id).delete(synchronize_session=False)
        db.query(SwotItem).filter(SwotItem.workspace_id == workspace_id).delete(synchronize_session=False)
        db.query(TowsOption).filter(TowsOption.workspace_id == workspace_id).delete(synchronize_session=False)
        db.flush()

    vision_text = "Hệ thống Quản trị Strategy SaaS thông minh"
    mission_text = "Tối ưu hóa lập kế hoạch và thực thi chiến lược cho doanh nghiệp"
    core_values_text = "Tối ưu, Đổi mới, Hiệu quả"

    canvas = db.query(StrategyCanvas).filter(StrategyCanvas.workspace_id == workspace_id).first()
    if canvas:
        rev = db.query(StrategyFoundation).filter(StrategyFoundation.canvas_id == canvas.id).first()
        if rev:
            if rev.vision_statement:
                vision_text = rev.vision_statement
            if rev.mission_statement:
                mission_text = rev.mission_statement
        cv_items = db.query(CoreValue).filter(CoreValue.workspace_id == workspace_id).all()
        if cv_items:
            core_values_text = ", ".join([cv.title for cv in cv_items if cv.title])

    project_context = "Toàn doanh nghiệp (Enterprise-wide)"
    project_label = ""
    if req_data.project_id:
        proj = db.query(Project).filter(Project.id == req_data.project_id, Project.workspace_id == workspace_id).first()
        if proj:
            proj_title = getattr(proj, 'title', getattr(proj, 'name', ''))
            project_label = proj_title
            project_context = f"Dự án '{proj_title}' (Mã: {proj.code or 'N/A'}) - Mô tả: {proj.description or 'Không có mô tả'}"

    focus_note = req_data.focus_area or "Phát triển Nền tảng SaaS & Tối ưu hóa Vận hành"

    json_example_structure = build_dynamic_json_example(pestel_count, swot_count, tows_count)
    prompt = template_str.format(
        vision_text=vision_text,
        mission_text=mission_text,
        core_values_text=core_values_text,
        project_context=project_context,
        focus_note=focus_note,
        pestel_count=pestel_count,
        pestel_total=pestel_count * 6,
        swot_count=swot_count,
        swot_total=swot_count * 4,
        tows_count=tows_count,
        tows_total=tows_count * 4,
        json_structure=json_example_structure
    )

    ai_success = False
    pestel_data, swot_data, tows_data = [], [], []

    client = AnthropicClient()
    if getattr(client, 'api_key', None):
        try:
            turns = [ChatTurn(role="user", content=prompt)]
            response_text = await run_in_threadpool(client.complete, turns=turns, temperature=0.3)
            
            clean_res = response_text.strip()
            if "```json" in clean_res:
                clean_res = clean_res.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_res:
                clean_res = clean_res.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(clean_res)
            pestel_data = parsed.get("pestel", [])
            swot_data = parsed.get("swot", [])
            tows_data = parsed.get("tows", [])
            ai_success = True
        except Exception as err:
            print(f"Anthropic AI generation error in generate_ai_analysis: {err}")
            ai_success = False

    if not ai_success or not pestel_data:
        pestel_data, swot_data, tows_data = generate_fallback_mock_analysis(
            vision_text=vision_text,
            project_label=project_label,
            focus_note=focus_note,
            pestel_count=pestel_count,
            swot_count=swot_count,
            tows_count=tows_count
        )

    saved_pestel = []
    for item_data in pestel_data:
        factor = item_data.get("factor", "Technological")
        stmt = item_data.get("statement", "Nhận định PESTEL")
        imp = item_data.get("impact", "Positive")
        if not stmt or not stmt.strip():
            continue
        p_item = PestelItem(
            workspace_id=workspace_id,
            analysis_id=pestel_analysis.id,
            factor=factor,
            statement=stmt,
            impact=imp,
            horizon="medium_term",
            confidence="high",
            evidence_status="verified"
        )
        db.add(p_item)
        saved_pestel.append(p_item)

    saved_swot = []
    for item_data in swot_data:
        cat = item_data.get("category", "Strength")
        stmt = item_data.get("statement", "Nhận định SWOT")
        imp = item_data.get("impact", "High")
        if not stmt or not stmt.strip():
            continue
        s_item = SwotItem(
            workspace_id=workspace_id,
            analysis_id=swot_analysis.id,
            category=cat,
            statement=stmt,
            impact=imp,
            likelihood="High",
            confidence="High",
            evidence_status="verified"
        )
        db.add(s_item)
        saved_swot.append(s_item)

    saved_tows = []
    for item_data in tows_data:
        quad = item_data.get("quadrant", "SO")
        title = item_data.get("title", "Lựa chọn TOWS")
        trade = item_data.get("tradeoffs", "Sự đánh đổi nguồn lực")
        if not title or not title.strip():
            continue
        t_item = TowsOption(
            workspace_id=workspace_id,
            analysis_id=tows_analysis.id,
            quadrant=quad,
            title=title,
            tradeoffs=trade,
            expected_impact="High",
            confidence="High",
            status="draft"
        )
        db.add(t_item)
        saved_tows.append(t_item)

    db.commit()
    for item in saved_pestel:
        db.refresh(item)
    for item in saved_swot:
        db.refresh(item)
    for item in saved_tows:
        db.refresh(item)

    return {
        "status": "success",
        "generated_by": "Claude 3.7 Sonnet (Anthropic AI)" if ai_success else "Fallback Strategic Engine",
        "counts": {
            "pestel": len(saved_pestel),
            "swot": len(saved_swot),
            "tows": len(saved_tows)
        },
        "pestel": [_serialize_pestel(i) for i in saved_pestel],
        "swot": [_serialize_swot(i) for i in saved_swot],
        "tows": [_serialize_tows(i) for i in saved_tows]
    }


@router.post("/decisions")
def create_decision(
    workspace_id: int,
    data: dict,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    decision_text = data.get("decision")
    tows_option_id = data.get("tows_option_id")
    if not decision_text:
        raise HTTPException(status_code=400, detail="decision text is required")
    item = StrategicDecision(
        workspace_id=workspace_id,
        decision=decision_text,
        tows_option_id=int(tows_option_id) if tows_option_id else None,
        status="active"
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_decision(item)


@router.get("/decisions")
def list_decisions(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    items = db.query(StrategicDecision).filter(StrategicDecision.workspace_id == workspace_id).all()
    return {"decisions": [_serialize_decision(i) for i in items]}
