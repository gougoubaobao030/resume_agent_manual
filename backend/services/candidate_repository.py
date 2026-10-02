from sqlalchemy import select

from database import SessionLocal
from models import CandidateModel, JobCandidateModel
from schemas.resume import Candidate


def _to_schema(row: CandidateModel) -> Candidate:
    return Candidate.model_validate({
        "id": row.id,
        "raw_text": row.raw_text,
        **row.structured_data_json,
    })


def save_candidate_for_job(
    candidate: Candidate,
    job_id: str,
    user_id: str | None,
) -> Candidate:
    if not candidate.id:
        raise ValueError("Candidate缺少id，无法保存")

    # payload把里面多余的另外存的拿出来
    payload = candidate.model_dump(mode="json")
    payload.pop("id", None)
    raw_text = payload.pop("raw_text", None)
    source_file = (candidate.extraction_metadata.source_file
                   if candidate.extraction_metadata else None)

    with SessionLocal() as db:
        row = db.get(CandidateModel, candidate.id)
        if row is None:
            row = CandidateModel(
                id=candidate.id,
                raw_text=raw_text,
                structured_data_json=payload,
                source_file=source_file,
                created_by=user_id,
            )
            db.add(row)
        else:
            # Resume Mock 使用文件名生成稳定ID；重复上传时更新同一快照。
            row.raw_text = raw_text
            row.structured_data_json = payload
            row.source_file = source_file

        relation = db.get(JobCandidateModel, (job_id, candidate.id))
        if relation is None:
            db.add(JobCandidateModel(
                job_id=job_id,
                candidate_id=candidate.id,
                added_by=user_id,
            ))
        db.commit()
    return candidate


def get_candidate(candidate_id: str) -> Candidate | None:
    with SessionLocal() as db:
        row = db.get(CandidateModel, candidate_id)
        return _to_schema(row) if row else None


def list_candidates(job_id: str | None = None) -> list[Candidate]:
    with SessionLocal() as db:
        statement = select(CandidateModel)
        if job_id:
            statement = statement.join(
                JobCandidateModel,
                JobCandidateModel.candidate_id == CandidateModel.id,
            ).where(JobCandidateModel.job_id == job_id)
        rows = db.scalars(statement.order_by(CandidateModel.created_at.desc())).all()
        return [_to_schema(row) for row in rows]


def delete_candidate(candidate_id: str) -> bool:
    with SessionLocal() as db:
        row = db.get(CandidateModel, candidate_id)
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True
