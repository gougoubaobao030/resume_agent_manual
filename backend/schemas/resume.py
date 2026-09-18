from typing import List, Optional

from pydantic import BaseModel, Field
from typing import Literal

#定义candidate字段的二级基本字段
class BasicInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

class Education(BaseModel):
    school: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class WorkExperience(BaseModel):
    company: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None

class Project(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)

class CandidateEvidence(BaseModel):
    category: Optional[str] = None

    title: Optional[str] = None

    description: Optional[str] = None

    evidence: List[str] = Field(
        default_factory=list
    )

class ExtractionMetadata(BaseModel):
    source_file: Optional[str] = None
    parser: Optional[str] = None
    model: Optional[str] = None
    confidence: Optional[float] = None

#最终内部使用的格式
class Candidate(BaseModel):

    id: Optional[str] = None

    basic_info: Optional[BasicInfo] = None

    education: List[Education] = Field(
        default_factory=list
    )

    work_experience: List[WorkExperience] = Field(
        default_factory=list
    )

    projects: List[Project] = Field(
        default_factory=list
    )

    skills: List[str] = Field(
        default_factory=list
    )

    languages: List[str] = Field(
        default_factory=list
    )

    achievements: List[str] = Field(
        default_factory=list
    )

    certifications: List[str] = Field(
        default_factory=list
    )

    candidate_evidence: List[CandidateEvidence] = Field(
        default_factory=list
    )

    custom_attributes: dict = Field(
        default_factory=dict
    )

    raw_text: Optional[str] = None

    extraction_metadata: Optional[ExtractionMetadata] = None

#让大模型去抽取的格式
#DTO分层设计数据分流
#比如大模型不需要抽取年龄，姓名，这些后端会找
#比如更明显的，大模型抽取来源，内部评分结构可能就用不到
class LLMBasicInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

class LLMEducation(BaseModel):
    school: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class LLMWorkExperience(BaseModel):
    company: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None

class LLMProject(BaseModel):

    name: Optional[str] = None

    description: Optional[str] = None

    technologies: List[str] = Field(
        default_factory=list
    )

    achievements: List[str] = Field(
        default_factory=list
    )

class LLMCandidateEvidence(BaseModel):

    category: Optional[str] = None

    title: Optional[str] = None

    description: Optional[str] = None

    evidence: List[str] = Field(
        default_factory=list
    )

class ResumeLLMResult(BaseModel):

    basic_info: Optional[LLMBasicInfo] = None


    education: List[LLMEducation] = Field(
        default_factory=list
    )


    work_experience: List[LLMWorkExperience] = Field(
        default_factory=list
    )


    projects: List[LLMProject] = Field(
        default_factory=list
    )


    skills: List[str] = Field(
        default_factory=list
    )


    languages: List[str] = Field(
        default_factory=list
    )


    achievements: List[str] = Field(
        default_factory=list
    )


    certifications: List[str] = Field(
        default_factory=list
    )


    candidate_evidence: List[LLMCandidateEvidence] = Field(
        default_factory=list
    )

# 处理批量上传
class ResumeParseItemResult(BaseModel):
    filename: str
    success: bool
    candidate: Optional[Candidate] = None
    error: Optional[str] = None


class ResumeBatchParseResponse(BaseModel):
    total: int
    success_count: int
    failed_count: int
    results: List[ResumeParseItemResult] = Field(
        default_factory=list
    )


class ResumeTaskItem(BaseModel):
    item_id: str
    filename: str
    status: Literal["pending", "running", "success", "failed"] = "pending"
    candidate: Optional[Candidate] = None
    error: Optional[str] = None


class ResumeTaskResponse(BaseModel):
    task_id: str
    status: Literal[
        "pending", "running", "completed", "completed_with_errors", "failed"
    ] = "pending"
    total: int
    success_count: int = 0
    failed_count: int = 0
    items: List[ResumeTaskItem] = Field(default_factory=list)
    # 单项错误放在 item.error；这里仅说明批次 runner 自身的失败。
    error: Optional[str] = None
