import { reactive } from 'vue'

export const session = reactive({
  currentJob: null,
  candidates: [],
})

export function setCurrentJob(job) {
  session.currentJob = structuredClone(job)
}

export function setCandidates(candidates) {
  session.candidates = structuredClone(candidates)
}
