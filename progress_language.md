## update 2026年9月23日
- 设计总目标
- 多语言设计不限定于中日英三语，而采用可扩展的多语言架构。系统将输入原文语言、内部结构化数据和 HR 显示语言解耦：简历及 JD 始终保留原文，模型直接理解原始语言，并基于原始资料进行岗位匹配和人才能力分析。分析结果按 HR 选择的语言输出，以降低跨语言阅读成本，同时保留原文证据供人工复核。

当前产品优先支持中文、日文和英文，后续可通过增加语言配置及相应测试，逐步扩展支持范围。

具体：
- 前端界面国际化（i18n）
- 跨语言理解与翻译展示
- 采用轻量策略模式，目前用大模型翻译，之后会考虑接入其他翻译供应商
- JD各语言独立，JD 独立不设置多语言联动，且多语言联动这也不太符合实际（比如日文写外国人需要N1，然后你中文翻译外国人需要N1那这个外国人到底是哪国人？）、评分以 job_id 为准，就按给的job_id的jd评、原文作为事实依据、翻译作为可选展示辅助。
- 语言切换与评分解耦

cd frontend
npm install vue-i18n@11
Composition API

- 完成核心手动三语注册
- codex完成三语json文件
- 暂时不npm run build 正式发布再用

- 验收发现问题，标题导航栏layout是变化了，主要内容views没有
- 当然也是因为没有下指令

- 考虑发现语言不一样加个提示进去
- 交的是混合双语怎么办, 等下再考虑双语，双他妹（主要就是提示词控制）
- 语言源数据我觉得很重要这个

## update 2026年9月27日
- 重新确认json 3大类 5种方式约束
schema注入，重要格式约束写在提示词最后，api确定，pydantic校验，后端校验，扔回大模型自纠错
- 确认api已经指定json mode
- 将简历结构化模块和jd解析模块升级为schema注入
- 考虑升级风险暂时没有struct outputs

## update 2026年9月28日
同时确认结构化简历信息和原文双保险
整个确认证据链之于评分业务serviece的数据流：
evaluate_job_match()
        ↓
evaluate_job_match_with_llm()
        ↓
真实 LLM 返回 LLMJobMatchResult
        ↓
_build_job_match_result()
        ↓
_build_requirement_results()
        ↓
每个 requirement
        ↓
_build_match_evidence()
        ↓
⭐ verify_candidate_evidence()
        ↓
Candidate / raw_text 精确核验
        ↓
只留下 verified evidence
        ↓
必要时降低 confidence
        ↓
必要时 needs_raw_review = True
        ↓
最终 JobMatchResult、

-- 完成jd，简历，评分，能力分持久化
-- 实现全部增删改查