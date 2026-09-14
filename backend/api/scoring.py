from fastapi import APIRouter, HTTPException

from clients.llm_client import (
    LLMConfigError,
    LLMRequestError,
    LLMResponseError,
)
from schemas.scoring import (
    JobMatchRequest,
    JobMatchResult,
)
from services.jd_repository import get_jd
from services.scoring_service import evaluate_job_match


router = APIRouter(
    prefix="/api/scoring",
    tags=["scoring"],
)

@router.post(
    "/job-match",
    response_model=JobMatchResult,
)
def score_job_match(
    request: JobMatchRequest,
) -> JobMatchResult:
    """对候选人与已保存岗位进行岗位匹配评分。"""

    jd = get_jd(request.job_id)

    if jd is None:
        raise HTTPException(
            status_code=404,
            detail="岗位不存在",
        )

    try:
        return evaluate_job_match(
            jd=jd,
            candidate=request.candidate,
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
            status_code=422,
            detail=str(exc),
        ) from exc
    

    