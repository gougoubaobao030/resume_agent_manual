from pathlib import Path
from uuid import uuid4

import asyncio
import hashlib
import logging
import os
import random
import time

from clients.llm_client import LLMClient

from prompts.resume_prompt import (
    RESUME_SYSTEM_PROMPT,
    RESUME_USER_PROMPT_TEMPLATE,
)
from schemas.resume import (
    BasicInfo,
    Candidate,
    CandidateEvidence,
    Education,
    ExtractionMetadata,
    Project,
    ResumeLLMResult,
    WorkExperience,
    ResumeBatchParseResponse,
    ResumeParseItemResult,
    ResumeTaskItem,
)
logger = logging.getLogger("uvicorn.error")

_llm_client: LLMClient | None = None


def _is_resume_mock_enabled() -> bool:
    """判断是否启用简历解析的开发测试 Mock。"""

    return os.getenv(
        "RESUME_USE_MOCK",
        "false",
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _get_llm_client() -> LLMClient:
    """只在真实简历解析分支中初始化并复用 LLM 客户端。"""

    global _llm_client

    if _llm_client is None:
        _llm_client = LLMClient()

    return _llm_client


def _extract_pdf_text_real(pdf_path: str) -> str:
    """仅在真实解析分支加载并调用 PDF 文本解析器。"""

    from services.pdf_service import extract_pdf_text

    return extract_pdf_text(pdf_path)

def _generate_candidate_id() -> str:
    return f"candidate_{uuid4().hex[:8]}"


def _build_mock_candidate(source_file: str) -> Candidate:
    """根据任意上传文件名构造符合现有 Candidate schema 的结果。"""

    filename = Path(source_file).name
    display_name = Path(filename).stem.strip() or "未命名简历"
    filename_digest = hashlib.sha256(
        filename.encode("utf-8")
    ).hexdigest()[:12]

    return Candidate(
        id=f"candidate_mock_{filename_digest}",
        basic_info=BasicInfo(
            name=f"Mock候选人 · {display_name}",
        ),
        skills=["Python", "FastAPI", "LLM应用开发"],
        languages=["中文"],
        candidate_evidence=[
            CandidateEvidence(
                category="mock",
                title="Resume Mock 测试数据",
                description=f"此候选人由上传文件 {filename} 生成。",
                evidence=[f"source_file={filename}"],
            )
        ],
        custom_attributes={"resume_mock": True},
        raw_text=f"Resume Mock 测试数据，来源文件：{filename}",
        extraction_metadata=ExtractionMetadata(
            source_file=filename,
            parser="resume-mock",
            model="resume-mock",
            confidence=1.0,
        ),
    )


async def _parse_resume_pdf_mock(source_file: str) -> Candidate:
    """模拟一次耗时 2～3 秒的外部 I/O，并返回 Mock Candidate。"""

    delay_seconds = random.uniform(2.0, 3.0)
    started_at = time.perf_counter()

    logger.info("[Resume Mock] START %s", source_file)
    await asyncio.sleep(delay_seconds)
    elapsed_seconds = time.perf_counter() - started_at
    logger.info(
        "[Resume Mock] DONE  %s elapsed=%.2fs",
        source_file,
        elapsed_seconds,
    )

    return _build_mock_candidate(source_file)


def _build_candidate(
    llm_result: ResumeLLMResult,
    raw_text: str,
    source_file: str | None = None,
) -> Candidate:

    basic_info = None

    if llm_result.basic_info is not None:
        basic_info = BasicInfo.model_validate(
            llm_result.basic_info.model_dump()
        )

    education = [
        Education.model_validate(item.model_dump())
        for item in llm_result.education
    ]

    work_experience = [
        WorkExperience.model_validate(item.model_dump())
        for item in llm_result.work_experience
    ]

    projects = [
        Project.model_validate(item.model_dump())
        for item in llm_result.projects
    ]

    candidate_evidence = [
        CandidateEvidence.model_validate(item.model_dump())
        for item in llm_result.candidate_evidence
    ]

    return Candidate(
        id=_generate_candidate_id(),
        basic_info=basic_info,
        education=education,
        work_experience=work_experience,
        projects=projects,
        skills=llm_result.skills,
        languages=llm_result.languages,
        achievements=llm_result.achievements,
        certifications=llm_result.certifications,
        candidate_evidence=candidate_evidence,
        custom_attributes={},
        raw_text=raw_text,
        extraction_metadata=ExtractionMetadata(
            source_file=source_file,
            parser="unstructured",
        ),
    )


def parse_resume_text(
    raw_text: str,
    source_file: str | None = None,
) -> Candidate:

    cleaned_text = raw_text.strip()

    if not cleaned_text:
        raise ValueError(
            "简历文本为空，无法解析"
        )

    user_prompt = RESUME_USER_PROMPT_TEMPLATE.format(
        resume_text=cleaned_text
    )

    #以后要批量的
    #llm_client = LLMClient()

    llm_result = _get_llm_client().generate_structured(
        system_prompt=RESUME_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=ResumeLLMResult,
    )

    return _build_candidate(
        llm_result=llm_result,
        raw_text=cleaned_text,
        source_file=source_file,
    )

# 另外拆出一个同步的pdf解析函数
# 里面有同步的text解析
# 也是在text里面调用大模型的
# 拆出来为了在异步适配器里一步步学习异步并发以及
# 临时asyncio.to_thread用
def _parse_resume_pdf_real(
    path: Path,
    source_file: str | None = None,
) -> Candidate:

    raw_text = _extract_pdf_text_real(
        str(path)
    )

    if not raw_text.strip():
        raise ValueError(
            "无法解析简历，请上传文本型PDF"
        )

    return parse_resume_text(
        raw_text=raw_text,
        source_file=source_file or path.name,
    )

# 这里被改造成了一个异步适配器
async def parse_resume_pdf(
    pdf_path: str,
    source_file: str | None = None,
) -> Candidate:

    path = Path(pdf_path)

    if _is_resume_mock_enabled():
        return await _parse_resume_pdf_mock(
            source_file=source_file or path.name,
        )

    # 这里是移出一个线程不是协程；
    # 但依旧用异步方式等线程返回
    return await asyncio.to_thread(
        _parse_resume_pdf_real,
        path,
        source_file,
    )

# 于是原函数暂时作废
#async def parse_resume_pdf(
#    pdf_path: str,
#    source_file: str | None = None,
#) -> Candidate:
#
#    path = Path(pdf_path)
#
#    if _is_resume_mock_enabled():
#        return await _parse_resume_pdf_mock(
#            source_file=source_file or path.name,
#        )
#
#    raw_text = _extract_pdf_text_real(
#        str(path)
#    )
#
#    if not raw_text.strip():
#        raise ValueError(
#            "无法解析简历，请上传文本型PDF"
#        )
#
#    return parse_resume_text(
#        raw_text=raw_text,
#        source_file=source_file or path.name,
#    )


#把从前的for 循环拆成单份worker
async def _parse_resume_item(
    filename: str,
    pdf_path: str,
    semaphore: asyncio.Semaphore,
    task_item: ResumeTaskItem | None = None,
) -> ResumeParseItemResult:

    async with semaphore:
        # 排队等待名额时仍是 pending；running 表示现在真的开始解析。
        if task_item is not None:
            task_item.status = "running"
        try:
            candidate = await parse_resume_pdf(
                pdf_path=pdf_path,
                source_file=filename,
            )

            if task_item is not None:
                task_item.candidate = candidate
                task_item.status = "success"

            return ResumeParseItemResult(
                filename=filename,
                success=True,
                candidate=candidate,
            )

        except Exception as exc:
            logger.exception("[Resume Item] FAILED %s", filename)
            if task_item is not None:
                task_item.error = str(exc)
                task_item.status = "failed"
            return ResumeParseItemResult(
                filename=filename,
                success=False,
                error=str(exc),
            )

#我们来掌握三句话
#1. for 里逐个 await = 串行。
#2. gather 会让多个协程一起交给事件循环调度。
#3. 并发执行顺序可以乱，但 gather 返回结果顺序与输入顺序一致。
async def parse_resume_batch(
    files: list[tuple[str, str]],
    *,
    task_items: list[ResumeTaskItem] | None = None,
) -> ResumeBatchParseResponse:

    if task_items is not None and len(task_items) != len(files):
        raise ValueError("任务状态项数量与文件数量不一致")

    # 并发控制
    semaphore = asyncio.Semaphore(3)

    tasks = [
        _parse_resume_item(
            filename=filename,
            pdf_path=pdf_path,
            semaphore=semaphore,
            task_item=task_items[index] if task_items is not None else None,
        )
        for index, (filename, pdf_path) in enumerate(files)
    ]

    results = await asyncio.gather(*tasks)

    success_count = sum(
        1
        for result in results
        if result.success
    )

    failed_count = len(results) - success_count

    return ResumeBatchParseResponse(
        total=len(results),
        success_count=success_count,
        failed_count=failed_count,
        results=results,
    )

# 原来旧批量处理函数作废咧
#async def parse_resume_batch(
#    files: list[tuple[str, str]],
#) -> ResumeBatchParseResponse:
#
#    results = []
#
#    for filename, pdf_path in files:
#
#        try:
#            candidate = await parse_resume_pdf(
#                pdf_path=pdf_path,
#                source_file=filename,
#            )
#
#            results.append(
#                ResumeParseItemResult(
#                    filename=filename,
#                    success=True,
#                    candidate=candidate,
#                )
#            )
#
#        except Exception as exc:
#            results.append(
#                ResumeParseItemResult(
#                    filename=filename,
#                    success=False,
#                    error=str(exc),
#                )
#            )
#
#    success_count = sum(
#        1
#        for result in results
#        if result.success
#    )
#
#    failed_count = len(results) - success_count
#
#    return ResumeBatchParseResponse(
#        total=len(results),
#        success_count=success_count,
#        failed_count=failed_count,
#        results=results,
#    )
