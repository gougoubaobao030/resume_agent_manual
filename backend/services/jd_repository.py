#简单储存层
from schemas.jd import JDInfo


# 临时内存存储
# 后面替换成数据库
_jd_storage: dict[str, JDInfo] = {}


def save_jd(
    job: JDInfo,
) -> JDInfo:
    """
    保存JD。
    """

    _jd_storage[job.id] = job

    return job



def get_jd(
    job_id: str,
) -> JDInfo | None:
    """
    根据ID获取JD。
    """

    return _jd_storage.get(job_id)



def update_jd(
    job_id: str,
    job: JDInfo,
) -> JDInfo:

    _jd_storage[job_id] = job

    return job