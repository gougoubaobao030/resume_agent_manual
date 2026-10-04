import { reactive } from 'vue'

import {
  ApiError,
  getCandidates,
  getJds,
  getJobMatches,
  getTalentResult,
} from '../services/api'
import {
  clearResumeTask,
  session,
  setCandidates,
  setCurrentJob,
  setJobMatchResult,
  setTalentResult,
} from './session'


export const workspace = reactive({ initialized: false, loading: false, error: '' })
let workspaceGeneration = 0

export async function refreshJobs(generation = workspaceGeneration) {
  const jobs = await getJds()
  if (generation === workspaceGeneration) session.jobs = jobs
  return jobs
}

export async function selectJob(job, generation = workspaceGeneration) {
  workspace.loading = true
  workspace.error = ''
  try {
    if (generation !== workspaceGeneration) return
    setCurrentJob(job)
    localStorage.setItem('current-job-id', job.id)
    const [candidates, matches] = await Promise.all([
      getCandidates(job.id),
      getJobMatches(job.id),
    ])
    if (generation !== workspaceGeneration) return
    setCandidates(candidates)
    matches.forEach((result) => setJobMatchResult(result.candidate_id, result))

    await Promise.all(candidates.map(async (candidate) => {
      try {
        const result = await getTalentResult(candidate.id)
        if (generation === workspaceGeneration) setTalentResult(candidate.id, result)
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 404) throw error
      }
    }))
  } catch (error) {
    if (generation !== workspaceGeneration) return
    workspace.error = error.detail || error.message || 'Load workspace failed'
    throw error
  } finally {
    if (generation === workspaceGeneration) workspace.loading = false
  }
}

export async function initializeWorkspace() {
  if (workspace.initialized) return
  const generation = workspaceGeneration
  workspace.error = ''
  try {
    const jobs = await refreshJobs(generation)
    if (generation !== workspaceGeneration) return
    if (jobs.length) {
      const cachedId = localStorage.getItem('current-job-id')
      await selectJob(jobs.find((job) => job.id === cachedId) || jobs[0], generation)
    }
    if (generation !== workspaceGeneration) return
    workspace.initialized = true
  } catch (error) {
    if (generation !== workspaceGeneration) return
    workspace.initialized = false
    workspace.error = error.detail || error.message || 'Load workspace failed'
    throw error
  }
}

export function resetWorkspace() {
  workspaceGeneration += 1
  workspace.initialized = false
  workspace.loading = false
  workspace.error = ''
  session.jobs = []
  setCurrentJob(null)
  setCandidates([])
  clearResumeTask()
}
