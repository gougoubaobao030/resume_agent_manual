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
    Candidate, ResumeBatchParseResponse
)
from services.resume_service import (
    parse_resume_pdf,
    parse_resume_batch,
)

router = APIRouter(
    prefix="/api/resume",
    tags=["Resume"],
)

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

        candidate = parse_resume_pdf(
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

        return parse_resume_batch(
            temp_files
        )

    finally:

        for file in files:
            await file.close()

        for _, temp_path in temp_files:

            if os.path.exists(temp_path):
                os.remove(temp_path)
