<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  getFriendlyApiError,
  getFriendlyResumeItemError,
  createResumeTask,
  retryResumeTaskItem,
} from '../services/api'
import {
  session,
  clearResumeTask,
  setResumeTaskOptions,
} from '../state/session'
import TalentSettings from '../components/TalentSettings.vue'
import {
  startResumeTaskRunner,
  terminalResumeTaskStatuses,
} from '../services/resumeTaskRunner'

const { locale, t } = useI18n()

const fileInput = ref(null)
const selectedFiles = ref([])
const uploadStatus = ref('idle')
const uploadMessage = ref('')
const selectedTalentModes = ref([])
const retryingItemIds = ref([])
const retryErrors = ref({})

const hasCurrentJob = computed(() => Boolean(session.currentJob?.id))
const isParsing = computed(() => uploadStatus.value === 'loading'
  || (session.resumeTaskId
    && !session.resumeTaskError
    && !terminalResumeTaskStatuses.has(session.resumeTaskStatus)))
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
const taskMessage = computed(() => {
  if (!session.resumeTaskId) return uploadMessage.value
  if (session.resumeTaskError && !terminalResumeTaskStatuses.has(session.resumeTaskStatus)) {
    return t('resumeUpload.messages.pollFailed', { error: session.resumeTaskError })
  }
  if (!terminalResumeTaskStatuses.has(session.resumeTaskStatus)) {
    return t('resumeUpload.messages.taskCreated', { count: taskItems.value.length })
  }
  if (session.resumeTaskStatus === 'failed') {
    return t('resumeUpload.messages.taskFailed', {
      reason: session.resumeTaskError
        ? getFriendlyResumeItemError(session.resumeTaskError)
        : t('resumeUpload.messages.noBackendReason'),
    })
  }
  return t('resumeUpload.messages.completed', {
    success: taskCounts.value.success,
    failed: taskCounts.value.failed,
  })
})
const taskDisplayStatus = computed(() => {
  if (!session.resumeTaskId) return uploadStatus.value
  if (session.resumeTaskError || session.resumeTaskStatus === 'failed' || taskCounts.value.failed) return 'error'
  return terminalResumeTaskStatuses.has(session.resumeTaskStatus) ? 'success' : 'loading'
})

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

async function handleRetry(item) {
  if (retryingItemIds.value.includes(item.item_id)) return

  retryingItemIds.value = [...retryingItemIds.value, item.item_id]
  retryErrors.value = { ...retryErrors.value, [item.item_id]: '' }
  try {
    const task = await retryResumeTaskItem(session.resumeTaskId, item.item_id)
    const options = session.resumeTaskOptions ?? {
      jobId: session.currentJob?.id,
      talentModes: [...selectedTalentModes.value],
      desiredTraits: [...session.desiredTraits],
      analysisLanguage: locale.value,
    }
    void startResumeTaskRunner(task, options)
  } catch (error) {
    retryErrors.value = {
      ...retryErrors.value,
      [item.item_id]: getFriendlyApiError(error, t('resumeUpload.operations.retry')),
    }
  } finally {
    retryingItemIds.value = retryingItemIds.value.filter((id) => id !== item.item_id)
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
  const options = {
    jobId: session.currentJob.id,
    talentModes: [...selectedTalentModes.value],
    desiredTraits: [...session.desiredTraits],
    analysisLanguage: locale.value,
  }
  setResumeTaskOptions(options)

  try {
    const task = await createResumeTask(selectedFiles.value, options.jobId)
    void startResumeTaskRunner(task, options)
    uploadStatus.value = 'idle'
  } catch (error) {
    uploadStatus.value = 'error'
    uploadMessage.value = getFriendlyApiError(error, t('resumeUpload.operations.createTask'))
  }
}
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
        v-if="taskMessage"
        class="upload-status"
        :class="`upload-status--${taskDisplayStatus}`"
        role="status"
      >
        <span v-if="isParsing" class="loading-spinner" aria-hidden="true"></span>
        <span>{{ taskMessage }}</span>
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
            <div class="task-file-row__content">
              <strong>{{ item.filename }}</strong>
              <small v-if="item.status === 'failed'">{{ getFriendlyResumeItemError(item.error) }}</small>
              <small v-if="retryErrors[item.item_id]" class="task-file-row__retry-error">{{ retryErrors[item.item_id] }}</small>
              <small v-else-if="item.status === 'success' && session.jobMatchStatuses[item.candidate?.id] === 'loading'">{{ t('resumeUpload.scoring.running') }}</small>
              <small v-else-if="item.status === 'success' && session.jobMatchStatuses[item.candidate?.id] === 'error'">{{ t('resumeUpload.scoring.failed') }}</small>
              <small v-else-if="item.status === 'success' && session.jobMatchStatuses[item.candidate?.id] === 'success'">{{ t('resumeUpload.scoring.completed') }}</small>
            </div>
            <div class="task-file-row__actions">
              <button
                v-if="item.status === 'failed' && terminalResumeTaskStatuses.has(session.resumeTaskStatus)"
                class="button button--secondary button--small"
                type="button"
                :disabled="retryingItemIds.includes(item.item_id)"
                @click="handleRetry(item)"
              >
                {{ t(retryingItemIds.includes(item.item_id) ? 'resumeUpload.actions.retrying' : 'resumeUpload.actions.retry') }}
              </button>
              <span class="status-badge" :class="itemStatus(item).className">{{ itemStatus(item).label }}</span>
            </div>
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
