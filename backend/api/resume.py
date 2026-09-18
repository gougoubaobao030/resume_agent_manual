import os
import shutil
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile
from typing import Annotated
from pydantic import WithJsonSchema

from clients.llm_client import (
    LLMConfigError,
    LLMRequestError,
    LLMResponseError,
)
from schemas.resume import (
    Candidate, ResumeBatchParseResponse, ResumeTaskResponse
)
from services.resume_service import (
    parse_resume_pdf,
    parse_resume_batch,
)

router = APIRouter(
    prefix="/api/resume",
    tags=["Resume"],
)
from services.resume_task_service import create_resume_task, get_resume_task

# Swagger UI currently does not render a file picker for arrays whose items use
# OpenAPI 3.1's ``contentMediaType``. Keep the runtime type as UploadFile while
# exposing the compatible binary-file schema for this endpoint.
SwaggerUploadFile = Annotated[
    UploadFile,
    WithJsonSchema({"type": "string", "format": "binary"}),
]

@router.post(
    "/parse",
    response_model=Candidate,
)
async def parse_resume(
    file: UploadFile = File(...)
) -> Candidate:

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="未提供文件名",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="仅支持PDF简历",
        )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf",
        ) as temp_file:

            shutil.copyfileobj(
                file.file,
                temp_file,
            )

            temp_path = temp_file.name

        candidate = await parse_resume_pdf(
            temp_path,
            source_file=file.filename,   
        )

        return candidate

    except LLMConfigError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"模型配置错误: {exc}",
        ) from exc

    except LLMRequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"模型服务请求失败: {exc}",
        ) from exc

    except LLMResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"模型返回格式错误: {exc}",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    finally:
        await file.close()

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@router.post(
    "/parse-batch",
    response_model=ResumeBatchParseResponse,
)
async def parse_resume_batch_api(
    files: list[SwaggerUploadFile] = File(...)
) -> ResumeBatchParseResponse:

    if not files:
        raise HTTPException(
            status_code=400,
            detail="请至少上传一份简历",
        )

    if len(files) > 30:
        raise HTTPException(
            status_code=400,
            detail="一次最多上传30份简历",
        )

    for file in files:

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="存在未提供文件名的文件",
            )

        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"{file.filename} 不是PDF文件",
            )

    temp_files = []

    try:

        for file in files:

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".pdf",
            ) as temp_file:

                shutil.copyfileobj(
                    file.file,
                    temp_file,
                )

                temp_files.append(
                    (
                        file.filename,
                        temp_file.name,
                    )
                )

        return await parse_resume_batch(
            temp_files
        )

    finally:

        for file in files:
            await file.close()

        for _, temp_path in temp_files:

            if os.path.exists(temp_path):
                os.remove(temp_path)


@router.post("/tasks", response_model=ResumeTaskResponse, status_code=202)
async def create_resume_task_api(
    files: list[SwaggerUploadFile] = File(...),
) -> ResumeTaskResponse:
    temp_files = []
    task_created = False
    try:
        if not files:
            raise HTTPException(status_code=400, detail="请至少上传一份简历")
        if len(files) > 30:
            raise HTTPException(status_code=400, detail="一次最多上传30份简历")
        for file in files:
            if not file.filename:
                raise HTTPException(status_code=400, detail="存在未提供文件名的文件")
            if not file.filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail=f"{file.filename} 不是PDF文件")

        for file in files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                # 先记录路径，复制中途失败时也能清理已创建的文件。
                temp_files.append((file.filename, temp_file.name))
                shutil.copyfileobj(file.file, temp_file)

        task = create_resume_task(temp_files)
        task_created = True
        return task
    finally:
        for file in files:
            await file.close()
        # 成功启动后，临时文件所有权交给 runner；这里不能立即删除。
        if not task_created:
            for _, temp_path in temp_files:
                if os.path.exists(temp_path):
                    os.remove(temp_path)


# 这里同步也可以 不过都是简历的事，又在简历并发，那就异步吧
@router.get("/tasks/{task_id}", response_model=ResumeTaskResponse)
async def get_resume_task_api(task_id: str) -> ResumeTaskResponse:
    task = get_resume_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="简历任务不存在")
    return task
