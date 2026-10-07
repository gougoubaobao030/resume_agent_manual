import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from app.main import app
from database import SessionLocal
from models import (
    CandidateModel,
    JobCandidateModel,
    JobModel,
    ScoringResultModel,
    TalentDiscoveryResultModel,
)
from schemas.jd import JDInfo, JDRequirement
from schemas.resume import BasicInfo, Candidate, ExtractionMetadata, WorkExperience
from services import resume_storage
from services.candidate_repository import delete_candidate, save_candidate_for_job
from services.jd_repository import delete_jd, save_jd


class CandidatePoolTest(unittest.TestCase):
    candidate_id = "candidate_pool_delete_test"
    other_candidate_id = "candidate_pool_other_test"
    job_one_id = "job_pool_one_test"
    job_two_id = "job_pool_two_test"

    def setUp(self) -> None:
        self.storage_dir = tempfile.TemporaryDirectory()
        self.storage_patch = patch.object(
            resume_storage, "DATA_ROOT", Path(self.storage_dir.name)
        )
        self.storage_patch.start()
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=None)
        self.client = TestClient(app)

        delete_candidate(self.candidate_id)
        delete_candidate(self.other_candidate_id)
        delete_jd(self.job_one_id)
        delete_jd(self.job_two_id)

        self.job_one = save_jd(JDInfo(
            id=self.job_one_id,
            job_title="Pool Job One",
            raw_text="Pool job one",
            requirements=[JDRequirement(name="Python")],
        ))
        self.job_two = save_jd(JDInfo(
            id=self.job_two_id,
            job_title="Pool Job Two",
            raw_text="Pool job two",
            requirements=[JDRequirement(name="SQL")],
        ))

        candidate_pdf = Path(self.storage_dir.name) / "candidate.pdf"
        candidate_pdf.write_bytes(b"candidate pdf")
        candidate = Candidate(
            id=self.candidate_id,
            basic_info=BasicInfo(name="Pool Candidate"),
            work_experience=[WorkExperience(company="Example", position="Engineer")],
            skills=["Python", "SQL"],
            extraction_metadata=ExtractionMetadata(source_file="candidate.pdf"),
        )
        save_candidate_for_job(
            candidate, self.job_one.id, None, resume_source_path=str(candidate_pdf)
        )
        save_candidate_for_job(candidate, self.job_two.id, None)

        other_pdf = Path(self.storage_dir.name) / "other.pdf"
        other_pdf.write_bytes(b"other pdf")
        other_candidate = Candidate(
            id=self.other_candidate_id,
            basic_info=BasicInfo(name="Other Candidate"),
            extraction_metadata=ExtractionMetadata(source_file="other.pdf"),
        )
        save_candidate_for_job(
            other_candidate,
            self.job_one.id,
            None,
            resume_source_path=str(other_pdf),
        )

        with SessionLocal() as db:
            db.add_all([
                self._score("score_pool_one", self.job_one.id, self.candidate_id),
                self._score("score_pool_two", self.job_two.id, self.candidate_id),
                self._score("score_pool_other", self.job_one.id, self.other_candidate_id),
                TalentDiscoveryResultModel(
                    id="talent_pool_candidate",
                    candidate_id=self.candidate_id,
                    mode="auto",
                    analysis_language="zh-CN",
                    desired_traits_json=[],
                    result_json={},
                ),
                TalentDiscoveryResultModel(
                    id="talent_pool_other",
                    candidate_id=self.other_candidate_id,
                    mode="auto",
                    analysis_language="zh-CN",
                    desired_traits_json=[],
                    result_json={},
                ),
            ])
            db.commit()

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        delete_candidate(self.candidate_id)
        delete_candidate(self.other_candidate_id)
        delete_jd(self.job_one_id)
        delete_jd(self.job_two_id)
        self.storage_patch.stop()
        self.storage_dir.cleanup()

    @staticmethod
    def _score(score_id: str, job_id: str, candidate_id: str) -> ScoringResultModel:
        return ScoringResultModel(
            id=score_id,
            job_id=job_id,
            candidate_id=candidate_id,
            job_revision=1,
            analysis_language="zh-CN",
            score=80,
            confidence="high",
            result_json={},
        )

    def test_pool_lists_candidate_summary_and_jobs(self) -> None:
        response = self.client.get("/api/candidates/pool")

        self.assertEqual(response.status_code, 200, response.text)
        item = next(
            item for item in response.json() if item["id"] == self.candidate_id
        )
        self.assertEqual(item["name"], "Pool Candidate")
        self.assertEqual(item["experience_summary"], "Engineer · Example")
        self.assertEqual(item["skills"], ["Python", "SQL"])
        self.assertEqual(item["source_file"], "candidate.pdf")
        self.assertTrue(item["has_resume"])
        self.assertEqual(
            {job["id"] for job in item["jobs"]},
            {self.job_one.id, self.job_two.id},
        )

    def test_global_delete_cascades_and_deletes_only_its_pdf(self) -> None:
        response = self.client.delete(f"/api/candidates/{self.candidate_id}")

        self.assertEqual(response.status_code, 204, response.text)
        candidate_pdf = (
            Path(self.storage_dir.name)
            / "resumes"
            / self.candidate_id
            / "original.pdf"
        )
        other_pdf = (
            Path(self.storage_dir.name)
            / "resumes"
            / self.other_candidate_id
            / "original.pdf"
        )
        self.assertFalse(candidate_pdf.exists())
        self.assertTrue(other_pdf.exists())

        with SessionLocal() as db:
            self.assertIsNone(db.get(CandidateModel, self.candidate_id))
            self.assertEqual(self._count(db, JobCandidateModel, self.candidate_id), 0)
            self.assertEqual(self._count(db, ScoringResultModel, self.candidate_id), 0)
            self.assertEqual(
                self._count(db, TalentDiscoveryResultModel, self.candidate_id), 0
            )
            self.assertIsNotNone(db.get(CandidateModel, self.other_candidate_id))
            self.assertEqual(self._count(db, JobCandidateModel, self.other_candidate_id), 1)
            self.assertEqual(self._count(db, ScoringResultModel, self.other_candidate_id), 1)
            self.assertEqual(
                self._count(db, TalentDiscoveryResultModel, self.other_candidate_id), 1
            )
            self.assertIsNotNone(db.get(JobModel, self.job_one.id))
            self.assertIsNotNone(db.get(JobModel, self.job_two.id))

    def test_remove_from_job_preserves_candidate_other_job_talent_and_pdf(self) -> None:
        response = self.client.delete(
            f"/api/candidates/{self.candidate_id}/jobs/{self.job_one.id}"
        )

        self.assertEqual(response.status_code, 204, response.text)
        candidate_pdf = (
            Path(self.storage_dir.name)
            / "resumes"
            / self.candidate_id
            / "original.pdf"
        )
        self.assertTrue(candidate_pdf.exists())

        with SessionLocal() as db:
            self.assertIsNotNone(db.get(CandidateModel, self.candidate_id))
            self.assertIsNone(
                db.get(JobCandidateModel, (self.job_one.id, self.candidate_id))
            )
            self.assertIsNotNone(
                db.get(JobCandidateModel, (self.job_two.id, self.candidate_id))
            )
            self.assertEqual(
                self._score_count(db, self.job_one.id, self.candidate_id), 0
            )
            self.assertEqual(
                self._score_count(db, self.job_two.id, self.candidate_id), 1
            )
            self.assertEqual(
                self._count(db, TalentDiscoveryResultModel, self.candidate_id), 1
            )

    def test_delete_job_cascades_only_job_scoped_data(self) -> None:
        response = self.client.delete(f"/api/jd/{self.job_one.id}")

        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(
            self.client.delete(f"/api/jd/{self.job_one.id}").status_code,
            404,
        )
        candidate_pdf = (
            Path(self.storage_dir.name)
            / "resumes"
            / self.candidate_id
            / "original.pdf"
        )
        self.assertTrue(candidate_pdf.exists())

        with SessionLocal() as db:
            self.assertIsNone(db.get(JobModel, self.job_one.id))
            self.assertEqual(
                db.scalar(
                    select(func.count()).select_from(JobCandidateModel).where(
                        JobCandidateModel.job_id == self.job_one.id
                    )
                ),
                0,
            )
            self.assertEqual(
                db.scalar(
                    select(func.count()).select_from(ScoringResultModel).where(
                        ScoringResultModel.job_id == self.job_one.id
                    )
                ),
                0,
            )

            self.assertIsNotNone(db.get(CandidateModel, self.candidate_id))
            self.assertEqual(
                self._count(db, TalentDiscoveryResultModel, self.candidate_id), 1
            )

            self.assertIsNotNone(db.get(JobModel, self.job_two.id))
            self.assertIsNotNone(
                db.get(JobCandidateModel, (self.job_two.id, self.candidate_id))
            )
            self.assertEqual(
                self._score_count(db, self.job_two.id, self.candidate_id), 1
            )

    def test_global_delete_restores_pdf_when_database_commit_fails(self) -> None:
        candidate_pdf = (
            Path(self.storage_dir.name)
            / "resumes"
            / self.candidate_id
            / "original.pdf"
        )

        with patch.object(Session, "commit", side_effect=RuntimeError("commit failed")):
            with self.assertRaises(RuntimeError):
                delete_candidate(self.candidate_id)

        self.assertTrue(candidate_pdf.exists())
        with SessionLocal() as db:
            self.assertIsNotNone(db.get(CandidateModel, self.candidate_id))

    @staticmethod
    def _count(db, model, candidate_id: str) -> int:
        return db.scalar(
            select(func.count()).select_from(model).where(
                model.candidate_id == candidate_id
            )
        )

    @staticmethod
    def _score_count(db, job_id: str, candidate_id: str) -> int:
        return db.scalar(
            select(func.count()).select_from(ScoringResultModel).where(
                ScoringResultModel.job_id == job_id,
                ScoringResultModel.candidate_id == candidate_id,
            )
        )


class CandidateResumeDeletionTest(unittest.TestCase):
    def test_staged_pdf_is_restored_when_database_work_fails(self) -> None:
        with tempfile.TemporaryDirectory() as storage_dir, patch.object(
            resume_storage, "DATA_ROOT", Path(storage_dir)
        ):
            resume_path = resume_storage.candidate_resume_key("restore_delete_test")
            physical_path = resume_storage.resolve_resume_path(resume_path)
            physical_path.parent.mkdir(parents=True)
            physical_path.write_bytes(b"resume")

            with self.assertRaises(RuntimeError):
                with resume_storage.stage_candidate_resume_deletion(resume_path):
                    self.assertFalse(physical_path.exists())
                    raise RuntimeError("database commit failed")

            self.assertEqual(physical_path.read_bytes(), b"resume")


if __name__ == "__main__":
    unittest.main()
