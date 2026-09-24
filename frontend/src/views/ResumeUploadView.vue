<script setup>
import { computed, onUnmounted, ref } from 'vue'

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
  setCandidates,
  setResumeTask,
  setJobMatchError,
  setJobMatchLoading,
  setJobMatchResult,
} from '../state/session'
import TalentSettings from '../components/TalentSettings.vue'
import { analyzeTalent } from '../services/talent'

const fileInput = ref(null)
const selectedFiles = ref([])
const uploadStatus = ref('idle')
const uploadMessage = ref('')
const POLL_INTERVAL_MS = 800
const terminalTaskStatuses = new Set(['completed', 'completed_with_errors', 'failed'])
let pollingStopped = false
let activeJobId = null
let activeTalentTiming = 'selected'
let activeTalentMode = 'auto'
let activeDesiredTraits = []

const hasCurrentJob = computed(() => Boolean(session.currentJob?.id))
const isParsing = computed(() => uploadStatus.value === 'loading')
const canSubmit = computed(
  () => hasCurrentJob.value && selectedFiles.value.length > 0 && !isParsing.value
    && (session.talentTiming !== 'automatic' || session.talentMode !== 'specified' || session.desiredTraits.length > 0),
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
  pending: { label: '等待中', className: 'status-badge--neutral' },
  running: { label: '解析中', className: 'status-badge--loading' },
  success: { label: '解析成功', className: 'status-badge--success' },
  failed: { label: '解析失败', className: 'status-badge--error' },
}

function itemStatus(item) {
  return itemStatusDisplay[item.status] ?? itemStatusDisplay.pending
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
    uploadMessage.value = `${nonPdf.name} 不是 PDF 文件，请重新选择。`
    return
  }

  if (files.length > 30) {
    uploadStatus.value = 'error'
    uploadMessage.value = '一次最多选择 30 份简历。'
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
    const matchResult = await scoreJobMatch(activeJobId, candidate)
    setJobMatchResult(candidate.id, matchResult)
    if (activeTalentTiming === 'automatic') {
      void analyzeTalent(candidate, activeTalentMode, activeDesiredTraits)
    }
  } catch (error) {
    setJobMatchError(candidate.id, getFriendlyApiError(error, '岗位匹配评分'))
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
    ? `批量解析任务失败：${task.error || '后端未返回具体原因。'}`
    : `简历解析完成：${successCount} 份成功，${failedCount} 份失败。成功候选人的岗位评分已分别启动。`
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
      uploadMessage.value = `${getFriendlyApiError(error, '任务状态查询')} 后台任务可能仍在运行。`
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
    uploadMessage.value = '请先完成并保存 JD。'
    return
  }

  if (!selectedFiles.value.length) {
    uploadStatus.value = 'error'
    uploadMessage.value = '请先选择至少一份 PDF 简历。'
    return
  }

  uploadStatus.value = 'loading'
  uploadMessage.value = `正在解析 ${selectedFiles.value.length} 份简历，请保持页面打开……`
  clearResumeTask()
  setCandidates([])
  activeJobId = session.currentJob.id
  activeTalentTiming = session.talentTiming
  activeTalentMode = session.talentMode
  activeDesiredTraits = [...session.desiredTraits]
  pollingStopped = false

  try {
    const task = await createResumeTask(selectedFiles.value)
    applyTaskSnapshot(task)
    uploadMessage.value = `任务已创建，正在解析 ${task.total} 份简历……`
    await pollResumeTask(task.task_id)
  } catch (error) {
    uploadStatus.value = 'error'
    uploadMessage.value = getFriendlyApiError(error, '创建简历解析任务')
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
        <p class="eyebrow">RESUME IMPORT</p>
        <h2>批量导入候选人</h2>
        <p>选择当前岗位后，上传 1–30 份文本型 PDF 简历。</p>
      </div>
      <span class="status-badge" :class="hasCurrentJob ? 'status-badge--success' : 'status-badge--warning'">
        {{ hasCurrentJob ? session.currentJob.job_title : '请先完成 JD' }}
      </span>
    </div>

    <article class="panel upload-panel">
      <div class="talent-upload-options">
        <h3>人才能力分析时机</h3>
        <label><input v-model="session.talentTiming" type="radio" value="selected" :disabled="isParsing" /> 先完成岗位匹配，在候选人列表中选人分析（默认）</label>
        <label><input v-model="session.talentTiming" type="radio" value="automatic" :disabled="isParsing" /> 岗位匹配完成后自动继续分析</label>
        <TalentSettings v-if="session.talentTiming === 'automatic'" />
      </div>
      <div
        class="upload-zone"
        :class="{ 'upload-zone--disabled': isParsing }"
        @dragover.prevent
        @drop.prevent="handleDrop"
      >
        <div class="upload-zone__mark">PDF</div>
        <h3>拖放简历到此处</h3>
        <p>仅支持文本型 PDF，单次最多 30 份。扫描版 PDF 暂不支持。</p>
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
          选择 PDF 文件
        </button>
      </div>

      <div v-if="selectedFiles.length" class="selected-files">
        <div class="selected-files__header">
          <div><strong>已选择文件</strong><span>{{ selectedFiles.length }} / 30</span></div>
          <button class="button button--primary" type="button" :disabled="!canSubmit" @click="handleParse">
            {{ isParsing ? '解析中…' : '开始批量解析' }}
          </button>
        </div>
        <ul>
          <li v-for="(file, index) in selectedFiles" :key="`${file.name}-${file.size}-${file.lastModified}`">
            <span class="file-type-mark">PDF</span>
            <div><strong>{{ file.name }}</strong><small>{{ formatFileSize(file.size) }}</small></div>
            <button type="button" :disabled="isParsing" :aria-label="`移除 ${file.name}`" @click="removeFile(index)">移除</button>
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
          <div><span>已完成</span><strong>{{ taskCounts.completed }} / {{ taskItems.length }}</strong></div>
          <div><span>解析成功</span><strong>{{ taskCounts.success }}</strong></div>
          <div><span>解析失败</span><strong>{{ taskCounts.failed }}</strong></div>
          <div><span>处理中</span><strong>{{ taskCounts.running }}</strong></div>
          <div><span>等待中</span><strong>{{ taskCounts.pending }}</strong></div>
        </div>

        <div class="task-files">
          <div v-for="item in taskItems" :key="item.item_id" class="task-file-row">
            <div>
              <strong>{{ item.filename }}</strong>
              <small v-if="item.status === 'failed'">{{ getFriendlyResumeItemError(item.error) }}</small>
              <small v-else-if="item.status === 'success' && session.jobMatchStatuses[item.candidate?.id] === 'loading'">岗位评分中…</small>
              <small v-else-if="item.status === 'success' && session.jobMatchStatuses[item.candidate?.id] === 'error'">岗位评分失败</small>
              <small v-else-if="item.status === 'success' && session.jobMatchStatuses[item.candidate?.id] === 'success'">岗位评分完成</small>
            </div>
            <span class="status-badge" :class="itemStatus(item).className">{{ itemStatus(item).label }}</span>
          </div>
        </div>

        <div v-if="failedResults.length" class="failed-files">
          <h3>未能解析的文件</h3>
          <ul>
            <li v-for="item in failedResults" :key="item.item_id">
              <strong>{{ item.filename }}</strong>
              <span>{{ getFriendlyResumeItemError(item.error) }}</span>
            </li>
          </ul>
        </div>

        <div class="batch-result__footer">
          <span>成功解析的候选人已保存到当前前端运行会话。</span>
          <RouterLink class="button button--primary" to="/candidates">查看候选人</RouterLink>
        </div>
      </div>

      <div class="upload-note">
        <strong>处理说明</strong>
        <span>每份简历独立解析；单份失败不会中断其他文件。</span>
      </div>
    </article>
  </section>
</template>
