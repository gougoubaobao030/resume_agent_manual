import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from api.auth import get_current_user
from app.main import app
from database import SessionLocal
from models import CandidateModel, JobCandidateModel, UserModel
from repositories.candidate_repository import save_candidate_for_job
from repositories.jd_repository import save_jd
from schemas.jd import JDInfo, JDRequirement
from schemas.resume import Candidate
from services.auth_service import create_user


class UserDataIsolationTest(unittest.TestCase):
    def setUp(self) -> None:
        suffix = uuid4().hex
        with SessionLocal() as db:
            self.user_a = create_user(
                db,
                username=f"isolation_a_{suffix}",
                password="test-password-a",
            )
            self.user_b = create_user(
                db,
                username=f"isolation_b_{suffix}",
                password="test-password-b",
            )

        self.job_a = save_jd(
            JDInfo(
                id=f"job_isolation_a_{suffix}",
                job_title="Owner A Job",
                raw_text="Owner A job description",
                requirements=[JDRequirement(name="Python")],
            ),
            self.user_a.id,
        )
        self.job_b = save_jd(
            JDInfo(
                id=f"job_isolation_b_{suffix}",
                job_title="Owner B Job",
                raw_text="Owner B job description",
                requirements=[JDRequirement(name="Java")],
            ),
            self.user_b.id,
        )
        self.candidate_a = Candidate(id=f"candidate_isolation_a_{suffix}")
        self.candidate_b = Candidate(id=f"candidate_isolation_b_{suffix}")
        save_candidate_for_job(self.candidate_a, self.job_a.id, self.user_a.id)
        save_candidate_for_job(self.candidate_b, self.job_b.id, self.user_b.id)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        with SessionLocal() as db:
            db.execute(delete(CandidateModel).where(
                CandidateModel.user_id.in_([self.user_a.id, self.user_b.id])
            ))
            from models import JobModel
            db.execute(delete(JobModel).where(
                JobModel.user_id.in_([self.user_a.id, self.user_b.id])
            ))
            db.execute(delete(UserModel).where(
                UserModel.id.in_([self.user_a.id, self.user_b.id])
            ))
            db.commit()

    def _as_user(self, user_id: str) -> None:
        app.dependency_overrides[get_current_user] = (
            lambda: SimpleNamespace(id=user_id)
        )

    def test_lists_details_mutations_and_mixed_ids_are_isolated(self) -> None:
        self._as_user(self.user_a.id)
        jobs = self.client.get("/api/jd")
        self.assertEqual(jobs.status_code, 200, jobs.text)
        self.assertEqual([row["id"] for row in jobs.json()], [self.job_a.id])

        self.assertEqual(self.client.get(f"/api/jd/{self.job_b.id}").status_code, 404)
        self.assertEqual(
            self.client.get(f"/api/candidates/{self.candidate_b.id}").status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(f"/api/candidates/{self.candidate_b.id}").status_code,
            404,
        )
        mixed = self.client.post("/api/scoring/job-match", json={
            "job_id": self.job_a.id,
            "candidate_id": self.candidate_b.id,
            "analysis_language": "ja-JP",
        })
        self.assertEqual(mixed.status_code, 404, mixed.text)

        self._as_user(self.user_b.id)
        self.assertEqual(self.client.get(f"/api/jd/{self.job_b.id}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/jd/{self.job_a.id}").status_code, 404)

    def test_resume_hash_is_unique_per_user_and_relations_cannot_cross_users(self) -> None:
        resume_hash = "a" * 64
        with SessionLocal() as db:
            db.add_all([
                CandidateModel(
                    id=f"candidate_hash_{uuid4().hex}",
                    user_id=self.user_a.id,
                    resume_hash=resume_hash,
                    structured_data_json={},
                    created_by=self.user_a.id,
                ),
                CandidateModel(
                    id=f"candidate_hash_{uuid4().hex}",
                    user_id=self.user_b.id,
                    resume_hash=resume_hash,
                    structured_data_json={},
                    created_by=self.user_b.id,
                ),
            ])
            db.commit()

            db.add(CandidateModel(
                id=f"candidate_hash_{uuid4().hex}",
                user_id=self.user_a.id,
                resume_hash=resume_hash,
                structured_data_json={},
                created_by=self.user_a.id,
            ))
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

            db.add(JobCandidateModel(
                user_id=self.user_a.id,
                job_id=self.job_a.id,
                candidate_id=self.candidate_b.id,
                added_by=self.user_a.id,
            ))
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

            owners = db.scalars(select(CandidateModel.user_id).where(
                CandidateModel.resume_hash == resume_hash
            )).all()
            self.assertEqual(set(owners), {self.user_a.id, self.user_b.id})


if __name__ == "__main__":
    unittest.main()
