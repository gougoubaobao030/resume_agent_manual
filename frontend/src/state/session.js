import { reactive, toRaw } from 'vue'

export const session = reactive({
  jobs: [],
  currentJob: null,
  candidates: [],
  jobMatches: {},
  jobMatchStatuses: {},
  jobMatchErrors: {},
  talentResults: {},
  talentStatuses: {},
  talentErrors: {},
  talentMode: 'auto',
  desiredTraits: [],
  selectedTalentCandidateIds: [],
  resumeTaskId: null,
  resumeTaskStatus: null,
  resumeTaskItems: [],
  resumeTaskError: '',
  resumeTaskOptions: null,
})

export function setCurrentJob(job) {
  const jobChanged = session.currentJob?.id && session.currentJob.id !== job?.id
  session.currentJob = job ? structuredClone(toRaw(job)) : null

  if (jobChanged) {
    session.jobMatches = {}
    session.jobMatchStatuses = {}
    session.jobMatchErrors = {}
    session.selectedTalentCandidateIds = []
  }
}

export function setCandidates(candidates) {
  session.candidates = structuredClone(candidates)
  session.jobMatches = {}
  session.jobMatchStatuses = {}
  session.jobMatchErrors = {}
  session.talentResults = {}
  session.talentStatuses = {}
  session.talentErrors = {}
  session.selectedTalentCandidateIds = []
}

export function clearResumeTask() {
  session.resumeTaskId = null
  session.resumeTaskStatus = null
  session.resumeTaskItems = []
  session.resumeTaskError = ''
  session.resumeTaskOptions = null
}

export function setResumeTaskOptions(options) {
  session.resumeTaskOptions = structuredClone(options)
}

export function setResumeTask(task) {
  session.resumeTaskId = task.task_id
  session.resumeTaskStatus = task.status
  session.resumeTaskError = task.error ?? ''
  // 每次轮询都用 item_id 对齐状态，不依赖可能重复的 filename。
  const previousItems = new Map(session.resumeTaskItems.map((item) => [item.item_id, item]))
  session.resumeTaskItems = (task.items ?? []).map((item) => ({
    ...previousItems.get(item.item_id),
    ...structuredClone(item),
  }))
}

export function setResumeTaskPollingError(message) {
  session.resumeTaskError = message
}

export function addCandidate(candidate) {
  if (!candidate?.id || session.candidates.some((item) => item.id === candidate.id)) {
    return false
  }

  session.candidates.push(structuredClone(candidate))
  return true
}

export function removeCandidateFromCurrentJob(candidateId) {
  session.candidates = session.candidates.filter((item) => item.id !== candidateId)
  delete session.jobMatches[candidateId]
  delete session.jobMatchStatuses[candidateId]
  delete session.jobMatchErrors[candidateId]
  session.selectedTalentCandidateIds = session.selectedTalentCandidateIds.filter(
    (id) => id !== candidateId,
  )
}

export function removeCandidateFromSession(candidateId) {
  removeCandidateFromCurrentJob(candidateId)
  delete session.talentResults[candidateId]
  delete session.talentStatuses[candidateId]
  delete session.talentErrors[candidateId]
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

function ensureTalentModeState(state, candidateId) {
  if (!state[candidateId]) state[candidateId] = {}
  return state[candidateId]
}

export function setTalentLoading(candidateId, mode) {
  delete ensureTalentModeState(session.talentResults, candidateId)[mode]
  ensureTalentModeState(session.talentStatuses, candidateId)[mode] = 'loading'
  delete ensureTalentModeState(session.talentErrors, candidateId)[mode]
}

export function setTalentResult(candidateId, mode, result) {
  ensureTalentModeState(session.talentResults, candidateId)[mode] = structuredClone(result)
  ensureTalentModeState(session.talentStatuses, candidateId)[mode] = 'success'
  delete ensureTalentModeState(session.talentErrors, candidateId)[mode]
}

export function setTalentError(candidateId, mode, message) {
  ensureTalentModeState(session.talentStatuses, candidateId)[mode] = 'error'
  ensureTalentModeState(session.talentErrors, candidateId)[mode] = message
}
