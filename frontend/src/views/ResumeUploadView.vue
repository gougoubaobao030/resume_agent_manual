<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  getFriendlyApiError,
  getFriendlyResumeItemError,
  createResumeTask,
  getResumeTask,
  scoreJobMatch,
} from '../services/api'
import {
  session,
  addCandidate,
  clearResumeTask,
  setResumeTask,
  setJobMatchError,
  setJobMatchLoading,
  setJobMatchResult,
} from '../state/session'
import TalentSettings from '../components/TalentSettings.vue'
import { analyzeTalent } from '../services/talent'

const { locale, t } = useI18n()

const fileInput = ref(null)
const selectedFiles = ref([])
const uploadStatus = ref('idle')
const uploadMessage = ref('')
const POLL_INTERVAL_MS = 800
const terminalTaskStatuses = new Set(['completed', 'completed_with_errors', 'failed'])
let pollingStopped = false
let activeJobId = null
let activeTalentModes = []
let activeDesiredTraits = []
let activeAnalysisLanguage = 'zh-CN'
const selectedTalentModes = ref([])

const hasCurrentJob = computed(() => Boolean(session.currentJob?.id))
const isParsing = computed(() => uploadStatus.value === 'loading')
const canSubmit = computed(
  () => hasCurrentJob.value && selectedFiles.value.length > 0 && !isParsing.value
    && (!selectedTalentModes.value.includes('specified') || session.desiredTraits.length > 0),
)
const taskItems = computed(() => session.resumeTaskItems)
const taskCounts = computed(() => {
  const counts = { completed: 0, success: 0, failed: 0, running: 0, pending: 0 }
  taskItems.value.forEach((item) => {
    if (item.status in counts) counts[item.status] += 1
    if (item.status === 'success' || item.status === 'failed') counts.completed += 1
  })
  return counts
})
const failedResults = computed(() => taskItems.value.filter((item) => item.status === 'failed'))

const itemStatusDisplay = {
  pending: { labelKey: 'resumeUpload.status.pending', className: 'status-badge--neutral' },
  running: { labelKey: 'resumeUpload.status.running', className: 'status-badge--loading' },
  success: { labelKey: 'resumeUpload.status.success', className: 'status-badge--success' },
  failed: { labelKey: 'resumeUpload.status.failed', className: 'status-badge--error' },
}

function itemStatus(item) {
  const status = itemStatusDisplay[item.status] ?? itemStatusDisplay.pending
  return { ...status, label: t(status.labelKey) }
}

function sleep(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds))
}

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function acceptFiles(fileList) {
  const files = Array.from(fileList ?? [])

  if (!files.length) {
    return
  }

  const nonPdf = files.find((file) => !file.name.toLowerCase().endsWith('.pdf'))
  if (nonPdf) {
    uploadStatus.value = 'error'
    uploadMessage.value = t('resumeUpload.messages.notPdf', { filename: nonPdf.name })
    return
  }

  if (files.length > 30) {
    uploadStatus.value = 'error'
    uploadMessage.value = t('resumeUpload.messages.tooMany')
    return
  }

  selectedFiles.value = files
  uploadStatus.value = 'idle'
  uploadMessage.value = ''
  clearResumeTask()
}

function handleFileInput(event) {
  acceptFiles(event.target.files)
  event.target.value = ''
}

function handleDrop(event) {
  if (isParsing.value) return
  acceptFiles(event.dataTransfer.files)
}

function removeFile(index) {
  selectedFiles.value.splice(index, 1)
  uploadStatus.value = 'idle'
  uploadMessage.value = ''
  clearResumeTask()
}

async function startCandidateScoring(candidate) {
  if (!candidate.id || !activeJobId || session.jobMatchStatuses[candidate.id]) return

  // loading 在请求前写入；后续轮询再次看到同一 candidate 时不会重复评分。
  setJobMatchLoading(candidate.id)
  try {
    const matchResult = await scoreJobMatch(activeJobId, candidate.id, activeAnalysisLanguage)
    setJobMatchResult(candidate.id, matchResult)
    void Promise.allSettled(activeTalentModes.map((mode) =>
      analyzeTalent(candidate, mode, activeDesiredTraits, activeAnalysisLanguage),
    ))
  } catch (error) {
    setJobMatchError(candidate.id, getFriendlyApiError(error, t('resumeUpload.operations.scoring')))
  }
}

function applyTaskSnapshot(task) {
  setResumeTask(task)

  for (const item of task.items ?? []) {
    if (item.status !== 'success' || !item.candidate) continue

    // success 会在每次轮询重复出现；只有第一次加入 session 才启动评分。
    if (addCandidate(item.candidate)) {
      void startCandidateScoring(item.candidate)
    }
  }
}

function finishTask(task) {
  const successCount = taskCounts.value.success
  const failedCount = taskCounts.value.failed
  uploadStatus.value = task.status === 'failed' || failedCount ? 'error' : 'success'
  uploadMessage.value = task.status === 'failed'
    ? t('resumeUpload.messages.taskFailed', { reason: task.error || t('resumeUpload.messages.noBackendReason') })
    : t('resumeUpload.messages.completed', { success: successCount, failed: failedCount })
}

async function pollResumeTask(taskId) {
  // 每次 GET 完成后才 sleep 并发起下一次，避免 setInterval 造成请求重叠。
  while (!pollingStopped) {
    let task
    try {
      task = await getResumeTask(taskId)
    } catch (error) {
      if (pollingStopped) return
      uploadStatus.value = 'error'
      uploadMessage.value = t('resumeUpload.messages.pollFailed', { error: getFriendlyApiError(error, t('resumeUpload.operations.taskStatus')) })
      return
    }

    if (pollingStopped) return
    applyTaskSnapshot(task)

    // 批次到达后端定义的终态后必须退出，否则会永久轮询。
    if (terminalTaskStatuses.has(task.status)) {
      finishTask(task)
      return
    }

    await sleep(POLL_INTERVAL_MS)
  }
}

async function handleParse() {
  if (!hasCurrentJob.value) {
    uploadStatus.value = 'error'
    uploadMessage.value = t('resumeUpload.messages.jobRequired')
    return
  }

  if (!selectedFiles.value.length) {
    uploadStatus.value = 'error'
    uploadMessage.value = t('resumeUpload.messages.fileRequired')
    return
  }

  uploadStatus.value = 'loading'
  uploadMessage.value = t('resumeUpload.messages.starting', { count: selectedFiles.value.length })
  clearResumeTask()
  activeJobId = session.currentJob.id
  activeTalentModes = [...selectedTalentModes.value]
  activeDesiredTraits = [...session.desiredTraits]
  activeAnalysisLanguage = locale.value
  pollingStopped = false

  try {
    const task = await createResumeTask(selectedFiles.value, activeJobId)
    applyTaskSnapshot(task)
    uploadMessage.value = t('resumeUpload.messages.taskCreated', { count: task.total })
    await pollResumeTask(task.task_id)
  } catch (error) {
    uploadStatus.value = 'error'
    uploadMessage.value = getFriendlyApiError(error, t('resumeUpload.operations.createTask'))
  }
}

onUnmounted(() => {
  // 页面离开后停止下一次 GET；后台任务仍由 FastAPI 继续执行。
  pollingStopped = true
})
</script>

<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div>
        <p class="eyebrow">{{ t('resumeUpload.eyebrow') }}</p>
        <h2>{{ t('resumeUpload.title') }}</h2>
        <p>{{ t('resumeUpload.description') }}</p>
      </div>
      <span class="status-badge" :class="hasCurrentJob ? 'status-badge--success' : 'status-badge--warning'">
        {{ hasCurrentJob ? session.currentJob.job_title : t('resumeUpload.jobRequired') }}
      </span>
    </div>

    <article class="panel upload-panel">
      <div class="talent-upload-options">
        <h3>{{ t('resumeUpload.talentExecution.title') }}</h3>
        <strong>{{ t('resumeUpload.talentExecution.jobMatch') }}</strong>
        <TalentSettings v-model="selectedTalentModes" multiple :disabled="isParsing" />
      </div>
      <div
        class="upload-zone"
        :class="{ 'upload-zone--disabled': isParsing }"
        @dragover.prevent
        @drop.prevent="handleDrop"
      >
        <div class="upload-zone__mark">PDF</div>
        <h3>{{ t('resumeUpload.dropzone.title') }}</h3>
        <p>{{ t('resumeUpload.dropzone.description') }}</p>
        <input
          ref="fileInput"
          class="visually-hidden"
          type="file"
          accept=".pdf,application/pdf"
          multiple
          :disabled="isParsing"
          @change="handleFileInput"
        />
        <button class="button button--secondary" type="button" :disabled="isParsing" @click="fileInput.click()">
          {{ t('resumeUpload.actions.selectFiles') }}
        </button>
      </div>

      <div v-if="selectedFiles.length" class="selected-files">
        <div class="selected-files__header">
          <div><strong>{{ t('resumeUpload.selectedFiles') }}</strong><span>{{ selectedFiles.length }} / 30</span></div>
          <button class="button button--primary" type="button" :disabled="!canSubmit" @click="handleParse">
            {{ t(isParsing ? 'resumeUpload.actions.parsing' : 'resumeUpload.actions.start') }}
          </button>
        </div>
        <ul>
          <li v-for="(file, index) in selectedFiles" :key="`${file.name}-${file.size}-${file.lastModified}`">
            <span class="file-type-mark">PDF</span>
            <div><strong>{{ file.name }}</strong><small>{{ formatFileSize(file.size) }}</small></div>
            <button type="button" :disabled="isParsing" :aria-label="t('resumeUpload.actions.removeLabel', { filename: file.name })" @click="removeFile(index)">{{ t('resumeUpload.actions.remove') }}</button>
          </li>
        </ul>
      </div>

      <div
        v-if="uploadMessage"
        class="upload-status"
        :class="`upload-status--${uploadStatus}`"
        role="status"
      >
        <span v-if="isParsing" class="loading-spinner" aria-hidden="true"></span>
        <span>{{ uploadMessage }}</span>
      </div>

      <div v-if="session.resumeTaskId" class="batch-result">
        <div class="batch-summary task-summary">
          <div><span>{{ t('resumeUpload.summary.completed') }}</span><strong>{{ taskCounts.completed }} / {{ taskItems.length }}</strong></div>
          <div><span>{{ t('resumeUpload.summary.success') }}</span><strong>{{ taskCounts.success }}</strong></div>
          <div><span>{{ t('resumeUpload.summary.failed') }}</span><strong>{{ taskCounts.failed }}</strong></div>
          <div><span>{{ t('resumeUpload.summary.running') }}</span><strong>{{ taskCounts.running }}</strong></div>
          <div><span>{{ t('resumeUpload.summary.pending') }}</span><strong>{{ taskCounts.pending }}</strong></div>
        </div>

        <div class="task-files">
          <div v-for="item in taskItems" :key="item.item_id" class="task-file-row">
            <div>
              <strong>{{ item.filename }}</strong>
              <small v-if="item.status === 'failed'">{{ getFriendlyResumeItemError(item.error) }}</small>
              <small v-else-if="item.status === 'success' && session.jobMatchStatuses[item.candidate?.id] === 'loading'">{{ t('resumeUpload.scoring.running') }}</small>
              <small v-else-if="item.status === 'success' && session.jobMatchStatuses[item.candidate?.id] === 'error'">{{ t('resumeUpload.scoring.failed') }}</small>
              <small v-else-if="item.status === 'success' && session.jobMatchStatuses[item.candidate?.id] === 'success'">{{ t('resumeUpload.scoring.completed') }}</small>
            </div>
            <span class="status-badge" :class="itemStatus(item).className">{{ itemStatus(item).label }}</span>
          </div>
        </div>

        <div v-if="failedResults.length" class="failed-files">
          <h3>{{ t('resumeUpload.failedFiles') }}</h3>
          <ul>
            <li v-for="item in failedResults" :key="item.item_id">
              <strong>{{ item.filename }}</strong>
              <span>{{ getFriendlyResumeItemError(item.error) }}</span>
            </li>
          </ul>
        </div>

        <div class="batch-result__footer">
          <span>{{ t('resumeUpload.sessionNote') }}</span>
          <RouterLink class="button button--primary" to="/candidates">{{ t('resumeUpload.actions.viewCandidates') }}</RouterLink>
        </div>
      </div>

      <div class="upload-note">
        <strong>{{ t('resumeUpload.note.title') }}</strong>
        <span>{{ t('resumeUpload.note.description') }}</span>
      </div>
    </article>
  </section>
</template>
