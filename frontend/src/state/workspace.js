import { reactive } from 'vue'

import {
  ApiError,
  getCandidates,
  getJds,
  getJobMatches,
  getTalentResult,
} from '../services/api'
import {
  session,
  setCandidates,
  setCurrentJob,
  setJobMatchResult,
  setTalentResult,
} from './session'


export const workspace = reactive({ initialized: false, loading: false, error: '' })

export async function refreshJobs() {
  session.jobs = await getJds()
  return session.jobs
}

export async function selectJob(job) {
  workspace.loading = true
  workspace.error = ''
  try {
    setCurrentJob(job)
    localStorage.setItem('current-job-id', job.id)
    const [candidates, matches] = await Promise.all([
      getCandidates(job.id),
      getJobMatches(job.id),
    ])
    setCandidates(candidates)
    matches.forEach((result) => setJobMatchResult(result.candidate_id, result))

    await Promise.all(candidates.map(async (candidate) => {
      try {
        setTalentResult(candidate.id, await getTalentResult(candidate.id))
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 404) throw error
      }
    }))
  } catch (error) {
    workspace.error = error.detail || error.message || 'Load workspace failed'
    throw error
  } finally {
    workspace.loading = false
  }
}

export async function initializeWorkspace() {
  if (workspace.initialized) return
  try {
    const jobs = await refreshJobs()
    if (jobs.length) {
      const cachedId = localStorage.getItem('current-job-id')
      await selectJob(jobs.find((job) => job.id === cachedId) || jobs[0])
    }
  } finally {
    workspace.initialized = true
  }
}

export function resetWorkspace() {
  workspace.initialized = false
  workspace.loading = false
  workspace.error = ''
  session.jobs = []
  setCurrentJob(null)
  setCandidates([])
}
