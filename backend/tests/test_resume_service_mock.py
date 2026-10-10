import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

from services import resume_service


class ResumeMockTest(unittest.IsolatedAsyncioTestCase):
    async def test_mock_skips_pdf_and_llm_and_uses_expected_delay(self) -> None:
        with (
            patch.dict(os.environ, {"RESUME_USE_MOCK": "true"}),
            patch.object(
                resume_service.asyncio,
                "sleep",
                new=AsyncMock(),
            ) as sleep_mock,
            patch.object(
                resume_service,
                "_extract_pdf_text_real",
                side_effect=AssertionError("Mock 不应解析 PDF"),
            ),
            patch.object(
                resume_service,
                "_get_llm_client",
                side_effect=AssertionError("Mock 不应初始化 LLM"),
            ),
        ):
            candidate = await resume_service.parse_resume_pdf(
                pdf_path="does-not-need-to-exist.pdf",
                source_file="任意文件名.pdf",
            )

        delay_seconds = sleep_mock.await_args.args[0]
        self.assertGreaterEqual(delay_seconds, 2.0)
        self.assertLessEqual(delay_seconds, 3.0)
        self.assertTrue(candidate.id.startswith("candidate_mock_"))
        self.assertIn("任意文件名", candidate.basic_info.name)
        self.assertEqual(
            candidate.extraction_metadata.source_file,
            "任意文件名.pdf",
        )

    async def test_real_mode_has_no_mock_sleep(self) -> None:
        with (
            patch.dict(os.environ, {"RESUME_USE_MOCK": "false"}),
            patch.object(
                resume_service.asyncio,
                "sleep",
                new=AsyncMock(),
            ) as sleep_mock,
            patch.object(
                resume_service,
                "_extract_pdf_text_real",
                return_value="真实简历文本",
            ) as extract_mock,
            patch.object(
                resume_service,
                "parse_resume_text",
                return_value=resume_service.Candidate(
                    id="candidate_real_test",
                ),
            ) as parse_text_mock,
        ):
            candidate = await resume_service.parse_resume_pdf(
                pdf_path="real-path.pdf",
                source_file="real.pdf",
            )

        sleep_mock.assert_not_awaited()
        extract_mock.assert_called_once_with("real-path.pdf")
        parse_text_mock.assert_called_once_with(
            raw_text="真实简历文本",
            source_file="real.pdf",
        )
        self.assertEqual(candidate.id, "candidate_real_test")

    async def test_batch_starts_files_concurrently(self) -> None:
        events = []

        async def fake_parse(pdf_path: str, source_file: str):
            events.append(f"START {source_file}")
            await asyncio.sleep(0)
            events.append(f"DONE {source_file}")
            return resume_service.Candidate(
                id=f"candidate_{source_file}",
            )

        with patch.object(
            resume_service,
            "parse_resume_pdf",
            side_effect=fake_parse,
        ):
            result = await resume_service.parse_resume_batch(
                [
                    ("a.pdf", "a-path.pdf"),
                    ("b.pdf", "b-path.pdf"),
                    ("c.pdf", "c-path.pdf"),
                ]
            )

        self.assertEqual(
            events,
            [
                "START a.pdf",
                "START b.pdf",
                "START c.pdf",
                "DONE a.pdf",
                "DONE b.pdf",
                "DONE c.pdf",
            ],
        )
        self.assertEqual(result.success_count, 3)
        self.assertEqual(result.failed_count, 0)


if __name__ == "__main__":
    unittest.main()
