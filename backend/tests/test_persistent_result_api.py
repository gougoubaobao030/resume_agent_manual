import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.main import app
from database import SessionLocal
from models import ScoringResultModel, UserModel
from schemas.jd import JDInfo, JDRequirement
from schemas.resume import Candidate
from services.auth_service import create_user
from repositories.candidate_repository import delete_candidate, save_candidate_for_job
from repositories.jd_repository import delete_jd, save_jd


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
            specified_talent = self.client.post("/api/talent/discover", json={
                "candidate_id": self.candidate.id,
                "analysis_language": "zh-CN",
                "mode": "specified",
                "desired_traits": ["认真"],
            })

        self.assertEqual(score.status_code, 200, score.text)
        self.assertEqual(talent.status_code, 200, talent.text)
        self.assertEqual(specified_talent.status_code, 200, specified_talent.text)
        self.assertEqual(
            self.client.get(
                f"/api/scoring/job-match/{self.job.id}/{self.candidate.id}"
            ).status_code,
            200,
        )
        auto_result = self.client.get(
            f"/api/talent/discover/{self.candidate.id}?mode=auto"
        )
        specified_result = self.client.get(
            f"/api/talent/discover/{self.candidate.id}?mode=specified"
        )
        self.assertEqual(auto_result.status_code, 200, auto_result.text)
        self.assertEqual(specified_result.status_code, 200, specified_result.text)
        self.assertEqual(auto_result.json()["mode"], "auto")
        self.assertEqual(specified_result.json()["mode"], "specified")

    def test_score_rejects_candidate_not_linked_to_job(self):
        other_job = save_jd(JDInfo(
            job_title="其他岗位",
            raw_text="另一个用于关系校验的岗位。",
            requirements=[JDRequirement(name="Java")],
        ))
        other_candidate = Candidate(
            id="candidate_other_job_result_api_test",
            skills=["Java"],
            raw_text="熟悉Java。",
        )
        save_candidate_for_job(other_candidate, other_job.id, self.user.id)

        try:
            with patch.dict(os.environ, {"SCORING_USE_MOCK": "true"}):
                response = self.client.post("/api/scoring/job-match", json={
                    "job_id": self.job.id,
                    "candidate_id": other_candidate.id,
                    "analysis_language": "zh-CN",
                })

            self.assertEqual(response.status_code, 404, response.text)
            self.assertEqual(response.json()["detail"], "Candidate未关联到该岗位")
        finally:
            delete_candidate(other_candidate.id)
            delete_jd(other_job.id)

    def test_rescore_updates_existing_result(self):
        with patch.dict(os.environ, {"SCORING_USE_MOCK": "true"}):
            first = self.client.post("/api/scoring/job-match", json={
                "job_id": self.job.id,
                "candidate_id": self.candidate.id,
                "analysis_language": "zh-CN",
            })
            second = self.client.post("/api/scoring/job-match", json={
                "job_id": self.job.id,
                "candidate_id": self.candidate.id,
                "analysis_language": "ja-JP",
            })

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        with SessionLocal() as db:
            rows = db.scalars(select(ScoringResultModel).where(
                ScoringResultModel.job_id == self.job.id,
                ScoringResultModel.candidate_id == self.candidate.id,
            )).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].analysis_language, "ja-JP")
        self.assertEqual(rows[0].result_json["analysis_language"], "ja-JP")


if __name__ == "__main__":
    unittest.main()
