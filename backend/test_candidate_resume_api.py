import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.auth import get_current_user
from app.main import app
from schemas.jd import JDInfo, JDRequirement
from schemas.resume import Candidate, ExtractionMetadata
from services import resume_storage
from services.candidate_repository import delete_candidate, save_candidate_for_job
from services.jd_repository import delete_jd, save_jd


class CandidateResumeApiTest(unittest.TestCase):
    def setUp(self):
        self.storage_dir = tempfile.TemporaryDirectory()
        self.storage_patch = patch.object(
            resume_storage, "DATA_ROOT", Path(self.storage_dir.name)
        )
        self.storage_patch.start()
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=None)
        self.client = TestClient(app)
        self.job = save_jd(JDInfo(
            job_title="原简历接口测试",
            raw_text="测试 Candidate 原始简历读取",
            requirements=[JDRequirement(name="Python")],
        ))
        self.candidate_ids = []

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        for candidate_id in self.candidate_ids:
            delete_candidate(candidate_id)
        delete_jd(self.job.id)
        self.storage_patch.stop()
        self.storage_dir.cleanup()

    def save_candidate(self, candidate_id: str, source_path: str | None = None) -> None:
        candidate = Candidate(
            id=candidate_id,
            extraction_metadata=ExtractionMetadata(source_file="张三简历.pdf"),
        )
        save_candidate_for_job(
            candidate,
            self.job.id,
            None,
            resume_source_path=source_path,
        )
        self.candidate_ids.append(candidate_id)

    def test_returns_original_pdf_inline_without_job_id(self):
        source_path = Path(self.storage_dir.name) / "upload.pdf"
        source_path.write_bytes(b"%PDF-1.4\noriginal resume")
        self.save_candidate("candidate_resume_api", str(source_path))

        response = self.client.get("/api/candidates/candidate_resume_api/resume")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertIn("inline", response.headers["content-disposition"])
        self.assertEqual(response.content, source_path.read_bytes())

    def test_requires_existing_login_protection(self):
        app.dependency_overrides.pop(get_current_user, None)
        try:
            response = self.client.get("/api/candidates/any/resume")
        finally:
            app.dependency_overrides[get_current_user] = (
                lambda: SimpleNamespace(id=None)
            )

        self.assertEqual(response.status_code, 401)

    def test_reports_candidate_path_and_file_absence_separately(self):
        missing_candidate = self.client.get("/api/candidates/not-found/resume")
        self.assertEqual(missing_candidate.status_code, 404)
        self.assertEqual(missing_candidate.json()["detail"], "Candidate不存在")

        self.save_candidate("candidate_without_resume")
        missing_path = self.client.get(
            "/api/candidates/candidate_without_resume/resume"
        )
        self.assertEqual(missing_path.status_code, 404)
        self.assertEqual(
            missing_path.json()["detail"],
            "该Candidate尚未配置原始简历",
        )

        source_path = Path(self.storage_dir.name) / "missing-upload.pdf"
        source_path.write_bytes(b"%PDF-1.4\nmissing")
        self.save_candidate("candidate_missing_file", str(source_path))
        stored_path = (
            Path(self.storage_dir.name)
            / "resumes"
            / "candidate_missing_file"
            / "original.pdf"
        )
        stored_path.unlink()
        missing_file = self.client.get(
            "/api/candidates/candidate_missing_file/resume"
        )
        self.assertEqual(missing_file.status_code, 404)
        self.assertEqual(missing_file.json()["detail"], "原始简历文件缺失")

    def test_same_candidate_id_overwrites_original_resume(self):
        first = Path(self.storage_dir.name) / "first-upload.pdf"
        second = Path(self.storage_dir.name) / "second-upload.pdf"
        first.write_bytes(b"first resume")
        second.write_bytes(b"second resume")
        self.save_candidate("candidate_overwrite", str(first))

        updated = Candidate(
            id="candidate_overwrite",
            extraction_metadata=ExtractionMetadata(source_file="更新后的简历.pdf"),
        )
        save_candidate_for_job(
            updated,
            self.job.id,
            None,
            resume_source_path=str(second),
        )

        response = self.client.get("/api/candidates/candidate_overwrite/resume")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"second resume")

    def test_resume_replacement_is_restored_when_caller_fails(self):
        first = Path(self.storage_dir.name) / "first.pdf"
        second = Path(self.storage_dir.name) / "second.pdf"
        first.write_bytes(b"first")
        second.write_bytes(b"second")

        with resume_storage.store_candidate_resume(str(first), "candidate_restore"):
            pass

        with self.assertRaises(RuntimeError):
            with resume_storage.store_candidate_resume(
                str(second), "candidate_restore"
            ):
                raise RuntimeError("database failed")

        stored = (
            Path(self.storage_dir.name)
            / "resumes"
            / "candidate_restore"
            / "original.pdf"
        )
        self.assertEqual(stored.read_bytes(), b"first")


if __name__ == "__main__":
    unittest.main()
