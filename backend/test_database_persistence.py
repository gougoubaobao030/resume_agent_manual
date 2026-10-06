import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from schemas.jd import JDInfo, JDRequirement
from schemas.resume import Candidate
from schemas.scoring import JobMatchResult
from schemas.talent import TalentDiscoveryResult
from services import resume_service, resume_task_service
from services import resume_storage
from services.candidate_repository import (
    delete_candidate,
    get_candidate,
    get_candidate_resume_info,
)
from services.jd_repository import delete_jd, save_jd, update_jd
from services.result_repository import (
    get_scoring_result,
    get_talent_result,
    save_scoring_result,
    save_talent_result,
)


class DatabasePersistenceTest(unittest.IsolatedAsyncioTestCase):
    async def test_candidate_is_committed_before_task_item_success(self):
        job = save_jd(JDInfo(
            job_title="顺序测试",
            raw_text="用于验证持久化顺序的岗位文本",
            requirements=[JDRequirement(name="Python")],
        ))
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        handle.close()

        async def fake_parse(**_kwargs):
            return Candidate(id="candidate_order_test", raw_text="evidence")

        try:
            with tempfile.TemporaryDirectory() as storage_dir, patch.object(
                resume_storage, "DATA_ROOT", Path(storage_dir)
            ), patch.object(resume_service, "parse_resume_pdf", side_effect=fake_parse):
                created = resume_task_service.create_resume_task(
                    [("A.pdf", handle.name)], job_id=job.id
                )
                await resume_task_service._background_tasks[created.task_id]
                final = resume_task_service.get_resume_task(created.task_id)

                self.assertEqual(final.items[0].status, "success")
                self.assertEqual(get_candidate("candidate_order_test").raw_text, "evidence")
                resume_path, _ = get_candidate_resume_info("candidate_order_test")
                self.assertEqual(
                    resume_path,
                    "resumes/candidate_order_test/original.pdf",
                )
                self.assertTrue((Path(storage_dir) / resume_path).is_file())
        finally:
            delete_candidate("candidate_order_test")
            delete_jd(job.id)
            Path(handle.name).unlink(missing_ok=True)

    async def test_result_json_round_trip_and_revision_staleness(self):
        job = save_jd(JDInfo(
            job_title="结果测试",
            raw_text="用于验证结果JSON和revision的岗位文本",
            requirements=[JDRequirement(name="Python")],
        ))
        candidate = Candidate(id="candidate_result_test", raw_text="Python")
        from services.candidate_repository import save_candidate_for_job
        save_candidate_for_job(candidate, job.id, None)
        try:
            scoring = JobMatchResult(
                job_id=job.id,
                candidate_id=candidate.id,
                analysis_language="zh-CN",
                score=88,
                confidence="high",
                summary="匹配",
            )
            save_scoring_result(scoring, job_revision=1, user_id=None)
            self.assertEqual(get_scoring_result(job.id, candidate.id).score, 88)

            auto_talent = TalentDiscoveryResult(
                candidate_id=candidate.id,
                analysis_language="zh-CN",
                mode="auto",
                attention_level="high",
                summary="值得关注",
            )
            specified_talent = TalentDiscoveryResult(
                candidate_id=candidate.id,
                analysis_language="zh-CN",
                mode="specified",
                specified_fit_level="medium_high",
                summary="符合指定人才像",
            )
            save_talent_result(auto_talent, desired_traits=[], user_id=None)
            save_talent_result(
                specified_talent, desired_traits=["认真"], user_id=None
            )
            self.assertEqual(
                get_talent_result(candidate.id, "auto").summary, "值得关注"
            )
            self.assertEqual(
                get_talent_result(candidate.id, "specified").summary,
                "符合指定人才像",
            )

            updated_auto_talent = auto_talent.model_copy(
                update={"summary": "更新后的自动发现结果"}
            )
            save_talent_result(updated_auto_talent, desired_traits=[], user_id=None)
            self.assertEqual(
                get_talent_result(candidate.id, "auto").summary,
                "更新后的自动发现结果",
            )
            self.assertEqual(
                get_talent_result(candidate.id, "specified").summary,
                "符合指定人才像",
            )

            update_jd(job.id, job)
            self.assertIsNone(get_scoring_result(job.id, candidate.id))
        finally:
            delete_candidate(candidate.id)
            delete_jd(job.id)


if __name__ == "__main__":
    unittest.main()
