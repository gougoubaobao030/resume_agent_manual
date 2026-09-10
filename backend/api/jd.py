from fastapi import APIRouter, HTTPException, status

from clients.llm_client import (
    LLMConfigError,
    LLMRequestError,
    LLMResponseError,
)
from schemas.jd import (
    JDParseRequest,
    JDParseResponse,
    JDSaveRequest,
    JDSaveResponse,
    JDUpdateRequest,
    JDInfo,
)
from services.jd_service import parse_jd, build_jd_info

from services.jd_repository import (
    save_jd,
    get_jd,
    update_jd,
    #这里全部是增删改查的一部分
)

#这是一个路由，这个路由文件前面都加"/api/jd"
router = APIRouter(
    prefix="/api/jd",
    tags=["JD"],
)


@router.post(
    "/parse",
    response_model=JDParseResponse,
)
#异常抛个前端用
def parse_jd_api(
    request: JDParseRequest,
) -> JDParseResponse:
    """
    解析岗位JD。

    接收原始JD文本，
    调用LLM解析，
    返回结构化岗位要求。
    """

    try:
        result = parse_jd(
            raw_text=request.raw_text,
        )

        return result


    except LLMConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


    except LLMRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )


    except LLMResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )


    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

#增加保存接口  第一次保存确认下来的JD解析条目 保存到临时数据库  
#增删改查的一部分
@router.post(
    "",
    response_model=JDSaveResponse,
)
def save_jd_api(
    request: JDSaveRequest,
):

    job = JDInfo(
        job_title=request.job_title,
        raw_text=request.raw_text,
        requirements=request.requirements,
    )


    saved_job = save_jd(job)


    return JDSaveResponse(
        job=saved_job
    )

#增加查询接口 输入id查询临时数据库已经保存的jd解析 增删改查的一部分
@router.get(
    "/{job_id}",
    response_model=JDInfo,
)
def get_jd_api(
    job_id: str,
):

    job = get_jd(job_id)


    if job is None:
        raise HTTPException(
            status_code=404,
            detail="JD不存在",
        )


    return job

#增加修改接口 针对已经保存过的内容，再次修改保存时使用 增删改查的一部分
@router.put(
    "/{job_id}",
    response_model=JDInfo,
)
def update_jd_api(
    job_id: str,
    request: JDUpdateRequest,
):

    old_job = get_jd(job_id)


    if old_job is None:
        raise HTTPException(
            status_code=404,
            detail="JD不存在",
        )


    updated_job = JDInfo(
        id=job_id,
        job_title=request.job_title,
        raw_text=old_job.raw_text,
        requirements=request.requirements,
    )


    return update_jd(
        job_id,
        updated_job,
    )