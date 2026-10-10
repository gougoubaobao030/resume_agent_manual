from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from schemas.resume import Candidate, CandidatePoolItem
from repositories.candidate_repository import (
    delete_candidate,
    get_candidate,
    get_candidate_resume_info,
    list_candidate_pool,
    list_candidates,
    remove_candidate_from_job,
)
from services.resume_storage import resolve_resume_path


router = APIRouter(prefix="/api/candidates", tags=["Candidates"])


@router.get("", response_model=list[Candidate])
def list_candidates_api(job_id: str | None = None) -> list[Candidate]:
    return list_candidates(job_id)


@router.get("/pool", response_model=list[CandidatePoolItem])
def list_candidate_pool_api() -> list[CandidatePoolItem]:
    return list_candidate_pool()


@router.get("/{candidate_id}", response_model=Candidate)
def get_candidate_api(candidate_id: str) -> Candidate:
    candidate = get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate不存在")
    return candidate


@router.get("/{candidate_id}/resume", response_class=FileResponse)
def get_candidate_resume_api(candidate_id: str) -> FileResponse:
    resume_info = get_candidate_resume_info(candidate_id)
    if resume_info is None:
        raise HTTPException(status_code=404, detail="Candidate不存在")

    resume_path, source_file = resume_info
    if not resume_path:
        raise HTTPException(status_code=404, detail="该Candidate尚未配置原始简历")

    try:
        physical_path = resolve_resume_path(resume_path)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not physical_path.is_file():
        raise HTTPException(status_code=404, detail="原始简历文件缺失")

    return FileResponse(
        physical_path,
        media_type="application/pdf",
        filename=source_file or "original.pdf",
        content_disposition_type="inline",
    )


@router.delete("/{candidate_id}", status_code=204)
def delete_candidate_api(candidate_id: str) -> Response:
    if not delete_candidate(candidate_id):
        raise HTTPException(status_code=404, detail="Candidate不存在")
    return Response(status_code=204)


@router.delete("/{candidate_id}/jobs/{job_id}", status_code=204)
def remove_candidate_from_job_api(candidate_id: str, job_id: str) -> Response:
    if not remove_candidate_from_job(job_id, candidate_id):
        raise HTTPException(status_code=404, detail="Candidate未关联到该岗位")
    return Response(status_code=204)
