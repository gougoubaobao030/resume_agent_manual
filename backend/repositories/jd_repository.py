from sqlalchemy import select

from database import SessionLocal
from models import JobModel
from schemas.jd import JDInfo, JDRequirement


def _to_schema(row: JobModel) -> JDInfo:
    return JDInfo(
        id=row.id,
        job_title=row.job_title,
        raw_text=row.raw_text,
        requirements=[JDRequirement.model_validate(item) for item in row.requirements_json],
    )


# 这里session单独可以自己开
# 因为是比较独立的操作
# 并不是有连续一系列要用到是数据库的操作
def save_jd(job: JDInfo, user_id: str) -> JDInfo:
    with SessionLocal() as db:
        db.add(JobModel(
            id=job.id,
            job_title=job.job_title,
            raw_text=job.raw_text,
            requirements_json=[item.model_dump(mode="json") for item in job.requirements],
            revision=1,
            user_id=user_id,
            created_by=user_id,
        ))
        db.commit()
    return job


def get_jd(job_id: str, user_id: str) -> JDInfo | None:
    with SessionLocal() as db:
        row = db.scalar(select(JobModel).where(
            JobModel.id == job_id,
            JobModel.user_id == user_id,
        ))
        return _to_schema(row) if row else None


def get_jd_revision(job_id: str, user_id: str) -> int | None:
    with SessionLocal() as db:
        return db.scalar(select(JobModel.revision).where(
            JobModel.id == job_id,
            JobModel.user_id == user_id,
        ))


def list_jds(user_id: str) -> list[JDInfo]:
    with SessionLocal() as db:
        rows = db.scalars(
            select(JobModel)
            .where(JobModel.user_id == user_id)
            .order_by(JobModel.updated_at.desc())
        ).all()
        return [_to_schema(row) for row in rows]


def update_jd(job_id: str, job: JDInfo, user_id: str) -> JDInfo:
    with SessionLocal() as db:
        row = db.scalar(select(JobModel).where(
            JobModel.id == job_id,
            JobModel.user_id == user_id,
        ))
        if row is None:
            raise ValueError("JD不存在")
        row.job_title = job.job_title
        row.raw_text = job.raw_text
        row.requirements_json = [
            item.model_dump(mode="json") for item in job.requirements
        ]
        row.revision += 1
        db.commit()
    return job


def delete_jd(job_id: str, user_id: str) -> bool:
    with SessionLocal() as db:
        row = db.scalar(select(JobModel).where(
            JobModel.id == job_id,
            JobModel.user_id == user_id,
        ))
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True
