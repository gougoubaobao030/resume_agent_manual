from schemas.resume import Candidate
from services.talent_service import discover_talent

# 放了现成测试Candidate版
# 且是压缩省token版哈哈哈哈
candidate = Candidate.model_validate(
    {
        "id": "candidate_966ab016",

        "basic_info": {
            "name": "勾勾",
            "email": "gougoubaobao030@gmail.com",
            "phone": "+86-139-5824-8237",
        },

        "education": [
            {
                "school": "宁波大学",
                "degree": "学士学位",
                "major": "会计学",
                "start_date": "2010/09",
                "end_date": "2014/06",
            },
            {
                "school": "日本留学经历",
                "degree": None,
                "major": "游戏开发相关学习",
                "start_date": "2024/09",
                "end_date": "2025/10",
            },
        ],

        "work_experience": [
            {
                "company": "个人开发工作室",
                "position": "软件开发",
                "start_date": "2022",
                "end_date": "2023",
                "description": (
                    "使用C#/Winform/.Net/C++/Qt开发人员管理系统，"
                    "实现登录、CRUD、权限管理、Socket通信、ORM和数据库设计。"
                ),
            },
            {
                "company": "会计/商务相关工作",
                "position": None,
                "start_date": "2014",
                "end_date": "2021",
                "description": "积累客户沟通、业务理解和多角度分析问题经验。",
            },
        ],

        "projects": [
            {
                "name": "AI智能简历初筛与潜力发现Agent",
                "description": (
                    "面向招聘场景开发AI简历筛选系统，"
                    "支持JD结构化、简历结构化、岗位匹配、"
                    "证据不足识别及人工复核。"
                ),
                "technologies": [
                    "Python",
                    "FastAPI",
                    "Pydantic",
                    "DeepSeek API",
                    "Vue3",
                    "LLM",
                ],
                "achievements": [
                    "设计并实现JD与简历结构化解析",
                    "使用Pydantic约束LLM结构化输出",
                    "实现10-30份简历批量解析，单份失败不影响整体",
                    "设计must_have、candidate_evidence、missing_information等结构",
                    "设计岗位匹配、潜力发现和人工复核流程",
                    "完成FastAPI与Vue3前后端联调",
                ],
            },
            {
                "name": "Unity3D中型RPG",
                "description": "个人从0到1独立开发多模块Unity3D RPG Demo。",
                "technologies": [
                    "Unity3D",
                    "C#",
                    "UGUI",
                    "NavMesh",
                    "对象池",
                    "状态机",
                ],
                "achievements": [
                    "实现技能、敌人AI、主角状态机等核心系统",
                    "实现商店、背包、任务、对话等业务模块",
                    "使用对象池和OverlapSphereNonAlloc进行性能优化",
                    "开发DevToolBox模块化调试工具",
                ],
            },
        ],

        "skills": [
            "Python/FastAPI/Pydantic",
            "LLM应用开发与Structured Output",
            "Prompt Engineering",
            "Vue3",
            "C#/Unity3D",
            "C++",
            "Git/GitHub",
            "数据结构与算法",
        ],

        "languages": [
            "英语",
            "日语",
        ],

        "achievements": [
            "宁波大学阳明班（特优班）特别荣誉",
        ],

        "certifications": [
            "日语N1证书(2017/12)",
            "商务日语结业证书(2025/06)",
            "英语四级(2012)",
        ],

        "candidate_evidence": [
            {
                "category": "AI应用开发",
                "title": "独立开发AI招聘应用",
                "description": "从需求、Schema、Prompt、后端API到前端展示进行开发。",
                "evidence": [
                    "使用Python/FastAPI开发后端",
                    "使用Pydantic设计结构化Schema",
                    "接入DeepSeek API",
                    "完成JD和简历结构化解析",
                    "完成批量简历处理",
                ],
            },
            {
                "category": "AI可靠性设计",
                "title": "设计LLM结果约束与证据机制",
                "description": "通过Schema和证据字段提升结果可解释性与可复核性。",
                "evidence": [
                    "设计must_have字段",
                    "设计candidate_evidence字段",
                    "设计need_raw_evidence机制",
                    "设计missing_information字段",
                ],
            },
            {
                "category": "独立开发",
                "title": "独立完成Unity3D中型项目",
                "description": "个人从0到1开发包含多个系统模块的Unity项目。",
                "evidence": [
                    "实现技能和AI系统",
                    "实现状态机和对象池",
                    "实现多个UGUI业务模块",
                    "开发调试工具框架",
                ],
            },
            {
                "category": "持续学习",
                "title": "跨技术栈持续学习与实践",
                "description": "从会计商务领域转向软件开发，再进入AI应用开发。",
                "evidence": [
                    "自学C#/Unity",
                    "学习并实践C++",
                    "学习Python/FastAPI",
                    "进行LLM应用开发",
                    "LeetCode通过262题",
                ],
            },
            {
                "category": "跨文化与语言",
                "title": "日本留学及日语能力",
                "description": "具有日本留学经历及日语能力。",
                "evidence": [
                    "日本留学",
                    "日语N1",
                    "商务日语结业证书",
                ],
            },
        ],

        "custom_attributes": {
            "career_direction": "AI应用工程师",
            "current_focus": [
                "LLM应用开发",
                "AI Agent",
                "招聘AI",
            ],
        },

        "raw_text": None,

        "extraction_metadata": {
            "source_file": "manual_scoring_test_candidate.json",
            "parser": "manual_test_data",
            "model": None,
            "confidence": None,
        },
    }
)

result = discover_talent(
    candidate=candidate,
    mode="specified",
    desired_traits=[
        "认真",
        "负责",
        "细致",
    ],
)

print(
    result.model_dump_json(
        indent=2,
    )
)