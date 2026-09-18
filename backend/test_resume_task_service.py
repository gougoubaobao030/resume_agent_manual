import asyncio
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app.main import app
from schemas.resume import Candidate
from services import resume_service, resume_task_service


class ResumeTaskTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def make_files(self, names):
        files = []
        for index, name in enumerate(names):
            path = Path(self.temp_dir.name) / f"{index}.pdf"
            path.write_bytes(b"mock pdf")
            files.append((name, str(path)))
        return files

    async def wait_finished(self, task_id):
        # 测试等待 runner，API 使用者则只调用 GET，不需要接触 asyncio.Task。
        await asyncio.wait_for(resume_task_service._background_tasks[task_id], timeout=10)
        return resume_task_service.get_resume_task(task_id)

    async def test_create_returns_pending_and_duplicate_names_have_distinct_ids(self):
        release = asyncio.Event()

        async def fake_parse(**kwargs):
            await release.wait()
            return Candidate(id="candidate_test")

        files = self.make_files(["same.pdf", "same.pdf"])
        with patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse):
            created = resume_task_service.create_resume_task(files)
            self.assertTrue(created.task_id.startswith("resume_task_"))
            self.assertEqual(created.status, "pending")
            self.assertEqual([i.status for i in created.items], ["pending", "pending"])
            self.assertNotEqual(created.items[0].item_id, created.items[1].item_id)
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            running = resume_task_service.get_resume_task(created.task_id)
            self.assertEqual(running.status, "running")
            self.assertEqual([i.status for i in running.items], ["running", "running"])
            self.assertTrue(all(Path(p).exists() for _, p in files))
            release.set()
            final = await self.wait_finished(created.task_id)
        self.assertEqual(final.status, "completed")
        self.assertEqual(final.success_count, 2)
        self.assertTrue(all(not Path(p).exists() for _, p in files))

    async def test_real_resume_mock_finishes_successfully(self):
        files = self.make_files(["A.pdf", "B.pdf", "C.pdf", "D.pdf", "E.pdf"])
        with patch.dict(os.environ, {"RESUME_USE_MOCK": "true"}):
            created = resume_task_service.create_resume_task(files)
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            current = resume_task_service.get_resume_task(created.task_id)
            self.assertEqual([i.status for i in current.items], ["running"] * 3 + ["pending"] * 2)
            final = await self.wait_finished(created.task_id)
        self.assertEqual([i.status for i in final.items], ["success"] * 5)
        self.assertEqual(final.items[0].candidate.extraction_metadata.parser, "resume-mock")
        self.assertEqual((final.success_count, final.failed_count), (5, 0))
        self.assertTrue(all(not Path(p).exists() for _, p in files))

    async def test_partial_upload_failure_cleans_created_temp_file(self):
        from api import resume as resume_api

        paths = []
        original_copy = resume_api.shutil.copyfileobj

        def failing_copy(source, target):
            paths.append(target.name)
            original_copy(source, target)
            raise OSError("模拟写盘失败")

        with patch.object(resume_api.shutil, "copyfileobj", side_effect=failing_copy):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                with self.assertRaises(OSError):
                    await client.post("/api/resume/tasks", files=[("files", ("A.pdf", b"mock"))])
        self.assertEqual(len(paths), 1)
        self.assertFalse(Path(paths[0]).exists())

    async def test_one_failure_is_isolated_and_files_are_cleaned(self):
        async def fake_parse(pdf_path, source_file):
            await asyncio.sleep(0)
            if source_file == "B.pdf":
                raise ValueError("B 解析失败")
            return Candidate(id=source_file)

        files = self.make_files(["A.pdf", "B.pdf", "C.pdf"])
        with patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse):
            created = resume_task_service.create_resume_task(files)
            final = await self.wait_finished(created.task_id)
        self.assertEqual([i.status for i in final.items], ["success", "failed", "success"])
        self.assertEqual(final.status, "completed_with_errors")
        self.assertEqual((final.success_count, final.failed_count), (2, 1))
        self.assertEqual(final.items[1].error, "B 解析失败")
        self.assertIsNone(final.error)
        self.assertTrue(all(not Path(p).exists() for _, p in files))

    async def test_semaphore_keeps_waiting_items_pending_and_maximum_three(self):
        release = asyncio.Event()
        first_three = asyncio.Event()
        active = maximum = 0

        async def fake_parse(**kwargs):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            if active == 3:
                first_three.set()
            try:
                await release.wait()
                return Candidate(id="test")
            finally:
                active -= 1

        files = self.make_files([f"{i}.pdf" for i in range(7)])
        with patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse):
            created = resume_task_service.create_resume_task(files)
            await asyncio.wait_for(first_three.wait(), timeout=2)
            current = resume_task_service.get_resume_task(created.task_id)
            self.assertEqual([i.status for i in current.items], ["running"] * 3 + ["pending"] * 4)
            self.assertEqual((current.success_count, current.failed_count), (0, 0))
            release.set()
            final = await self.wait_finished(created.task_id)
        self.assertEqual(maximum, 3)
        self.assertEqual(final.success_count, 7)

    async def test_batch_infrastructure_failure_marks_batch_failed_and_cleans(self):
        files = self.make_files(["A.pdf"])
        with patch.object(resume_task_service, "parse_resume_batch", side_effect=RuntimeError("编排失败")):
            created = resume_task_service.create_resume_task(files)
            final = await self.wait_finished(created.task_id)
        self.assertEqual(final.status, "failed")
        self.assertEqual(final.error, "编排失败")
        self.assertEqual(final.items[0].status, "failed")
        self.assertEqual(final.failed_count, 1)
        self.assertFalse(Path(files[0][1]).exists())

    async def test_api_returns_before_parse_and_get_reports_progress(self):
        release = asyncio.Event()
        started = asyncio.Event()
        paths = []

        async def fake_parse(pdf_path, source_file):
            paths.append(pdf_path)
            started.set()
            await release.wait()
            return Candidate(id="api_test")

        with patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await asyncio.wait_for(client.post(
                    "/api/resume/tasks", files=[("files", ("A.pdf", b"mock", "application/pdf"))]
                ), timeout=2)
                self.assertEqual(response.status_code, 202)
                created = response.json()
                self.assertEqual(created["status"], "pending")
                await asyncio.wait_for(started.wait(), timeout=2)
                self.assertTrue(Path(paths[0]).exists())
                current = await client.get(f"/api/resume/tasks/{created['task_id']}")
                self.assertEqual(current.json()["items"][0]["status"], "running")
                release.set()
                await self.wait_finished(created["task_id"])
                final = await client.get(f"/api/resume/tasks/{created['task_id']}")
                self.assertEqual(final.json()["status"], "completed")
                self.assertFalse(Path(paths[0]).exists())
                missing = await client.get("/api/resume/tasks/not-found")
                self.assertEqual(missing.status_code, 404)

    async def test_old_batch_api_contract_and_new_validation(self):
        async def fake_parse(**kwargs):
            return Candidate(id="old_api")

        with patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/resume/parse-batch", files=[("files", ("A.pdf", b"mock"))])
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["success_count"], 1)
                self.assertTrue(response.json()["results"][0]["success"])
                invalid = await client.post("/api/resume/tasks", files=[("files", ("A.txt", b"mock"))])
                self.assertEqual(invalid.status_code, 400)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
