from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_user
from clients.llm_client import LLMConfigError, LLMRequestError, LLMResponseError
from models import UserModel
from schemas.talent import TalentDiscoveryRequest, TalentDiscoveryResult, TalentMode
from repositories.candidate_repository import get_candidate
from repositories.result_repository import get_talent_result, save_talent_result
from services.talent_service import discover_talent


router = APIRouter(prefix="/api/talent", tags=["talent"])


@router.get("/discover/{candidate_id}", response_model=TalentDiscoveryResult)
def get_talent_discovery(
    candidate_id: str, mode: TalentMode
) -> TalentDiscoveryResult:
    result = get_talent_result(candidate_id, mode)
    if result is None:
        raise HTTPException(status_code=404, detail="人才能力分析结果不存在")
    return result


@router.post("/discover", response_model=TalentDiscoveryResult)
def discover_talent_api(
    request: TalentDiscoveryRequest,
    current_user: UserModel = Depends(get_current_user),
) -> TalentDiscoveryResult:
    candidate = get_candidate(request.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate不存在")

    try:
        result = discover_talent(
            candidate=candidate,
            mode=request.mode,
            desired_traits=request.desired_traits,
            analysis_language=request.analysis_language,
        )
        return save_talent_result(
            result,
            desired_traits=request.desired_traits,
            user_id=current_user.id,
        )
    except LLMConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMRequestError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
