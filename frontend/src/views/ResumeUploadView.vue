<script setup>
import { computed, ref } from 'vue'

import {
  getFriendlyApiError,
  getFriendlyResumeItemError,
  parseResumeBatch,
  scoreJobMatch,
} from '../services/api'
import {
  session,
  setCandidates,
  setJobMatchError,
  setJobMatchLoading,
  setJobMatchResult,
} from '../state/session'

const fileInput = ref(null)
const selectedFiles = ref([])
const uploadStatus = ref('idle')
const uploadMessage = ref('')
const batchResult = ref(null)

const hasCurrentJob = computed(() => Boolean(session.currentJob?.id))
const isParsing = computed(() => uploadStatus.value === 'loading')
const canSubmit = computed(
  () => hasCurrentJob.value && selectedFiles.value.length > 0 && !isParsing.value,
)
const failedResults = computed(() =>
  (batchResult.value?.results ?? []).filter((item) => !item.success),
)

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
  batchResult.value = null
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
  batchResult.value = null
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
  batchResult.value = null

  try {
    const result = await parseResumeBatch(selectedFiles.value)
    const results = Array.isArray(result.results) ? result.results : []
    const candidates = results
      .filter((item) => item.success && item.candidate)
      .map((item) => item.candidate)

    results
      .filter((item) => !item.success)
      .forEach((item) => console.error(`Resume parse failed: ${item.filename}`, item.error))

    setCandidates(candidates)
    batchResult.value = result
    uploadMessage.value = `简历解析完成，正在计算 ${candidates.length} 位候选人的岗位匹配结果……`

    const scoringTasks = candidates.map(async (candidate) => {
      if (!candidate.id) return false

      setJobMatchLoading(candidate.id)
      try {
        const matchResult = await scoreJobMatch(session.currentJob.id, candidate)
        setJobMatchResult(candidate.id, matchResult)
        return true
      } catch (error) {
        setJobMatchError(candidate.id, getFriendlyApiError(error, '岗位匹配评分'))
        return false
      }
    })
    const scoringResults = await Promise.all(scoringTasks)
    const scoredCount = scoringResults.filter(Boolean).length
    const scoringFailedCount = candidates.length - scoredCount

    uploadStatus.value = scoringFailedCount ? 'error' : 'success'
    uploadMessage.value = scoringFailedCount
      ? `简历解析完成；岗位匹配 ${scoredCount} 人成功，${scoringFailedCount} 人失败。可在候选人列表查看。`
      : `解析与岗位匹配完成：${scoredCount} 位候选人已生成真实评分结果。`
  } catch (error) {
    uploadStatus.value = 'error'
    uploadMessage.value = getFriendlyApiError(error, '简历批量解析')
  }
}
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

      <div v-if="batchResult" class="batch-result">
        <div class="batch-summary">
          <div><span>处理总数</span><strong>{{ batchResult.total }}</strong></div>
          <div><span>解析成功</span><strong>{{ batchResult.success_count }}</strong></div>
          <div><span>解析失败</span><strong>{{ batchResult.failed_count }}</strong></div>
        </div>

        <div v-if="failedResults.length" class="failed-files">
          <h3>未能解析的文件</h3>
          <ul>
            <li v-for="item in failedResults" :key="item.filename">
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
