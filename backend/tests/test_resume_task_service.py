import asyncio
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from types import SimpleNamespace

from app.main import app
from api.auth import get_current_user
from schemas.resume import Candidate
from services import resume_service, resume_storage, resume_task_service


class ResumeTaskTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.storage_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage_dir.cleanup)
        storage_patch = patch.object(resume_storage, "DATA_ROOT", Path(self.storage_dir.name))
        storage_patch.start()
        self.addCleanup(storage_patch.stop)
        resume_task_service.task_store.clear()
        resume_task_service._background_tasks.clear()
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=None)
        self.addCleanup(app.dependency_overrides.clear)

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
            self.assertTrue(all(not Path(p).exists() for _, p in files))
            record = resume_task_service.task_store[created.task_id]
            self.assertTrue(all(
                resume_storage.resolve_resume_path(resume_path).is_file()
                for resume_path in record.pending_resumes.values()
            ))
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
        record = resume_task_service.task_store[created.task_id]
        pending_paths = {
            item.filename: resume_storage.resolve_resume_path(
                record.pending_resumes[item.item_id]
            )
            for item in record.task.items
        }
        self.assertFalse(pending_paths["A.pdf"].exists())
        self.assertTrue(pending_paths["B.pdf"].is_file())
        self.assertFalse(pending_paths["C.pdf"].exists())

    async def test_failed_item_can_retry_to_success_and_double_click_is_blocked(self):
        attempts = 0

        async def fake_parse(**_kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("模型暂时不可用")
            return Candidate(id="candidate_retry_success")

        files = self.make_files(["retry.pdf"])
        with patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse):
            created = resume_task_service.create_resume_task(files, user_id="user-a")
            first = await self.wait_finished(created.task_id)
            self.assertEqual(first.items[0].status, "failed")

            record = resume_task_service.task_store[created.task_id]
            item_id = first.items[0].item_id
            pending_path = resume_storage.resolve_resume_path(
                record.pending_resumes[item_id]
            )
            self.assertTrue(pending_path.is_file())

            retrying = resume_task_service.retry_resume_task_item(
                created.task_id, item_id, "user-a"
            )
            self.assertEqual(retrying.status, "running")
            self.assertEqual(retrying.items[0].status, "running")
            with self.assertRaises(resume_task_service.ResumeTaskConflictError):
                resume_task_service.retry_resume_task_item(
                    created.task_id, item_id, "user-a"
                )

            await resume_task_service._background_tasks[
                f"{created.task_id}:{item_id}"
            ]
            final = resume_task_service.get_resume_task(created.task_id)

        self.assertEqual(attempts, 2)
        self.assertEqual(final.status, "completed")
        self.assertEqual(final.items[0].status, "success")
        self.assertFalse(pending_path.exists())

    async def test_failed_retry_keeps_pending_pdf(self):
        async def fake_parse(**_kwargs):
            raise RuntimeError("仍然失败")

        files = self.make_files(["retry.pdf"])
        with patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse):
            created = resume_task_service.create_resume_task(files)
            first = await self.wait_finished(created.task_id)
            item_id = first.items[0].item_id
            record = resume_task_service.task_store[created.task_id]
            pending_path = resume_storage.resolve_resume_path(
                record.pending_resumes[item_id]
            )

            resume_task_service.retry_resume_task_item(created.task_id, item_id, None)
            await resume_task_service._background_tasks[
                f"{created.task_id}:{item_id}"
            ]
            final = resume_task_service.get_resume_task(created.task_id)

        self.assertEqual(final.status, "completed_with_errors")
        self.assertEqual(final.items[0].status, "failed")
        self.assertTrue(pending_path.is_file())

    async def test_candidate_persistence_failure_keeps_item_failed_and_pending_pdf(self):
        async def fake_parse(**_kwargs):
            return Candidate(id="candidate_persist_failure")

        files = self.make_files(["persist.pdf"])
        with patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse), patch.object(
            resume_task_service,
            "save_candidate_for_job",
            side_effect=RuntimeError("数据库暂时不可用"),
        ):
            created = resume_task_service.create_resume_task(files, job_id="job-test")
            final = await self.wait_finished(created.task_id)

        record = resume_task_service.task_store[created.task_id]
        item_id = final.items[0].item_id
        pending_path = resume_storage.resolve_resume_path(
            record.pending_resumes[item_id]
        )
        self.assertEqual(final.items[0].status, "failed")
        self.assertIsNone(final.items[0].candidate)
        self.assertTrue(pending_path.is_file())

    async def test_retry_rejects_success_missing_pdf_and_other_user(self):
        async def successful_parse(**_kwargs):
            return Candidate(id="candidate_no_retry")

        files = self.make_files(["success.pdf"])
        with patch.object(resume_service, "parse_resume_pdf", side_effect=successful_parse):
            created = resume_task_service.create_resume_task(files, user_id="user-a")
            final = await self.wait_finished(created.task_id)

        item_id = final.items[0].item_id
        with self.assertRaises(resume_task_service.ResumeTaskConflictError):
            resume_task_service.retry_resume_task_item(
                created.task_id, item_id, "user-a"
            )

        record = resume_task_service.task_store[created.task_id]
        record.task.items[0].status = "failed"
        record.task.status = "completed_with_errors"
        with self.assertRaises(resume_task_service.ResumeTaskForbiddenError):
            resume_task_service.retry_resume_task_item(
                created.task_id, item_id, "user-b"
            )
        with self.assertRaises(resume_task_service.ResumeTaskConflictError):
            resume_task_service.retry_resume_task_item(
                created.task_id, item_id, "user-a"
            )

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
                retry_missing = await client.post(
                    "/api/resume/tasks/not-found/items/not-found/retry"
                )
                self.assertEqual(retry_missing.status_code, 404)

    async def test_retry_api_switches_state_before_background_execution(self):
        attempts = 0
        release = asyncio.Event()

        async def fake_parse(**_kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("模型暂时不可用")
            await release.wait()
            return Candidate(id="candidate_retry_api")

        with patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/resume/tasks",
                    files=[("files", ("A.pdf", b"mock", "application/pdf"))],
                )
                created = response.json()
                await self.wait_finished(created["task_id"])
                item_id = created["items"][0]["item_id"]
                retry_url = (
                    f"/api/resume/tasks/{created['task_id']}/items/{item_id}/retry"
                )

                retrying = await client.post(retry_url)
                self.assertEqual(retrying.status_code, 202)
                self.assertEqual(retrying.json()["status"], "running")
                self.assertEqual(retrying.json()["items"][0]["status"], "running")
                duplicate = await client.post(retry_url)
                self.assertEqual(duplicate.status_code, 409)

                release.set()
                await resume_task_service._background_tasks[
                    f"{created['task_id']}:{item_id}"
                ]
                final = await client.get(f"/api/resume/tasks/{created['task_id']}")
                self.assertEqual(final.json()["items"][0]["status"], "success")

    async def test_retry_api_rejects_other_user_and_missing_pending_pdf(self):
        async def fake_parse(**_kwargs):
            raise RuntimeError("解析失败")

        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-a")
        with patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/resume/tasks",
                    files=[("files", ("A.pdf", b"mock", "application/pdf"))],
                )
                created = response.json()
                await self.wait_finished(created["task_id"])
                item_id = created["items"][0]["item_id"]
                retry_url = (
                    f"/api/resume/tasks/{created['task_id']}/items/{item_id}/retry"
                )

                app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
                    id="user-b"
                )
                forbidden = await client.post(retry_url)
                self.assertEqual(forbidden.status_code, 403)

                app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
                    id="user-a"
                )
                record = resume_task_service.task_store[created["task_id"]]
                resume_storage.delete_pending_resume(record.pending_resumes[item_id])
                missing_pdf = await client.post(retry_url)
                self.assertEqual(missing_pdf.status_code, 409)
                missing_item = await client.post(
                    f"/api/resume/tasks/{created['task_id']}/items/not-found/retry"
                )
                self.assertEqual(missing_item.status_code, 404)

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
