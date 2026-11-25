from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import JobModel, ScoringResultModel, TalentDiscoveryResultModel
from schemas.scoring import JobMatchResult
from schemas.talent import TalentDiscoveryResult, TalentMode


def save_scoring_result(
    result: JobMatchResult, *, job_revision: int, user_id: str
) -> JobMatchResult:
    with SessionLocal() as db:
        job = db.scalar(select(JobModel).where(
            JobModel.id == result.job_id,
            JobModel.user_id == user_id,
        ))
        if job is None:
            raise ValueError("岗位不存在")
        if job.revision != job_revision:
            raise ValueError("评分期间JD已被修改，请重新评分")
        row = db.scalar(select(ScoringResultModel).where(
            ScoringResultModel.user_id == user_id,
            ScoringResultModel.job_id == result.job_id,
            ScoringResultModel.candidate_id == result.candidate_id,
        ))
        if row is None:
            row = ScoringResultModel(
                id=f"score_{uuid4().hex}", job_id=result.job_id,
                candidate_id=result.candidate_id,
                user_id=user_id,
                created_by=user_id,
            )
            db.add(row)
        row.job_revision = job_revision
        row.analysis_language = result.analysis_language.value
        row.score = result.score
        row.confidence = result.confidence.value
        row.result_json = result.model_dump(mode="json")
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            row = db.scalar(select(ScoringResultModel).where(
                ScoringResultModel.user_id == user_id,
                ScoringResultModel.job_id == result.job_id,
                ScoringResultModel.candidate_id == result.candidate_id,
            ))
            job = db.scalar(select(JobModel).where(
                JobModel.id == result.job_id,
                JobModel.user_id == user_id,
            ))
            if row is None or job is None or job.revision != job_revision:
                raise
            row.job_revision = job_revision
            row.analysis_language = result.analysis_language.value
            row.score = result.score
            row.confidence = result.confidence.value
            row.result_json = result.model_dump(mode="json")
            db.commit()
    return result


def get_scoring_result(
    job_id: str, candidate_id: str, user_id: str
) -> JobMatchResult | None:
    with SessionLocal() as db:
        row = db.scalar(select(ScoringResultModel).where(
            ScoringResultModel.user_id == user_id,
            ScoringResultModel.job_id == job_id,
            ScoringResultModel.candidate_id == candidate_id,
        ))
        job = db.scalar(select(JobModel).where(
            JobModel.id == job_id,
            JobModel.user_id == user_id,
        ))
        if row is None or job is None or row.job_revision != job.revision:
            return None
        return JobMatchResult.model_validate(row.result_json)


def list_scoring_results(job_id: str, user_id: str) -> list[JobMatchResult]:
    with SessionLocal() as db:
        job = db.scalar(select(JobModel).where(
            JobModel.id == job_id,
            JobModel.user_id == user_id,
        ))
        if job is None:
            return []
        rows = db.scalars(select(ScoringResultModel).where(
            ScoringResultModel.user_id == user_id,
            ScoringResultModel.job_id == job_id,
            ScoringResultModel.job_revision == job.revision,
        )).all()
        return [JobMatchResult.model_validate(row.result_json) for row in rows]


def save_talent_result(
    result: TalentDiscoveryResult,
    *,
    desired_traits: list[str],
    user_id: str,
) -> TalentDiscoveryResult:
    with SessionLocal() as db:
        row = db.scalar(select(TalentDiscoveryResultModel).where(
            TalentDiscoveryResultModel.user_id == user_id,
            TalentDiscoveryResultModel.candidate_id == result.candidate_id,
            TalentDiscoveryResultModel.mode == result.mode,
        ))
        if row is None:
            row = TalentDiscoveryResultModel(
                id=f"talent_{uuid4().hex}",
                user_id=user_id,
                candidate_id=result.candidate_id,
                mode=result.mode,
                created_by=user_id,
            )
            db.add(row)
        row.analysis_language = result.analysis_language.value
        row.desired_traits_json = desired_traits
        row.result_json = result.model_dump(mode="json")
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            row = db.scalar(select(TalentDiscoveryResultModel).where(
                TalentDiscoveryResultModel.user_id == user_id,
                TalentDiscoveryResultModel.candidate_id == result.candidate_id,
                TalentDiscoveryResultModel.mode == result.mode,
            ))
            if row is None:
                raise
            row.analysis_language = result.analysis_language.value
            row.desired_traits_json = desired_traits
            row.result_json = result.model_dump(mode="json")
            db.commit()
    return result


def get_talent_result(
    candidate_id: str, mode: TalentMode, user_id: str
) -> TalentDiscoveryResult | None:
    with SessionLocal() as db:
        row = db.scalar(select(TalentDiscoveryResultModel).where(
            TalentDiscoveryResultModel.user_id == user_id,
            TalentDiscoveryResultModel.candidate_id == candidate_id,
            TalentDiscoveryResultModel.mode == mode,
        ))
        return TalentDiscoveryResult.model_validate(row.result_json) if row else None
