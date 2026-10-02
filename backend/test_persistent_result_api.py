import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.main import app
from database import SessionLocal
from models import UserModel
from schemas.jd import JDInfo, JDRequirement
from schemas.resume import Candidate
from services.auth_service import create_user
from services.candidate_repository import delete_candidate, save_candidate_for_job
from services.jd_repository import delete_jd, save_jd


class PersistentResultApiTest(unittest.TestCase):
    def setUp(self):
        with SessionLocal() as db:
            db.execute(delete(UserModel).where(UserModel.username == "result_api_test"))
            db.commit()
            self.user = create_user(
                db, username="result_api_test", password="test-pass-123"
            )
        self.job = save_jd(JDInfo(
            job_title="API结果测试",
            raw_text="招聘熟悉Python的开发人员，要求能够完成后端开发。",
            requirements=[JDRequirement(
                name="Python", description="熟悉Python", category="technical"
            )],
        ))
        self.candidate = Candidate(
            id="candidate_result_api_test",
            skills=["Python"],
            raw_text="熟悉Python并完成过后端开发。",
        )
        save_candidate_for_job(self.candidate, self.job.id, self.user.id)
        self.client = TestClient(app)
        response = self.client.post("/api/auth/login", json={
            "username": "result_api_test", "password": "test-pass-123"
        })
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        delete_candidate(self.candidate.id)
        delete_jd(self.job.id)
        with SessionLocal() as db:
            db.execute(delete(UserModel).where(UserModel.username == "result_api_test"))
            db.commit()

    def test_score_and_talent_are_loaded_from_database_and_persisted(self):
        with patch.dict(os.environ, {
            "SCORING_USE_MOCK": "true",
            "TALENT_USE_MOCK": "true",
        }):
            score = self.client.post("/api/scoring/job-match", json={
                "job_id": self.job.id,
                "candidate_id": self.candidate.id,
                "analysis_language": "zh-CN",
            })
            talent = self.client.post("/api/talent/discover", json={
                "candidate_id": self.candidate.id,
                "analysis_language": "zh-CN",
                "mode": "auto",
                "desired_traits": [],
            })

        self.assertEqual(score.status_code, 200, score.text)
        self.assertEqual(talent.status_code, 200, talent.text)
        self.assertEqual(
            self.client.get(
                f"/api/scoring/job-match/{self.job.id}/{self.candidate.id}"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(f"/api/talent/discover/{self.candidate.id}").status_code,
            200,
        )


if __name__ == "__main__":
    unittest.main()
