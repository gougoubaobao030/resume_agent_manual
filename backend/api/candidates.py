from fastapi import APIRouter, HTTPException, Response

from schemas.resume import Candidate
from services.candidate_repository import (
    delete_candidate,
    get_candidate,
    list_candidates,
)


router = APIRouter(prefix="/api/candidates", tags=["Candidates"])


@router.get("", response_model=list[Candidate])
def list_candidates_api(job_id: str | None = None) -> list[Candidate]:
    return list_candidates(job_id)


@router.get("/{candidate_id}", response_model=Candidate)
def get_candidate_api(candidate_id: str) -> Candidate:
    candidate = get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate不存在")
    return candidate


@router.delete("/{candidate_id}", status_code=204)
def delete_candidate_api(candidate_id: str) -> Response:
    if not delete_candidate(candidate_id):
        raise HTTPException(status_code=404, detail="Candidate不存在")
    return Response(status_code=204)
