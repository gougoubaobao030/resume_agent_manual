# 1. 第6步解决了什么问题

第5步以后，FastAPI 已经会在后台解析，并在内存 task store 中保存每份简历的 `pending / running / success / failed`。但 Vue 原来仍调用旧的 `POST /api/resume/parse-batch`，这个请求会等整批结束后才返回，所以浏览器看不到后端已经拥有的中间状态。

第6步让上传页改用任务接口：先创建任务并取得 `task_id`，然后每 800ms 查询一次。每次查询结果写入 Vue 响应式状态，页面便能增量显示状态。某项第一次成功时，Candidate 立即进入当前 session，并立即开始原有岗位评分，不等其他简历。

本次没有修改第5步后端，也没有引入前端库、SSE、WebSocket 或新评分系统。

# 2. 改造前数据流

真实旧代码的数据流是：

```text
ResumeUploadView.handleParse
  → api.parseResumeBatch(files)
  → POST /api/resume/parse-batch
  → await 后端整个 gather 完成
  → 一次性收到 ResumeBatchParseResponse
  → setCandidates(allCandidates) 覆盖候选人列表
  → candidates.map(...) 创建所有评分 Promise
  → await Promise.all(scoringTasks)
```

后端虽然并发解析，但前端只有“整个请求还在等待”与“整批结果已经返回”两种观察结果。

# 3. 改造后数据流

```text
ResumeUploadView.handleParse
  → createResumeTask(files)
  → POST /api/resume/tasks
  → 很快收到 task_id + pending 快照
  → pollResumeTask(task_id)
      → GET /api/resume/tasks/{task_id}
      → applyTaskSnapshot(task)
          → setResumeTask(task)：更新 batch/item 状态
          → 首次发现 success + candidate
              → addCandidate(candidate)
              → startCandidateScoring(candidate)
                  → setJobMatchLoading
                  → POST /api/scoring/job-match
                  → setJobMatchResult / setJobMatchError
      → 非终态：等待 800ms 后再 GET
      → 终态：finishTask 并退出循环
```

解析和评分现在会重叠。例如 A/B/C 先解析，A 成功后立刻评分，同时 D 获得解析名额。

# 4. 6A 调用链

```text
frontend/src/views/ResumeUploadView.vue
  handleParse()
    → frontend/src/services/api.js
      createResumeTask(files)
        → POST /api/resume/tasks
    → applyTaskSnapshot(initialTask)
    → pollResumeTask(taskId)
      → frontend/src/services/api.js
        getResumeTask(taskId)
          → GET /api/resume/tasks/{task_id}
      → frontend/src/state/session.js
        setResumeTask(task)
          → session.resumeTaskId
          → session.resumeTaskStatus
          → session.resumeTaskItems
      → ResumeUploadView 的 computed 重新计算
          → taskCounts
          → 每行 pending/running/success/failed
      → addCandidate(candidate)
          → session.candidates.push(...)
          → CandidateListView 读取同一个 session.candidates
```

`CandidateListView.vue` 无需修改：它本来就直接读取响应式的 `session.candidates`。数据由一次性替换改成逐个 push 后，原页面仍然正常工作。

# 5. 6B 调用链

```text
GET 快照中的 item 首次成为 success
  → applyTaskSnapshot
  → addCandidate(item.candidate) 返回 true
  → startCandidateScoring(candidate)
      → 检查 candidate.id / job id / 已有评分状态
      → setJobMatchLoading(candidate.id)
      → scoreJobMatch(activeJobId, candidate)
          → POST /api/scoring/job-match
      ├─ 成功 → setJobMatchResult(candidate.id, result)
      └─ 失败 → setJobMatchError(candidate.id, friendlyMessage)
```

每次评分是独立、带自身 try/catch 的异步函数。某人评分失败，只改变自己的状态，不阻断轮询或其他评分请求。

# 6. 本次修改文件

| 文件 | 修改内容 | 原因 |
| --- | --- | --- |
| `frontend/src/services/api.js` | 新增 `createResumeTask`、`getResumeTask`；保留 `parseResumeBatch` | Vue 需要调用第5步任务接口，旧接口仍可保留 |
| `frontend/src/state/session.js` | 增加最小 resume task 状态、`clearResumeTask`、`setResumeTask`、`addCandidate` | 让不同页面共享当前任务快照和增量候选人 |
| `frontend/src/views/ResumeUploadView.vue` | 切换创建任务/轮询、状态统计、逐项 UI、增量候选人和即时评分 | 本阶段主要编排入口 |
| `frontend/src/styles/main.css` | 增加任务统计和文件状态行样式 | 沿用现有 panel/status-badge 风格，不引入 UI 库 |
| `docs/async_step6_incremental_display_learning.md` | 本文档 | 记录真实数据流与验证方式 |

没有修改后端文件。`CandidateListView`、候选人详情页和分析页也没有修改；浏览器回归确认它们继续读取原有 session 数据。

# 7. api.js 新函数

## createResumeTask(files)

```javascript
export function createResumeTask(files) {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  return request('/api/resume/tasks', { method: 'POST', body: formData })
}
```

- 输入：浏览器 File 数组。
- 请求：`POST /api/resume/tasks`。
- 返回：后端 `ResumeTaskResponse`，包括 task_id、批次状态和 items。
- 为什么 FormData：FastAPI 接收 multipart 的多个 `files` 字段。

## getResumeTask(taskId)

```javascript
export function getResumeTask(taskId) {
  return request(`/api/resume/tasks/${encodeURIComponent(taskId)}`)
}
```

- 请求：`GET /api/resume/tasks/{task_id}`。
- `encodeURIComponent` 防止路径参数中出现特殊字符。
- 继续复用现有 `request()` 的网络错误和 HTTP 错误处理。

# 8. 轮询核心代码

核心结构是：

```javascript
while (!pollingStopped) {
  const task = await getResumeTask(taskId)
  if (pollingStopped) return
  applyTaskSnapshot(task)

  if (terminalTaskStatuses.has(task.status)) {
    finishTask(task)
    return
  }

  await sleep(POLL_INTERVAL_MS)
}
```

每一次 GET 完整返回以后，才处理结果、等待 800ms 并进入下一次循环。因此不会出现 `setInterval` 可能造成的情况：上一次网络请求尚未结束，下一次请求又开始。

状态查询失败时显示“后台任务可能仍在运行”，并停止本页面的轮询。没有把一次查询错误错误地写成后端批次 failed，也没有增加复杂重试/退避。

# 9. Vue 响应式更新

Vue 的 `reactive` 可以理解为“被页面观察的数据对象”。

```text
GET 返回普通 JSON
  → setResumeTask(task)
  → 修改 reactive session 的三个字段
  → 依赖这些字段的 computed 重新计算
  → template 自动重新显示新数字和新状态
```

关键状态很简单：

```javascript
resumeTaskId: null,
resumeTaskStatus: null,
resumeTaskItems: [],
```

`taskItems` 和 `taskCounts` 是 computed：不自己保存第二份计数，而是根据当前 items 计算完成、成功、失败、运行和等待数量。

# 10. item_id / candidate.id

- `item_id`：这次上传批次中的处理单元，由后端第5步生成。任务列表的 `v-for :key` 和快照对齐都使用它。同名 PDF 也不会冲突。
- `candidate.id`：解析成功以后产生的业务候选人 ID，用于 candidates、岗位评分结果、详情路由和分析页。

pending/failed 项可能根本没有 candidate，所以不能用 candidate.id 代替 item_id。filename 可能重复，也不能作为任务 key。

# 11. 防重复 candidate

每次轮询都会再次返回已经 success 的项。`addCandidate` 在 push 前检查已有 ID：

```javascript
if (!candidate?.id || session.candidates.some((item) => item.id === candidate.id)) {
  return false
}
session.candidates.push(structuredClone(candidate))
return true
```

返回值很重要：只有 `true` 表示这个 candidate 是第一次进入 session。没有新增 Set、Map 状态或专门的去重框架。

现有 Resume Mock 按 filename 生成 candidate.id，因此同名文件可能被视为同一候选人；item 状态仍分别展示。这是当前 Mock 的已知边界，不在第6步修改后端。

# 12. 防重复评分

使用两层简单保护：

1. `applyTaskSnapshot` 只有在 `addCandidate()` 返回 true 时启动评分。
2. `startCandidateScoring` 检查 `session.jobMatchStatuses[candidate.id]`；loading/success/error 任意一种都表示已经发起过。

```javascript
if (!candidate.id || !activeJobId || session.jobMatchStatuses[candidate.id]) return
setJobMatchLoading(candidate.id)
```

loading 必须在 `await scoreJobMatch` 之前设置。即使同一时刻又处理到相同 candidate，也会看到 loading 并退出。

# 13. 解析并发 vs 评分并发

解析并发：

```text
FastAPI 后台 runner
→ asyncio.gather 创建多个单文件 worker
→ asyncio.Semaphore(3)
→ 每批最多 3 份真正解析
```

评分并发：

```text
Vue 发现一个新 Candidate
→ 独立 POST /api/scoring/job-match
→ 多个 Candidate 可同时拥有独立 HTTP 请求
→ FastAPI 当前同步评分 endpoint 在线程池处理
```

解析的 Semaphore(3) 不限制评分请求。第6步没有建立评分队列或业务级评分上限。

# 14. 轮询什么时候停止

`ResumeUploadView.vue` 定义与后端 schema 完全一致的批次终态：

```javascript
const terminalTaskStatuses = new Set([
  'completed',
  'completed_with_errors',
  'failed',
])
```

`pollResumeTask()` 每次应用最新快照后检查这个 Set。终态调用 `finishTask()` 更新总提示，然后 return 退出 while。查询错误也会 return。

# 15. 页面卸载如何停止

```javascript
onUnmounted(() => {
  pollingStopped = true
})
```

如果正好有一个 GET 在途，不强行构建复杂 AbortController。它返回后，紧接着的 `if (pollingStopped) return` 会丢弃结果且不再发下一次请求。

实际浏览器验证：启动 5 份后立刻离开上传页，后端只收到创建后的第一次 GET；随后后台按 Semaphore(3) 完成，但没有新的 GET。

# 16. 当前限制

- 刷新页面不会恢复 task_id，也不会自动重连已有任务。
- 离开上传页会停止轮询；后端继续运行，但当前 session 不再接收后续候选人。已经加入的候选人在 CandidateList 可见。
- 后端 task store 仍是单进程内存 dict，重启丢失，多 worker 不共享。
- 没有 SSE、WebSocket、任务恢复或持久化。
- 状态查询失败就停止轮询，不做自动重试。
- 评分没有业务级并发上限，解析 Semaphore 不控制评分。
- 新批次开始会清空当前 candidates 和评分状态，符合当前“单次前端会话”流程。
- 评分可能在解析批次完成提示之后继续；每个文件行会独立显示岗位评分中/完成/失败。
- 页面卸载不取消后端解析，也不取消已经发出的评分请求。

# 17. 以后如果升级 SSE，会改变哪里

现在是 Vue 主动询问：

```text
Vue → 每800ms GET → FastAPI 返回完整当前快照
```

SSE 会变成后端主动推送：

```text
Vue 先 POST 创建任务
Vue 建立 GET 事件流
FastAPI 在状态变化时推送 item 事件
Vue 收到事件后更新同一份 session
```

主要替换的是 `pollResumeTask()` 和 GET 状态传输方式。`setResumeTask`、`addCandidate`、评分状态和 UI 映射仍可以复用。SSE 要处理连接关闭、重连、事件遗漏和代理缓冲，因此当前教学 MVP 不实现。

# 18. 本阶段真正需要理解的内容

1. 后端拥有状态，不代表前端会自动知道；两者需要 GET 轮询或推送通道。
2. `api.js` 只负责 HTTP，`session.js` 保存共享数据，View 负责页面流程和展示。
3. Vue reactive 数据变化后，computed 和 template 会自动刷新，无需手动重画页面。
4. 顺序轮询是“GET 完成 → 处理 → 等待 → 下一个 GET”，不会请求重叠。
5. item_id 跟踪上传任务，candidate.id 跟踪候选人业务，不能混用。
6. 轮询重复返回 success，因此 candidate 和评分都必须防重复。
7. 一个 candidate 的解析完成就可以启动下游评分，不需要人为等待整个 gather。
8. 解析并发和评分并发是两个独立机制。
9. 终态、查询错误和组件卸载都必须能退出轮询。
10. 当前限制是明确的 MVP 取舍；不需要为了增量展示立即引入复杂前端架构。

## 实际验证记录

- `npm run build`：Vite 构建通过。
- 第5步后端回归：指定 `D:/python/python.exe` 后 14 项测试通过。
- 浏览器通过真实本地 Vue + FastAPI + Resume/Scoring Mock 上传 5 份文件。
- 首次快照：0/5 完成，3 running，2 pending。
- 日志：A/B/C 先 START；A 完成后 D START，B 完成后 E START。
- A/B/C 的三次评分请求出现在 D/E 解析完成之前。
- 最终 5/5 success、每个候选人恰好一次评分请求；CandidateList 显示 5 人。
- 页面卸载测试：仅保留一次已在途 GET，后端继续完成，没有继续轮询。
- 候选人详情和完整评分分析页均能正常显示。
- 未通过 UI 强制制造评分失败；但 `startCandidateScoring` 的逐候选人 try/catch 与现有 error 状态保持独立，构建及原评分 Mock 回归通过。
