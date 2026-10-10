import asyncio
import logging
import os
from dataclasses import dataclass
from uuid import uuid4

from schemas.resume import ResumeTaskItem, ResumeTaskResponse
from repositories.candidate_repository import save_candidate_for_job
from services.resume_service import parse_resume_batch
from services.resume_storage import (
    delete_pending_resume,
    resolve_resume_path,
    store_pending_resume,
)

logger = logging.getLogger("uvicorn.error")


class ResumeTaskNotFoundError(Exception):
    pass


class ResumeTaskForbiddenError(Exception):
    pass


class ResumeTaskConflictError(Exception):
    pass


@dataclass
class ResumeTaskRecord:
    task: ResumeTaskResponse
    job_id: str | None
    user_id: str | None
    pending_resumes: dict[str, str]


# 教学 MVP：只保存在当前进程内，重启会丢失，不与其他 worker 共享。
task_store: dict[str, ResumeTaskRecord] = {}
# 保留 asyncio.Task 的强引用，直到 runner 结束；它与业务状态不是同一个对象。
_background_tasks: dict[str, asyncio.Task] = {}


def _refresh_task_summary(task: ResumeTaskResponse) -> None:
    task.success_count = sum(item.status == "success" for item in task.items)
    task.failed_count = sum(item.status == "failed" for item in task.items)
    if any(item.status in {"pending", "running"} for item in task.items):
        task.status = "running"
    else:
        task.status = "completed_with_errors" if task.failed_count else "completed"


def _pending_files(record: ResumeTaskRecord) -> list[tuple[str, str]]:
    return [
        (
            item.filename,
            str(resolve_resume_path(record.pending_resumes[item.item_id])),
        )
        for item in record.task.items
    ]


async def _persist_candidate(
    record: ResumeTaskRecord,
    candidate,
    pdf_path: str,
    pending_resume_path: str,
) -> None:
    if record.job_id is not None:
        await asyncio.to_thread(
            save_candidate_for_job,
            candidate,
            record.job_id,
            record.user_id,
            pdf_path,
        )

    # 只有 Candidate 的正式 PDF 和数据库提交成功后，才删除 pending PDF。
    try:
        await asyncio.to_thread(delete_pending_resume, pending_resume_path)
    except OSError:
        # Candidate 已完整持久化，pending 清理失败不应把成功项变成可重复执行的失败项。
        logger.exception(
            "[Resume Task] 清理 pending PDF 失败 %s",
            pending_resume_path,
        )


def create_resume_task(
    files: list[tuple[str, str]],
    job_id: str | None = None,
    user_id: str | None = None,
) -> ResumeTaskResponse:
    if not files:
        raise ValueError("请至少提供一份简历")

    task_id = f"resume_task_{uuid4().hex}"
    task = ResumeTaskResponse(
        task_id=task_id,
        total=len(files),
        status="pending",
        items=[
            ResumeTaskItem(
                item_id=f"{task_id}_item_{index + 1}",
                filename=filename,
                status="pending",
            )
            for index, (filename, _) in enumerate(files)
        ],
    )

    pending_resumes: dict[str, str] = {}
    try:
        for item, (_, source_path) in zip(task.items, files, strict=True):
            pending_resumes[item.item_id] = store_pending_resume(
                source_path,
                task_id,
                item.item_id,
            )
    except Exception:
        for resume_path in pending_resumes.values():
            try:
                delete_pending_resume(resume_path)
            except OSError:
                logger.exception(
                    "[Resume Task] 回滚 pending PDF 失败 %s",
                    resume_path,
                )
        raise
    finally:
        # create_resume_task 接管调用方传入的上传临时文件，稳定保存后立即释放。
        for _, source_path in files:
            try:
                if os.path.exists(source_path):
                    os.remove(source_path)
            except OSError:
                logger.exception("[Resume Task] 清理上传临时文件失败 %s", source_path)

    record = ResumeTaskRecord(
        task=task,
        job_id=job_id,
        user_id=user_id,
        pending_resumes=pending_resumes,
    )
    task_store[task_id] = record

    background_task = asyncio.create_task(run_resume_task(task_id))
    _background_tasks[task_id] = background_task
    background_task.add_done_callback(lambda _: _background_tasks.pop(task_id, None))
    return task.model_copy(deep=True)


def get_resume_task(task_id: str) -> ResumeTaskResponse | None:
    record = task_store.get(task_id)
    if record is None:
        return None

    snapshot = record.task.model_copy(deep=True)
    snapshot.success_count = sum(item.status == "success" for item in snapshot.items)
    snapshot.failed_count = sum(item.status == "failed" for item in snapshot.items)
    return snapshot


async def run_resume_task(task_id: str) -> None:
    record = task_store[task_id]
    task = record.task
    task.status = "running"
    files = _pending_files(record)
    pending_by_path = {
        pdf_path: record.pending_resumes[item.item_id]
        for item, (_, pdf_path) in zip(task.items, files, strict=True)
    }
    logger.info("[Resume Task] START %s total=%s", task_id, task.total)
    try:
        async def persist_candidate(candidate, pdf_path: str) -> None:
            await _persist_candidate(
                record,
                candidate,
                pdf_path,
                pending_by_path[pdf_path],
            )

        await parse_resume_batch(
            files,
            task_items=task.items,
            on_candidate_parsed=persist_candidate,
        )
        _refresh_task_summary(task)
    except Exception as exc:
        # 单文件业务异常已被 worker 捕获；这里处理批次编排本身的异常。
        logger.exception("[Resume Task] FAILED %s", task_id)
        task.status = "failed"
        task.error = str(exc)
        for item in task.items:
            if item.status in {"pending", "running"}:
                item.status = "failed"
                item.error = f"批次执行失败: {exc}"
        task.success_count = sum(item.status == "success" for item in task.items)
        task.failed_count = sum(item.status == "failed" for item in task.items)
    finally:
        logger.info("[Resume Task] DONE %s status=%s", task_id, task.status)


async def run_resume_task_item(task_id: str, item_id: str) -> None:
    record = task_store[task_id]
    task = record.task
    item = next(item for item in task.items if item.item_id == item_id)
    pending_resume_path = record.pending_resumes[item_id]
    pdf_path = str(resolve_resume_path(pending_resume_path))

    try:
        async def persist_candidate(candidate, parsed_pdf_path: str) -> None:
            await _persist_candidate(
                record,
                candidate,
                parsed_pdf_path,
                pending_resume_path,
            )

        await parse_resume_batch(
            [(item.filename, pdf_path)],
            task_items=[item],
            on_candidate_parsed=persist_candidate,
        )
    except Exception as exc:
        logger.exception("[Resume Task Retry] FAILED %s %s", task_id, item_id)
        item.status = "failed"
        item.error = str(exc)
    finally:
        _refresh_task_summary(task)


def retry_resume_task_item(
    task_id: str,
    item_id: str,
    user_id: str | None,
) -> ResumeTaskResponse:
    record = task_store.get(task_id)
    if record is None:
        raise ResumeTaskNotFoundError("简历任务不存在")
    if record.user_id != user_id:
        raise ResumeTaskForbiddenError("不能重新解析其他用户的简历任务")

    item = next((item for item in record.task.items if item.item_id == item_id), None)
    if item is None:
        raise ResumeTaskNotFoundError("简历任务项不存在")
    if record.task.status not in {"completed_with_errors", "failed"}:
        raise ResumeTaskConflictError("简历任务仍在执行，请等待任务完成后重试")
    if item.status != "failed":
        raise ResumeTaskConflictError("只有解析失败的简历可以重新解析")

    pending_resume_path = record.pending_resumes.get(item_id)
    if (
        pending_resume_path is None
        or not resolve_resume_path(pending_resume_path).is_file()
    ):
        raise ResumeTaskConflictError("待重新解析的原始简历已不存在")

    # 在创建后台任务前同步切换状态，阻止双击生成两个 Candidate。
    item.status = "running"
    item.error = None
    item.candidate = None
    record.task.status = "running"
    record.task.error = None
    _refresh_task_summary(record.task)

    background_key = f"{task_id}:{item_id}"
    background_task = asyncio.create_task(run_resume_task_item(task_id, item_id))
    _background_tasks[background_key] = background_task
    background_task.add_done_callback(
        lambda _: _background_tasks.pop(background_key, None)
    )
    snapshot = get_resume_task(task_id)
    assert snapshot is not None
    return snapshot
