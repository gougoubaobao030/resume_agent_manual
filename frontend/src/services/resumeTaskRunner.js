import {
  getFriendlyApiError,
  getResumeTask,
  scoreJobMatch,
} from './api'
import { i18n } from '../i18n'
import {
  addCandidate,
  session,
  setJobMatchError,
  setJobMatchLoading,
  setJobMatchResult,
  setResumeTask,
  setResumeTaskPollingError,
} from '../state/session'
import { analyzeTalent } from './talent'

const POLL_INTERVAL_MS = 800
export const terminalResumeTaskStatuses = new Set(['completed', 'completed_with_errors', 'failed'])

let activeRun = null

function sleep(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds))
}

async function startCandidateScoring(candidate, run) {
  if (!candidate.id || session.jobMatchStatuses[candidate.id]) return

  setJobMatchLoading(candidate.id)
  try {
    const matchResult = await scoreJobMatch(run.jobId, candidate.id, run.analysisLanguage)
    setJobMatchResult(candidate.id, matchResult)

    const talentRequests = run.talentModes.flatMap((mode) => {
      const key = `${candidate.id}:${mode}`
      if (run.startedTalent.has(key) || session.talentStatuses[candidate.id]?.[mode]) return []
      run.startedTalent.add(key)
      return [analyzeTalent(candidate, mode, run.desiredTraits, run.analysisLanguage)]
    })
    void Promise.allSettled(talentRequests)
  } catch (error) {
    setJobMatchError(
      candidate.id,
      getFriendlyApiError(error, i18n.global.t('resumeUpload.operations.scoring')),
    )
  }
}

function applyTaskSnapshot(task, run) {
  setResumeTask(task)

  for (const item of task.items ?? []) {
    if (item.status !== 'success' || !item.candidate) continue

    addCandidate(item.candidate)
    if (run.startedCandidates.has(item.candidate.id)) continue
    run.startedCandidates.add(item.candidate.id)
    void startCandidateScoring(item.candidate, run)
  }
}

async function pollResumeTask(run) {
  while (true) {
    let task
    try {
      task = await getResumeTask(run.taskId)
    } catch (error) {
      setResumeTaskPollingError(
        getFriendlyApiError(error, i18n.global.t('resumeUpload.operations.taskStatus')),
      )
      return
    }

    applyTaskSnapshot(task, run)
    if (terminalResumeTaskStatuses.has(task.status)) return
    await sleep(POLL_INTERVAL_MS)
  }
}

export function startResumeTaskRunner(task, options) {
  if (activeRun?.taskId === task.task_id) return activeRun.promise
  if (activeRun) return activeRun.promise

  const run = {
    taskId: task.task_id,
    jobId: options.jobId,
    talentModes: [...options.talentModes],
    desiredTraits: [...options.desiredTraits],
    analysisLanguage: options.analysisLanguage,
    startedCandidates: new Set(),
    startedTalent: new Set(),
    promise: null,
  }

  applyTaskSnapshot(task, run)
  if (terminalResumeTaskStatuses.has(task.status)) return Promise.resolve()

  run.promise = pollResumeTask(run).finally(() => {
    if (activeRun === run) activeRun = null
  })
  activeRun = run
  return run.promise
}
