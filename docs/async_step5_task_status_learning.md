# 1. 本阶段解决了什么问题

前四步已经让批量解析能够并发运行，并用 Semaphore 把每批真正解析的数量限制为 3。但旧接口仍然 `await` 整个批次：外部只能看到“请求还没返回”，不知道 A 已成功、B 正在解析、C 还在排队。

第五步把“等待解析完成”和“查询处理状态”分开。后端先保存一份批次状态，安排后台 runner，返回 task_id。外部使用 GET 查询每个上传项的状态。

本次只实现单进程、内存状态的教学 MVP，没有修改 Vue、评分接口或 Promise.all，没有加入轮询、SSE、WebSocket、持久化或任务框架。

重新检查时确认：to_thread、gather、Semaphore(3)、单文件 try/except 都已存在。唯一不一致的是旧 Mock 测试还断言串行顺序，本次将其更新为当前并发行为的断言。没有删除之前保留的注释版代码，也没有重构无关代码。

# 2. 改造前调用链

旧接口仍然保留，调用链也仍然成立：

```text
POST /api/resume/parse-batch
  → parse_resume_batch_api：校验并保存临时 PDF
  → await parse_resume_batch(temp_files)
      → asyncio.gather(*tasks)
          → _parse_resume_item
              → async with Semaphore(3)
              → await parse_resume_pdf
                  → Mock：await asyncio.sleep(2～3秒)
                  → 真实：await asyncio.to_thread(_parse_resume_pdf_real, ...)
  → 所有解析完成，返回 ResumeBatchParseResponse
  → 接口 finally 关闭上传文件、删除临时 PDF
```

HTTP 连接必须等待整个批次结束。旧响应中的 success 是最终结果，不是可查询的运行中状态。

# 3. 改造后调用链

```text
POST /api/resume/tasks
  → create_resume_task_api
      → 基础校验（1～30份、文件名、PDF后缀）
      → 保存全部临时 PDF
      → create_resume_task(temp_files)
          → 建立 ResumeTaskResponse 和 ResumeTaskItem（pending）
          → 保存到 task_store
          → asyncio.create_task(run_resume_task(...))
          → 返回 pending 状态的独立快照
      → 返回 HTTP 202，包含 task_id
      → finally 关闭 UploadFile，但不删除 runner 正在使用的 PDF

事件循环后台调度：
run_resume_task
  → 批次 running
  → await parse_resume_batch(files, task_items=task.items)
      → asyncio.gather(*tasks)
          → _parse_resume_item（持有对应 ResumeTaskItem）
              → 等待 Semaphore：单项仍是 pending
              → 获得名额：单项 running
              → await parse_resume_pdf
              → 单项 success / failed
  → 批次 completed / completed_with_errors
  → finally 统一尝试删除全部临时 PDF

GET /api/resume/tasks/{task_id}
  → get_resume_task_api
  → get_resume_task：读取 store，复制快照，计算当前计数
  → 返回 ResumeTaskResponse；不存在时 HTTP 404
```

“较快返回”不是不需要上传时间：POST 仍需接收文件、校验、写盘、关闭上传对象。它只是不再等待 2～3 秒一份的解析工作。新接口保留当前同步写盘方式，未额外引入上传 I/O 重构。

# 4. 本次修改的文件

项目根目录：`D:/VSProject/Python/resume_agent_manual`。

| 文件路径（相对根目录） | 修改内容 | 为什么修改 |
| --- | --- | --- |
| backend/services/resume_task_service.py（新增） | 内存 store、创建、查询、后台 runner、清理 | 将任务生命周期与简历解析算法分开 |
| backend/schemas/resume.py | 新增 ResumeTaskItem、ResumeTaskResponse | 明确 API 字段和允许的状态；继续复用 Candidate |
| backend/services/resume_service.py | worker 可选接收状态项，在 Semaphore 内更新状态；批量函数可选接收 task_items | 让旧接口和新任务模式复用同一套 gather/Semaphore/worker |
| backend/api/resume.py | 新增 POST /tasks 和 GET /tasks/{task_id} | 将 HTTP 上传/校验与后台处理连接起来；保留旧接口 |
| backend/test_resume_task_service.py（新增） | 8 项 unittest 异步测试 | 验证状态、隔离、并发、API 和文件清理 |
| backend/test_resume_service_mock.py | 将过时的串行断言改成并发断言 | 测试必须符合当前已经完成的第三步 |
| docs/async_step5_task_status_learning.md（新增） | 本教学文档 | 以后能够沿真实调用链重新理解代码 |

新增任务服务为什么不直接写在 API 里：API 已负责上传和 HTTP 错误，继续塞入 store、runner 和状态汇总会让资源所有权不清楚，也难以脱离 HTTP 测试。

为什么不直接写在 parse_resume_batch 里：旧接口只需要等待最终结果，不需要建立可查询的业务任务，也不应该因此启动后台工作。

如果删掉任务服务层：功能仍可以写出来，但这两种生命周期会混进 API 或解析函数；读代码时更难分辨谁持有临时 PDF、谁保存状态、谁启动后台任务。这里只新增一个文件和三个函数，没有类体系、通用 TaskManager 或事件回调链。

两个新 schema 分别描述上传项和批次。若不用 schema，只写嵌套 dict，也能实现，但状态拼写和 API 文档容易不一致。Literal 只允许本阶段约定的几个状态，不是新的复杂状态框架。

# 5. 每个核心函数讲解

## task_store 与 _background_tasks

位于 `backend/services/resume_task_service.py`：

```python
task_store: dict[str, ResumeTaskResponse] = {}
_background_tasks: dict[str, asyncio.Task] = {}
```

task_store 保存业务数据，供 GET 查询，批次结束后仍保留。_background_tasks 保存 Python 调度对象的强引用，runner 结束后移除。二者用途完全不同。

## create_resume_task(files)

- 输入：`[(filename, temp_path), ...]`，必须在正在运行的事件循环中调用。
- 输出：ResumeTaskResponse 的独立快照。
- 职责：建立唯一批次、建立每项 pending 状态、保存 store、安排 runner。
- 调用者：create_resume_task_api、测试。
- 调用：run_resume_task（交给 create_task 调度）。
- 为什么存在：创建状态和安排后台工作需要作为一个清楚的步骤，但不需要等待解析完成。

## run_resume_task(task_id, files)

- 输入：已存在的 task_id 和 runner 拥有的临时文件列表。
- 输出：None；通过修改 store 保存处理结果。
- 职责：批次 running、等待原有批量解析、设置批次终态、处理批次异常、最终清理文件。
- 调用者：事件循环调度的 asyncio.Task。
- 调用：parse_resume_batch、os.path.exists、os.remove。
- 为什么存在：接口返回以后，仍需要一个拥有完整 try/except/finally 生命周期的执行入口。

## get_resume_task(task_id)

- 输入：task_id。
- 输出：ResumeTaskResponse 快照或 None。
- 职责：不改变解析流程，只读取状态，按单项当前状态计算成功/失败数。
- 调用者：get_resume_task_api、测试。
- 为什么复制：返回方不能意外修改 store，已经返回的创建响应也不会随后自动变化。

## _parse_resume_item(filename, pdf_path, semaphore, task_item=None)

- 输入：文件名、路径、共享 Semaphore、可选 ResumeTaskItem。
- 输出：原有 ResumeParseItemResult。
- 职责：一个上传项的并发名额、状态变化和异常隔离。
- 调用者：parse_resume_batch 通过 gather 调度。
- 调用：parse_resume_pdf。
- 为什么可选：旧接口不传 task_item，仍然得到原来的结果；新模式传入对应状态对象。

## parse_resume_batch(files, *, task_items=None)

- 输入：文件列表，以及可选且按相同上传顺序排列的状态列表。
- 输出：原有 ResumeBatchParseResponse。
- 职责：创建每批 Semaphore(3)、构造 worker、gather、汇总结果。
- 调用者：旧 parse_resume_batch_api、新 run_resume_task。
- 调用：_parse_resume_item、asyncio.gather。
- 数量检查避免文件与状态项错配；映射使用序号而不是文件名。

## create_resume_task_api(files)

- 输入：multipart 的 files 字段。
- 输出：HTTP 202 + ResumeTaskResponse。
- 职责：HTTP 校验、临时文件写盘、交接文件所有权、关闭 UploadFile。
- 调用：create_resume_task。

## get_resume_task_api(task_id)

- 输入：URL 中的 task_id。
- 输出：HTTP 200 + ResumeTaskResponse，或 HTTP 404。
- 职责：把服务层的查询结果转换成 HTTP 行为。
- 调用：get_resume_task。
- 使用 async def：当前 store 的更新也在同一事件循环中，查询没有 await 间隙，也不额外放入线程池。

# 6. 核心代码逐段讲解

## 保存状态后再调度

```python
task_store[task_id] = task
background_task = asyncio.create_task(run_resume_task(task_id, files))
_background_tasks[task_id] = background_task
background_task.add_done_callback(lambda _: _background_tasks.pop(task_id, None))
return task.model_copy(deep=True)
```

runner 启动时就能读到 store。create_task 返回的是 asyncio.Task，不是解析结果。done_callback 只做运行对象引用的回收，不删除业务状态。

本项目选择 create_task 而不是 FastAPI BackgroundTasks：这里学习的就是显式创建后台协程；代码直接展示“调度对象”与“业务状态”的区别，且复用 asyncio 已有知识。BackgroundTasks 也是合理的简单方案，但它在响应发送后执行回调，本次不需要再引入另一套启动方式。

create_task 安排 runner 在事件循环后续调度机会开始执行，不保证恰好在客户端收到响应之后。它可能在接口 finally 的异步关闭期间开始，也可能在响应以后开始。创建返回值是 pending 快照，所以即使 runner 很快更新 store，POST 返回体仍是创建时快照；后续 GET 才读最新状态。

## 名额和状态

```python
async with semaphore:
    if task_item is not None:
        task_item.status = "running"
    try:
        candidate = await parse_resume_pdf(...)
```

还没获得名额的协程不在解析，所以保持 pending。若创建协程时就标 running，7 份文件会全部显示 running，掩盖“只有 3 份真的工作、4 份排队”的事实。

## 成功和失败

```python
task_item.candidate = candidate
task_item.status = "success"
```

成功时先保存 candidate，再设终态，查询就不会看到 success 却没有结果。

```python
except Exception as exc:
    logger.exception("[Resume Item] FAILED %s", filename)
    if task_item is not None:
        task_item.error = str(exc)
        task_item.status = "failed"
    return ResumeParseItemResult(filename=filename, success=False, error=str(exc))
```

worker 把异常转换成结果，因此其他 worker 继续运行。没有增加异常类、重试或恢复机制。

## runner 的清理

```python
try:
    result = await parse_resume_batch(files, task_items=task.items)
    task.status = "completed_with_errors" if result.failed_count else "completed"
except Exception as exc:
    task.status = "failed"
    task.error = str(exc)
finally:
    for _, temp_path in files:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            logger.exception("[Resume Task] 清理临时文件失败 %s", temp_path)
```

无论正常完成还是批次异常，都会尝试清理全部文件。操作系统拒绝删除时记录日志，继续尝试其他文件，不假装一定能删掉；本阶段没有清理重试机制。

# 7. 状态机

单项正常路径：

```text
pending（create_resume_task）
   ↓ 获得 Semaphore 名额
running（_parse_resume_item）
   ├─ 解析返回 Candidate → success（同一 worker）
   └─ 解析抛 Exception → failed（同一 worker）
```

批次路径：

```text
pending（create_resume_task）
   ↓ runner 开始
running（run_resume_task）
   ├─ 全部成功 → completed
   ├─ 至少一项业务失败 → completed_with_errors
   └─ 批次编排本身异常 → failed
```

保留 pending 是为了表达刚创建与排队；保留批次 failed 是为了区分 runner 故障与已正常收集的单项失败。全部文件都业务失败时仍是 completed_with_errors，因为编排正常完成了。

批次级异常发生时，runner 将尚未到终态的 pending/running 项标 failed，并写明“批次执行失败”；已经 success/failed 的项不被覆盖。这是异常路径，不要求每项都先进入 running。

# 8. task_id / item_id / candidate_id 区别

| ID | 生成/来源 | 表达什么 |
| --- | --- | --- |
| task_id | `resume_task_` + `uuid4().hex` | 每次上传创建的独立批次 |
| item_id | `task_id + "_item_" + (上传序号+1)` | 此批次中的一次上传/处理单元 |
| candidate_id | 现有 Candidate.id | 解析得到的候选人业务对象，用于评分等业务 |

filename 是展示信息，不是唯一 ID：两个上传项都可能叫 resume.pdf，但仍拥有不同 item_id。失败项还没有 candidate，因此不能用 candidate_id 追踪上传任务。

当前 Mock 按文件名生成 candidate_id，所以同名文件可能得到相同 candidate_id。这不影响 item 状态隔离；未来 Vue 接入时仍需分别处理上传项 ID 和候选人业务 ID。本次不改 Mock 候选人生成逻辑。

# 9. await vs create_task

```python
result = await parse_resume_batch(files)
return result
```

调用者必须等解析结束，才继续执行 return。await 等待时让出事件循环，所以其他请求仍可运行，但当前请求没有完成。

```python
background_task = asyncio.create_task(run_resume_task(task_id, files))
return task.model_copy(deep=True)
```

调用者只安排 runner，不等待其结束，继续返回。runner 自己在内部 await parse_resume_batch，因此 runner 仍会正确等待整个批次，最后清理文件。

关系是：

```text
调用 async 函数 → coroutine 对象（待执行工作）
create_task(coroutine) → asyncio.Task（事件循环调度的工作）
event loop → 在 await 等待点之间调度这些工作
task_store 中的 ResumeTaskResponse → 业务状态数据，不负责调度
```

接口 return 只是结束请求处理，不会关闭整个 FastAPI 事件循环。runner Task 有自己的生命周期和引用，事件循环继续运行它。它不是新进程，也不因 create_task 自动新建线程；真实同步解析进入线程，是已有 to_thread 的作用。

本次没有直接 create_task(parse_resume_batch(...))，因为批次外面还需要状态汇总和 finally；所以使用清晰的 run_resume_task 包住现有批量函数。

# 10. gather / Semaphore / background task 三者的职责区别

| 概念 | 本项目位置 | 解决的问题 |
| --- | --- | --- |
| create_task 后台 runner | create_resume_task | 请求不必等待整个批次；把请求生命周期与解析生命周期分开 |
| gather | parse_resume_batch | 同时调度多个 worker，并等待它们全部返回；返回顺序对应上传顺序 |
| Semaphore(3) | parse_resume_batch / _parse_resume_item | 每批最多 3 个 worker 进入真正解析区域 |
| to_thread | parse_resume_pdf 真实分支 | 同步 PDF/LLM 工作不占住 event loop |

它们不是四种同义的“并发”。后台启动解决等待关系，gather 解决集合调度和聚合，Semaphore 解决资源数量，to_thread 解决同步阻塞兼容。

# 11. 失败隔离

单文件业务失败：例如 PDF 内容无法解析、LLM 请求失败。异常在 _parse_resume_item 内被捕获，生成 failed 状态和失败结果。gather 收到的是一个正常返回的 ResumeParseItemResult，其他项不会因此中断。

测试验证 A/B/C 状态为 success/failed/success，计数 2/1，批次 completed_with_errors，批次 error 为 None。

批次基础设施级失败：例如状态数量与文件不一致，或批量编排入口发生意外异常。runner 外层 except 设置批次 failed 和 task.error。测试用 RuntimeError 注入这个路径，不增加复杂异常类体系。

本阶段不处理进程强制退出、任务取消、线程终止或恢复。正常 worker 中的 Exception 已被隔离；不要把本实现理解成能从任意系统故障恢复。

# 12. 临时文件生命周期

旧接口的 finally 位于“await 全批次”以后，因此删除 PDF 是安全的。

新接口 return 不等于解析完成：如果沿用旧接口的无条件删除，runner 后面读 PDF 就会找不到文件。Mock 不实际读 PDF，可能掩盖此错误，所以测试还专门检查解析等待期间路径确实存在。

新接口使用一个简单的 task_created 标记：

- 创建前或复制中途失败：接口负责删除已建临时文件。
- 成功安排 runner：接口只关闭 UploadFile，临时 PDF 交给 runner。
- runner 正常完成或异常结束：其 finally 尝试统一删除。

关闭 UploadFile 只是关闭原始上传对象；独立保存的临时 PDF 不会因此消失。写盘时先记录路径，再 copyfileobj，确保部分复制失败也能找到并删除文件。

# 13. 当前方案的局限

- task_store 是 Python dict，状态仅存在当前进程内。
- Uvicorn 重启、reload 或进程退出后，状态消失；执行中的任务也不会恢复。
- 多 worker 不共享 store；本教学方案应使用单 worker。
- 没有数据库/Redis 持久化，不适合生产分布式任务部署。
- 已完成状态暂不自动淘汰，长时间运行会占内存。
- Semaphore 是每批 3 个，不是所有批次合计 3 个；旧接口也各有自己的 Semaphore。
- POST 接收和同步写盘仍花时间，大文件写盘可能短暂阻塞事件循环，本次没有扩展上传重构。
- 操作系统拒绝删除文件时仅记录日志，不重试；进程硬退出也不能保证 finally 执行。
- task_store 的同步访问基于当前同一事件循环中的状态更新；不是跨线程/进程同步方案。
- 未改变现有共享 LLM 客户端或同名 Mock candidate_id 行为。
- 没有取消、超时恢复、自动重试、历史任务中心、鉴权和生产级资源配额。

这些限制在教学 MVP 中是明确取舍：现在先理解请求、协程、状态和文件生命周期，不自动引入 Redis 或任务框架。

# 14. 如何手动验证

1. 在项目根目录 .env 中确认 `RESUME_USE_MOCK=true`。LLM 客户端模块会加载这个文件；修改后重新启动后端。
2. 在 backend 目录启动：`uvicorn app.main:app --reload --port 18000`。不要加多个 worker，观察期间不要修改文件触发 reload。
3. 打开 `http://127.0.0.1:18000/docs`。
4. 展开 POST /api/resume/tasks，选择 Try it out，通过 files 上传 5～7 份 PDF，执行。
5. 应得到 HTTP 202、task_id、total、items，POST 响应中是 pending 快照。记录 task_id。
6. 展开 GET /api/resume/tasks/{task_id}，粘贴 task_id，执行。
7. 如果查询够快，7 份文件应有 3 个 running、4 个 pending；稍后可同时看到 success、running、pending。手动重复 Execute 即可，本次没有前端轮询。
8. 最终应为 completed，全部单项 success，success_count=total、failed_count=0，每项有 candidate。
9. 查询不存在的 ID 应得到 404；上传 .txt 应得到 400；缺少 multipart 的必填 files 字段由 FastAPI 返回 422。
10. 调用旧 POST /api/resume/parse-batch，仍等待全部结束并返回原来的 results/success_count/failed_count。
11. Mock 默认不会业务失败。A/B/C 失败隔离、runner 失败、临时路径清理由自动测试注入，不需要给业务接口加“强制失败参数”。

状态变化很快：手动 GET 不保证能抓到 pending；它可能已经 running 或 completed，这并不表示状态缺失。事件阻塞测试能确定性验证中间状态。

在 backend 目录执行测试：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
python -m unittest test_resume_service_mock test_resume_task_service test_scoring_service_mock
```

用 `python test_resume_task_service.py` 可以同时看到 INFO 级 Mock 日志。使用 unittest、unittest.mock 和现有 OpenAI 依赖环境中的 httpx，没有增加测试框架或依赖文件。

# 15. 日志应该长什么样

本次真实 2～3 秒 Resume Mock 的一次实测（省略完整 task_id）：

```text
[Resume Task] START ... total=5
[Resume Mock] START A.pdf
[Resume Mock] START B.pdf
[Resume Mock] START C.pdf
[Resume Mock] DONE  C.pdf elapsed=2.41s
[Resume Mock] START D.pdf
[Resume Mock] DONE  B.pdf elapsed=2.64s
[Resume Mock] START E.pdf
[Resume Mock] DONE  A.pdf elapsed=2.69s
[Resume Mock] DONE  D.pdf elapsed=2.21s
[Resume Mock] DONE  E.pdf elapsed=2.97s
[Resume Task] DONE ... status=completed
```

先启动三项，释放一个名额再开始 D/E；DONE 顺序随机，但 API 的 items 仍按上传顺序排列。

GET 的一个可能快照：

```json
{
  "task_id": "resume_task_...",
  "status": "running",
  "total": 5,
  "success_count": 1,
  "failed_count": 0,
  "items": [
    {"item_id": "..._item_1", "filename": "A.pdf", "status": "running", "candidate": null, "error": null},
    {"item_id": "..._item_2", "filename": "B.pdf", "status": "running", "candidate": null, "error": null},
    {"item_id": "..._item_3", "filename": "C.pdf", "status": "success", "candidate": {"id": "candidate_mock_..."}, "error": null},
    {"item_id": "..._item_4", "filename": "D.pdf", "status": "running", "candidate": null, "error": null},
    {"item_id": "..._item_5", "filename": "E.pdf", "status": "pending", "candidate": null, "error": null}
  ],
  "error": null
}
```

candidate 在此示例中只保留 id 以便阅读，实际仍返回完整 Candidate schema。

失败注入测试出现 ERROR 和异常栈是预期日志，不代表测试失败。断言验证异常被正确隔离或汇总。

# 16. 我这一阶段真正应该学会什么

1. 协程对象、asyncio.Task 和业务状态对象是三种不同对象。
2. await 让出事件循环，但当前调用者仍等待；create_task 让调用者不必等待整个工作。
3. HTTP 请求结束不等于后台协程结束，进程结束也不等于任务持久化。
4. gather、Semaphore、create_task、to_thread 各自解决不同问题。
5. pending 和 running 应描述真实排队/执行事实，不只是界面文字。
6. 一份上传项有自己的稳定 ID，文件名和候选人 ID不能代替它。
7. worker 内捕获业务异常，使失败成为可聚合的结果。
8. 临时文件必须跟随真正使用它的工作生命周期清理。
9. 状态查询返回独立快照，运行中计数从单项状态计算。
10. 简单内存实现有清楚边界，但足以独立验证当前学习阶段。

本次测试覆盖：创建即时返回、pending/running、同名 item 隔离、真实 Mock 成功、A/B/C 失败隔离、实时状态/最终计数、最大并发 3、runner 异常、正常/异常文件清理、部分上传失败清理、旧 API 和新 API 校验/404。

最终回归：`test_resume_service_mock` 3 项 + `test_resume_task_service` 8 项 + `test_scoring_service_mock` 3 项，共 14 项通过。另一次直接执行新测试文件的 8 项也通过，并记录了以上真实 Mock 日志。没有运行会请求真实 LLM 的脚本/集成测试，以免产生不必要的调用和费用。
