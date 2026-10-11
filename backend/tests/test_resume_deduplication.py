import asyncio
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import func, select

from database import SessionLocal
from models import CandidateModel, JobCandidateModel
from repositories.candidate_repository import (
    delete_candidate,
    save_candidate_for_job,
    save_candidate_for_job_with_hash,
)
from repositories.jd_repository import delete_jd, save_jd
from schemas.jd import JDInfo, JDRequirement
from schemas.resume import BasicInfo, Candidate, ExtractionMetadata
from services import resume_service, resume_storage, resume_task_service


class ResumeDeduplicationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.source_dir = tempfile.TemporaryDirectory()
        self.storage_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.source_dir.cleanup)
        self.addCleanup(self.storage_dir.cleanup)
        storage_patch = patch.object(
            resume_storage,
            "DATA_ROOT",
            Path(self.storage_dir.name),
        )
        storage_patch.start()
        self.addCleanup(storage_patch.stop)
        resume_task_service.task_store.clear()
        resume_task_service._background_tasks.clear()
        self.candidate_ids: list[str] = []
        self.job_ids: list[str] = []

    async def asyncTearDown(self) -> None:
        for candidate_id in self.candidate_ids:
            delete_candidate(candidate_id)
        for job_id in self.job_ids:
            delete_jd(job_id)

    def make_job(self, title: str) -> JDInfo:
        job = save_jd(JDInfo(
            id=f"job_dedupe_{uuid4().hex}",
            job_title=title,
            raw_text=title,
            requirements=[JDRequirement(name="Python")],
        ))
        self.job_ids.append(job.id)
        return job

    def make_upload(self, name: str, content: bytes) -> tuple[str, str]:
        path = Path(self.source_dir.name) / f"{uuid4().hex}.pdf"
        path.write_bytes(content)
        return name, str(path)

    async def wait_finished(self, task_id: str):
        await asyncio.wait_for(
            resume_task_service._background_tasks[task_id],
            timeout=10,
        )
        return resume_task_service.get_resume_task(task_id)

    async def test_created_reused_and_already_linked(self) -> None:
        first_job = self.make_job("First")
        second_job = self.make_job("Second")
        content = b"same original pdf bytes"
        resume_hash = hashlib.sha256(content).hexdigest()
        candidate_id = f"candidate_dedupe_{uuid4().hex}"
        self.candidate_ids.append(candidate_id)
        parse_calls = 0

        async def fake_parse(**_kwargs):
            nonlocal parse_calls
            parse_calls += 1
            return Candidate(
                id=candidate_id,
                basic_info=BasicInfo(name="Original Candidate"),
                raw_text="original raw text",
                extraction_metadata=ExtractionMetadata(source_file="first.pdf"),
            )

        with patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse):
            created_task = resume_task_service.create_resume_task(
                [self.make_upload("first.pdf", content)],
                job_id=first_job.id,
            )
            created = await self.wait_finished(created_task.task_id)

            reused_task = resume_task_service.create_resume_task(
                [self.make_upload("renamed.pdf", content)],
                job_id=second_job.id,
            )
            reused_record = resume_task_service.task_store[reused_task.task_id]
            reused_item_id = reused_task.items[0].item_id
            reused_pending = resume_storage.resolve_resume_path(
                reused_record.pending_resumes[reused_item_id]
            )
            reused = await self.wait_finished(reused_task.task_id)

            linked_task = resume_task_service.create_resume_task(
                [self.make_upload("again.pdf", content)],
                job_id=second_job.id,
            )
            linked_record = resume_task_service.task_store[linked_task.task_id]
            linked_item_id = linked_task.items[0].item_id
            linked_pending = resume_storage.resolve_resume_path(
                linked_record.pending_resumes[linked_item_id]
            )
            already_linked = await self.wait_finished(linked_task.task_id)

        self.assertEqual(parse_calls, 1)
        self.assertEqual(created.items[0].outcome, "created")
        self.assertEqual(reused.items[0].outcome, "reused")
        self.assertEqual(already_linked.items[0].outcome, "already_linked")
        self.assertEqual(reused.items[0].candidate.id, candidate_id)
        self.assertEqual(already_linked.items[0].candidate.id, candidate_id)
        self.assertFalse(reused_pending.exists())
        self.assertFalse(linked_pending.exists())

        with SessionLocal() as db:
            rows = db.scalars(
                select(CandidateModel).where(
                    CandidateModel.resume_hash == resume_hash
                )
            ).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].id, candidate_id)
            self.assertEqual(rows[0].raw_text, "original raw text")
            self.assertEqual(rows[0].source_file, "first.pdf")
            self.assertEqual(
                resume_storage.resolve_resume_path(rows[0].resume_path).read_bytes(),
                content,
            )
            self.assertEqual(
                rows[0].structured_data_json["basic_info"]["name"],
                "Original Candidate",
            )
            self.assertEqual(
                db.scalar(
                    select(func.count()).select_from(JobCandidateModel).where(
                        JobCandidateModel.candidate_id == candidate_id
                    )
                ),
                2,
            )

    async def test_same_pdf_in_one_batch_recovers_unique_hash_race(self) -> None:
        job = self.make_job("Concurrent")
        content = b"concurrent identical pdf"
        resume_hash = hashlib.sha256(content).hexdigest()
        started = 0
        both_started = asyncio.Event()
        release = asyncio.Event()

        async def fake_parse(**_kwargs):
            nonlocal started
            started += 1
            if started == 2:
                both_started.set()
            await release.wait()
            candidate_id = f"candidate_dedupe_{uuid4().hex}"
            self.candidate_ids.append(candidate_id)
            return Candidate(id=candidate_id, raw_text="race")

        with patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse):
            created = resume_task_service.create_resume_task(
                [
                    self.make_upload("one.pdf", content),
                    self.make_upload("two.pdf", content),
                ],
                job_id=job.id,
            )
            await asyncio.wait_for(both_started.wait(), timeout=5)
            release.set()
            final = await self.wait_finished(created.task_id)

        self.assertEqual(started, 2)
        self.assertEqual([item.status for item in final.items], ["success", "success"])
        self.assertEqual(
            {item.outcome for item in final.items},
            {"created", "already_linked"},
        )
        winner_ids = {item.candidate.id for item in final.items}
        self.assertEqual(len(winner_ids), 1)

        with SessionLocal() as db:
            self.assertEqual(
                db.scalar(
                    select(func.count()).select_from(CandidateModel).where(
                        CandidateModel.resume_hash == resume_hash
                    )
                ),
                1,
            )
            self.assertEqual(
                db.scalar(
                    select(func.count()).select_from(JobCandidateModel).where(
                        JobCandidateModel.job_id == job.id
                    )
                ),
                1,
            )

        losing_ids = set(self.candidate_ids) - winner_ids
        for losing_id in losing_ids:
            losing_pdf = (
                Path(self.storage_dir.name)
                / "resumes"
                / losing_id
                / "original.pdf"
            )
            self.assertFalse(losing_pdf.exists())

    async def test_retry_uses_hash_lookup_before_parsing(self) -> None:
        retry_job = self.make_job("Retry")
        winner_job = self.make_job("Winner")
        content = b"retry duplicate pdf"
        resume_hash = hashlib.sha256(content).hexdigest()
        winner_id = f"candidate_dedupe_{uuid4().hex}"
        self.candidate_ids.append(winner_id)

        async def fail_parse(**_kwargs):
            raise RuntimeError("temporary parse failure")

        with patch.object(resume_service, "parse_resume_pdf", side_effect=fail_parse):
            created = resume_task_service.create_resume_task(
                [self.make_upload("retry.pdf", content)],
                job_id=retry_job.id,
                user_id=None,
            )
            failed = await self.wait_finished(created.task_id)

        winner_source = Path(self.source_dir.name) / "winner.pdf"
        winner_source.write_bytes(content)
        save_candidate_for_job_with_hash(
            Candidate(id=winner_id, raw_text="winner"),
            winner_job.id,
            None,
            str(winner_source),
            resume_hash,
        )

        item_id = failed.items[0].item_id
        record = resume_task_service.task_store[created.task_id]
        pending_path = resume_storage.resolve_resume_path(
            record.pending_resumes[item_id]
        )
        self.assertTrue(pending_path.exists())

        with patch.object(
            resume_service,
            "parse_resume_pdf",
            side_effect=AssertionError("retry must not parse a known hash"),
        ):
            resume_task_service.retry_resume_task_item(created.task_id, item_id, None)
            await resume_task_service._background_tasks[f"{created.task_id}:{item_id}"]

        final = resume_task_service.get_resume_task(created.task_id)
        self.assertEqual(final.items[0].status, "success")
        self.assertEqual(final.items[0].outcome, "reused")
        self.assertEqual(final.items[0].candidate.id, winner_id)
        self.assertFalse(pending_path.exists())

    def test_candidates_without_hash_remain_valid(self) -> None:
        job = self.make_job("Legacy Null")
        candidate_id = f"candidate_dedupe_{uuid4().hex}"
        self.candidate_ids.append(candidate_id)
        save_candidate_for_job(Candidate(id=candidate_id), job.id, None)

        with SessionLocal() as db:
            row = db.get(CandidateModel, candidate_id)
            self.assertIsNone(row.resume_hash)


if __name__ == "__main__":
    unittest.main()
