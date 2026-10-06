from sqlalchemy import delete, select

from database import SessionLocal
from models import CandidateModel, JobCandidateModel, JobModel, ScoringResultModel
from schemas.resume import Candidate, CandidatePoolItem, CandidatePoolJob
from services.resume_storage import (
    resolve_resume_path,
    stage_candidate_resume_deletion,
    store_candidate_resume,
)


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
    resume_source_path: str | None = None,
) -> Candidate:
    if not candidate.id:
        raise ValueError("Candidate缺少id，无法保存")

    # payload把里面多余的另外存的拿出来
    payload = candidate.model_dump(mode="json")
    payload.pop("id", None)
    raw_text = payload.pop("raw_text", None)
    source_file = (candidate.extraction_metadata.source_file
                   if candidate.extraction_metadata else None)

    def persist(resume_path: str | None = None) -> None:
        with SessionLocal() as db:
            row = db.get(CandidateModel, candidate.id)
            if row is None:
                row = CandidateModel(
                    id=candidate.id,
                    raw_text=raw_text,
                    structured_data_json=payload,
                    source_file=source_file,
                    resume_path=resume_path,
                    created_by=user_id,
                )
                db.add(row)
            else:
                # Resume Mock 使用文件名生成稳定ID；重复上传时更新同一快照。
                row.raw_text = raw_text
                row.structured_data_json = payload
                row.source_file = source_file
                if resume_path is not None:
                    row.resume_path = resume_path

            relation = db.get(JobCandidateModel, (job_id, candidate.id))
            if relation is None:
                db.add(JobCandidateModel(
                    job_id=job_id,
                    candidate_id=candidate.id,
                    added_by=user_id,
                ))
            db.commit()

    if resume_source_path is None:
        persist()
    else:
        # 数据库提交失败时，storage context 会恢复原文件或移除新文件。
        with store_candidate_resume(resume_source_path, candidate.id) as resume_path:
            persist(resume_path)
    return candidate


def get_candidate(candidate_id: str) -> Candidate | None:
    with SessionLocal() as db:
        row = db.get(CandidateModel, candidate_id)
        return _to_schema(row) if row else None


def get_candidate_resume_info(candidate_id: str) -> tuple[str | None, str | None] | None:
    with SessionLocal() as db:
        row = db.get(CandidateModel, candidate_id)
        if row is None:
            return None
        return row.resume_path, row.source_file


def candidate_belongs_to_job(job_id: str, candidate_id: str) -> bool:
    with SessionLocal() as db:
        return db.get(JobCandidateModel, (job_id, candidate_id)) is not None


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


def _experience_summary(row: CandidateModel) -> str | None:
    experiences = row.structured_data_json.get("work_experience") or []
    if not experiences:
        return None
    latest = experiences[0]
    values = [latest.get("position"), latest.get("company")]
    return " · ".join(value for value in values if value) or None


def list_candidate_pool() -> list[CandidatePoolItem]:
    with SessionLocal() as db:
        candidates = db.scalars(
            select(CandidateModel).order_by(CandidateModel.created_at.desc())
        ).all()
        relation_rows = db.execute(
            select(JobCandidateModel.candidate_id, JobModel.id, JobModel.job_title)
            .join(JobModel, JobModel.id == JobCandidateModel.job_id)
            .order_by(JobCandidateModel.created_at.desc())
        ).all()

        jobs_by_candidate: dict[str, list[CandidatePoolJob]] = {}
        for candidate_id, job_id, job_title in relation_rows:
            jobs_by_candidate.setdefault(candidate_id, []).append(
                CandidatePoolJob(id=job_id, job_title=job_title)
            )

        items = []
        for row in candidates:
            basic_info = row.structured_data_json.get("basic_info") or {}
            source_file = row.source_file
            if not source_file:
                metadata = row.structured_data_json.get("extraction_metadata") or {}
                source_file = metadata.get("source_file")

            has_resume = False
            if row.resume_path:
                try:
                    has_resume = resolve_resume_path(row.resume_path).is_file()
                except ValueError:
                    has_resume = False

            items.append(CandidatePoolItem(
                id=row.id,
                name=basic_info.get("name"),
                experience_summary=_experience_summary(row),
                skills=row.structured_data_json.get("skills") or [],
                created_at=row.created_at,
                source_file=source_file,
                has_resume=has_resume,
                jobs=jobs_by_candidate.get(row.id, []),
            ))
        return items


def remove_candidate_from_job(job_id: str, candidate_id: str) -> bool:
    with SessionLocal() as db:
        relation = db.get(JobCandidateModel, (job_id, candidate_id))
        if relation is None:
            return False
        db.execute(delete(ScoringResultModel).where(
            ScoringResultModel.job_id == job_id,
            ScoringResultModel.candidate_id == candidate_id,
        ))
        db.delete(relation)
        db.commit()
        return True


def delete_candidate(candidate_id: str) -> bool:
    with SessionLocal() as db:
        row = db.get(CandidateModel, candidate_id)
        if row is None:
            return False
        with stage_candidate_resume_deletion(row.resume_path):
            db.delete(row)
            db.commit()
        return True
