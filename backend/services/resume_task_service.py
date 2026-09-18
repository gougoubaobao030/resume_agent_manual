import asyncio
import logging
import os
from uuid import uuid4

from schemas.resume import ResumeTaskItem, ResumeTaskResponse
from services.resume_service import parse_resume_batch

logger = logging.getLogger("uvicorn.error")

# 教学 MVP：只保存在当前进程内，重启会丢失，不与其他 worker 共享。
task_store: dict[str, ResumeTaskResponse] = {}
# 保留 asyncio.Task 的强引用，直到 runner 结束；它与业务状态不是同一个对象。
_background_tasks: dict[str, asyncio.Task] = {}


def create_resume_task(files: list[tuple[str, str]]) -> ResumeTaskResponse:
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
    task_store[task_id] = task

    # 不 await 整个批次：调用方拿到快照即可返回，runner 由事件循环继续调度。
    # 如果不asyncio出去一个协程，(注意不是线程) ，依旧是等await结束才返回task_id
    # 状态管理是实现了，但是状态查询呢？
    # 移出去的协程不是另一个线程去做，是事件循环的会看看有没有空做(说的好凌乱)
    # 异步也是有要等和不用等随它去的
    background_task = asyncio.create_task(run_resume_task(task_id, files))
    #保存正在执行的业务对象
    #后台保存的是协程不是线程
    _background_tasks[task_id] = background_task
    background_task.add_done_callback(lambda _: _background_tasks.pop(task_id, None))
    return task.model_copy(deep=True)


def get_resume_task(task_id: str) -> ResumeTaskResponse | None:
    task = task_store.get(task_id)
    if task is None:
        return None

    # 返回快照，避免 API 调用方修改 store；运行中的计数从单项状态直接计算。
    # 1. 被存到了全局 / store / cache 里
    # 2. 后面还会继续被修改
    # 3. 当前又要把它交给别的地方 就要有搞快照意识
    snapshot = task.model_copy(deep=True)
    snapshot.success_count = sum(item.status == "success" for item in snapshot.items)
    snapshot.failed_count = sum(item.status == "failed" for item in snapshot.items)
    return snapshot


# runner
# 负责总状态、结果汇总、批次级异常、临时文件清理。
async def run_resume_task(task_id: str, files: list[tuple[str, str]]) -> None:
    task = task_store[task_id]
    task.status = "running"
    logger.info("[Resume Task] START %s total=%s", task_id, task.total)
    try:
        # 复用前四步：同一个 gather、Semaphore(3) 和单文件失败隔离 worker。
        result = await parse_resume_batch(files, task_items=task.items)
        task.success_count = result.success_count
        task.failed_count = result.failed_count
        task.status = "completed_with_errors" if result.failed_count else "completed"
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
        # POST 已返回，但 PDF 仍属于 runner；所有解析结束后才释放文件。
        # 每个文件独立清理，某个删除失败也不妨碍尝试删除其他文件。
        for _, temp_path in files:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except OSError:
                logger.exception("[Resume Task] 清理临时文件失败 %s", temp_path)
        logger.info("[Resume Task] DONE %s status=%s", task_id, task.status)
