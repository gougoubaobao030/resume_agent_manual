import { reactive } from 'vue'

export const session = reactive({
  currentJob: null,
  candidates: [],
  jobMatches: {},
  jobMatchStatuses: {},
  jobMatchErrors: {},
  resumeTaskId: null,
  resumeTaskStatus: null,
  resumeTaskItems: [],
})

export function setCurrentJob(job) {
  const jobChanged = session.currentJob?.id && session.currentJob.id !== job.id
  session.currentJob = structuredClone(job)

  if (jobChanged) {
    session.jobMatches = {}
    session.jobMatchStatuses = {}
    session.jobMatchErrors = {}
  }
}

export function setCandidates(candidates) {
  session.candidates = structuredClone(candidates)
  session.jobMatches = {}
  session.jobMatchStatuses = {}
  session.jobMatchErrors = {}
}

export function clearResumeTask() {
  session.resumeTaskId = null
  session.resumeTaskStatus = null
  session.resumeTaskItems = []
}

export function setResumeTask(task) {
  session.resumeTaskId = task.task_id
  session.resumeTaskStatus = task.status
  // 每次轮询都用 item_id 对齐状态，不依赖可能重复的 filename。
  const previousItems = new Map(session.resumeTaskItems.map((item) => [item.item_id, item]))
  session.resumeTaskItems = (task.items ?? []).map((item) => ({
    ...previousItems.get(item.item_id),
    ...structuredClone(item),
  }))
}

export function addCandidate(candidate) {
  if (!candidate?.id || session.candidates.some((item) => item.id === candidate.id)) {
    return false
  }

  session.candidates.push(structuredClone(candidate))
  return true
}

export function setJobMatchLoading(candidateId) {
  session.jobMatchStatuses[candidateId] = 'loading'
  delete session.jobMatchErrors[candidateId]
}

export function setJobMatchResult(candidateId, result) {
  session.jobMatches[candidateId] = structuredClone(result)
  session.jobMatchStatuses[candidateId] = 'success'
  delete session.jobMatchErrors[candidateId]
}

export function setJobMatchError(candidateId, message) {
  session.jobMatchStatuses[candidateId] = 'error'
  session.jobMatchErrors[candidateId] = message
}
