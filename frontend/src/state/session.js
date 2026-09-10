import { reactive } from 'vue'

export const session = reactive({
  currentJob: null,
})

export function setCurrentJob(job) {
  session.currentJob = structuredClone(job)
}
