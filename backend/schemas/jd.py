from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class JDCategory(str, Enum):
    """JD 要求条目的分类。"""

    TECHNICAL = "technical"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    OTHER = "other"


#clas JDReuirement(BaseModel)继承了BaseModel属性
#field 是给每个字段添加规则
#field_validator 补充自定义清洗规则
class JDRequirement(BaseModel):
    """JD 中的一条岗位要求。"""

    #注意这里生成这个岗位里某一条要求的唯一标识
    #假如这里生成的时候没有传
    """
    item = JDRequirement(
    id="req_custom001",
    name="Python经验",
    )
    """
    #之类的内容，就会自动生成id，这是field自带的作用
    id: str = Field(
        default_factory=lambda: f"req_{uuid4().hex[:8]}",
        description="岗位要求的唯一标识",
    )

    name: str = Field(
        min_length=1,
        max_length=100,
        description="岗位要求的简短名称",
    )

    description: str = Field(
        default="",
        max_length=1000,
        description="岗位要求的详细说明",
    )

    category: JDCategory = Field(
        default=JDCategory.OTHER,
        description="岗位要求分类",
    )

    weight: float = Field(
        default=1.0,
        ge=0,
        le=1000,
        description="HR 设置的相对权重，不要求总和为 100",
    )

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        """去掉文本前后的多余空格。"""

        return value.strip()


class JDInfo(BaseModel):
    """完整的结构化 JD。"""

    id: str = Field(
        default_factory=lambda: f"job_{uuid4().hex[:8]}",
        description="岗位的唯一标识",
    )

    job_title: str = Field(
        min_length=1,
        max_length=100,
        description="岗位名称",
    )

    raw_text: str = Field(
        min_length=1,
        description="用户输入的原始 JD 文本",
    )

    requirements: list[JDRequirement] = Field(
        default_factory=list,
        description="解析并经过 HR 确认的岗位要求列表",
    )

    @field_validator("job_title", "raw_text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        """去掉文本前后的多余空格。"""

        return value.strip()
    
#接下来把把 JD 领域数据 和 JD 解析接口数据 分开。
#分成三种接口 因为
#JDInfo 表示系统内部的一份完整 JD；
#接口请求只需要传“待解析的原始文本”；
#接口响应还可能需要返回解析状态、警告信息；
#后面 HR 保存修改结果时，又是另一种请求。

#给纯文本的岗位描述，接收岗位描述
class JDParseRequest(BaseModel):
    """JD 解析接口的请求数据。"""

    raw_text: str = Field(
        min_length=10,
        max_length=20000,
        description="需要解析的原始 JD 文本",
    )

    @field_validator("raw_text")
    @classmethod
    def strip_raw_text(cls, value: str) -> str:
        """清理原始 JD 前后的空格，并拒绝纯空白内容。"""

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("JD 文本不能为空")

        return cleaned_value

# 返回的JD结构，但并非等于最终结构，返回给前端时还会带有各种警告
class JDParseResponse(BaseModel):
    """JD 解析接口的响应数据。"""

    job: JDInfo = Field(
        description="解析得到的结构化 JD",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="解析过程中的非致命提示",
    )

#最终权重修改，条目增减后保存的数据，可以关联数据库
class JDSaveRequest(BaseModel):
    """HR 确认并保存 JD 时提交的数据。"""

    job_title: str = Field(
        min_length=1,
        max_length=100,
        description="HR 确认后的岗位名称",
    )

    raw_text: str = Field(
        min_length=1,
        max_length=20000,
        description="原始 JD 文本",
    )

    requirements: list[JDRequirement] = Field(
        min_length=1,
        description="HR 确认后的岗位要求列表",
    )

    @field_validator("job_title", "raw_text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        """去掉文本前后的多余空格。"""

        return value.strip()

#这个是对下面最终返回做的约束    
class LLMJDRequirement(BaseModel):
    """大模型解析得到的一条岗位要求。"""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="岗位要求的简短名称",
    )

    description: str = Field(
        default="",
        max_length=1000,
        description="岗位要求的详细说明",
    )

    category: JDCategory = Field(
        default=JDCategory.OTHER,
        description="岗位要求分类",
    )

    weight: float = Field(
        default=1.0,
        ge=0,
        le=1000,
        description="模型建议的相对权重",
    )

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        """去掉模型输出文本前后的多余空格。"""

        return value.strip()

# 最终返回的是这个
class LLMJDResult(BaseModel):
    """大模型解析 JD 后应返回的数据。"""

    job_title: str = Field(
        min_length=1,
        max_length=100,
        description="从 JD 中识别出的岗位名称",
    )

    requirements: list[LLMJDRequirement] = Field(
        default_factory=list,
        description="从 JD 中提取出的岗位要求列表",
    )

    @field_validator("job_title")
    @classmethod
    def strip_job_title(cls, value: str) -> str:
        """去掉岗位名称前后的多余空格。"""

        return value.strip()