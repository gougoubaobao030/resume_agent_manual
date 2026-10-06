from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_user
from clients.llm_client import LLMConfigError, LLMRequestError, LLMResponseError
from models import UserModel
from schemas.scoring import JobMatchRequest, JobMatchResult
from services.candidate_repository import candidate_belongs_to_job, get_candidate
from services.jd_repository import get_jd, get_jd_revision
from services.result_repository import (
    get_scoring_result,
    list_scoring_results,
    save_scoring_result,
)
from services.scoring_service import evaluate_job_match


router = APIRouter(prefix="/api/scoring", tags=["scoring"])


@router.get("/job-match", response_model=list[JobMatchResult])
def list_job_matches(job_id: str) -> list[JobMatchResult]:
    return list_scoring_results(job_id)


@router.get("/job-match/{job_id}/{candidate_id}", response_model=JobMatchResult)
def get_job_match(job_id: str, candidate_id: str) -> JobMatchResult:
    result = get_scoring_result(job_id, candidate_id)
    if result is None:
        raise HTTPException(status_code=404, detail="当前评分不存在或已过期")
    return result


@router.post("/job-match", response_model=JobMatchResult)
def score_job_match(
    request: JobMatchRequest,
    current_user: UserModel = Depends(get_current_user),
) -> JobMatchResult:
    jd = get_jd(request.job_id)
    if jd is None:
        raise HTTPException(status_code=404, detail="岗位不存在")
    candidate = get_candidate(request.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate不存在")
    if not candidate_belongs_to_job(request.job_id, request.candidate_id):
        raise HTTPException(status_code=404, detail="Candidate未关联到该岗位")
    job_revision = get_jd_revision(request.job_id)

    try:
        result = evaluate_job_match(
            jd=jd,
            candidate=candidate,
            analysis_language=request.analysis_language,
        )
        return save_scoring_result(
            result,
            job_revision=job_revision,
            user_id=current_user.id,
        )
    except LLMConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMRequestError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
