from fastapi import APIRouter, HTTPException

from clients.llm_client import (
    LLMConfigError,
    LLMRequestError,
    LLMResponseError,
)

from schemas.talent import (
    TalentDiscoveryRequest,
    TalentDiscoveryResult,
)

from services.talent_service import discover_talent


router = APIRouter(
    prefix="/api/talent",
    tags=["talent"],
)


@router.post(
    "/discover",
    response_model=TalentDiscoveryResult,
)
def discover_talent_api(
    request: TalentDiscoveryRequest,
) -> TalentDiscoveryResult:
    """分析候选人的人才能力与指定人才特征。"""

    try:
        return discover_talent(
            candidate=request.candidate,
            mode=request.mode,
            desired_traits=request.desired_traits,
        )

    except LLMConfigError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    except LLMRequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except LLMResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc