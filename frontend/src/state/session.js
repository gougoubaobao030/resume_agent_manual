import { reactive } from 'vue'

export const session = reactive({
  currentJob: null,
  candidates: [],
  jobMatches: {},
  jobMatchStatuses: {},
  jobMatchErrors: {},
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
