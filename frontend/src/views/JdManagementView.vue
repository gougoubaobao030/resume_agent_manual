<script setup>
import { computed, ref } from 'vue'

import { getFriendlyApiError, parseJd, saveJd } from '../services/api'
import { session, setCurrentJob } from '../state/session'

const categoryOptions = [
  { value: 'technical', label: '技术能力' },
  { value: 'experience', label: '工作经验' },
  { value: 'education', label: '教育背景' },
  { value: 'other', label: '其他' },
]

let rowSequence = 0

function editableRequirement(requirement = {}) {
  rowSequence += 1
  return {
    _key: `requirement-${rowSequence}`,
    id: requirement.id,
    name: requirement.name ?? '',
    description: requirement.description ?? '',
    category: requirement.category ?? 'other',
    weight: requirement.weight ?? 1,
    must_have: Boolean(requirement.must_have),
  }
}

const rawText = ref(session.currentJob?.raw_text ?? '')
const jobTitle = ref(session.currentJob?.job_title ?? '')
const requirements = ref(
  (session.currentJob?.requirements ?? []).map(editableRequirement),
)
const warnings = ref([])
const savedJobId = ref(session.currentJob?.id ?? '')

const parseStatus = ref('idle')
const parseMessage = ref('')
const saveStatus = ref(session.currentJob ? 'success' : 'idle')
const saveMessage = ref(session.currentJob ? '当前会话中的 JD 已载入。' : '')

const hasParsedJob = computed(() => requirements.value.length > 0)
const isBusy = computed(
  () => parseStatus.value === 'loading' || saveStatus.value === 'loading',
)

async function handleParse() {
  const cleanedText = rawText.value.trim()

  if (!cleanedText) {
    parseStatus.value = 'error'
    parseMessage.value = '请先输入岗位说明。'
    return
  }

  if (cleanedText.length < 10) {
    parseStatus.value = 'error'
    parseMessage.value = '岗位说明过短，请补充岗位职责或任职要求。'
    return
  }

  parseStatus.value = 'loading'
  parseMessage.value = 'AI 正在解析岗位说明，请稍候……'
  saveStatus.value = 'idle'
  saveMessage.value = ''
  savedJobId.value = ''

  try {
    const result = await parseJd(cleanedText)
    const job = result.job

    rawText.value = job.raw_text
    jobTitle.value = job.job_title
    requirements.value = job.requirements.map(editableRequirement)
    warnings.value = result.warnings ?? []
    parseStatus.value = 'success'
    parseMessage.value = `解析完成，共识别 ${requirements.value.length} 项岗位要求。`
  } catch (error) {
    parseStatus.value = 'error'
    parseMessage.value = getFriendlyApiError(error, 'JD 解析')
  }
}

function addRequirement() {
  requirements.value.push(editableRequirement())
  saveStatus.value = 'idle'
  saveMessage.value = ''
}

function removeRequirement(index) {
  requirements.value.splice(index, 1)
  saveStatus.value = 'idle'
  saveMessage.value = ''
}

function validateJob() {
  if (!jobTitle.value.trim()) {
    return '请填写岗位名称。'
  }

  if (requirements.value.length === 0) {
    return '请至少保留一项岗位要求。'
  }

  const invalidNameIndex = requirements.value.findIndex((item) => !item.name.trim())
  if (invalidNameIndex >= 0) {
    return `第 ${invalidNameIndex + 1} 项要求缺少名称。`
  }

  const invalidWeightIndex = requirements.value.findIndex((item) => {
    const weight = Number(item.weight)
    return !Number.isFinite(weight) || weight < 0 || weight > 1000
  })
  if (invalidWeightIndex >= 0) {
    return `第 ${invalidWeightIndex + 1} 项的相对权重应为 0–1000 之间的数字。`
  }

  return ''
}

function requirementPayload(item) {
  const payload = {
    name: item.name.trim(),
    description: item.description.trim(),
    category: item.category,
    weight: Number(item.weight),
    must_have: Boolean(item.must_have),
  }

  if (item.id) {
    payload.id = item.id
  }

  return payload
}

async function handleSave() {
  const validationMessage = validateJob()
  if (validationMessage) {
    saveStatus.value = 'error'
    saveMessage.value = validationMessage
    return
  }

  saveStatus.value = 'loading'
  saveMessage.value = '正在保存 HR 确认后的 JD……'

  const payload = {
    job_title: jobTitle.value.trim(),
    raw_text: rawText.value.trim(),
    requirements: requirements.value.map(requirementPayload),
  }

  try {
    const result = await saveJd(payload)
    const savedJob = result.job

    setCurrentJob(savedJob)
    jobTitle.value = savedJob.job_title
    requirements.value = savedJob.requirements.map(editableRequirement)
    savedJobId.value = savedJob.id
    saveStatus.value = 'success'
    saveMessage.value = 'JD 已保存，可继续用于本次招聘流程。'
  } catch (error) {
    saveStatus.value = 'error'
    saveMessage.value = getFriendlyApiError(error, 'JD 保存')
  }
}
</script>

<template>
  <section class="page-stack">
    <div class="page-heading">
      <p class="eyebrow">JOB DESCRIPTION</p>
      <h2>JD 解析与确认</h2>
      <p>输入岗位说明，由 AI 提取岗位要求，再由 HR 修改并确认保存。</p>
    </div>

    <div class="jd-workspace">
      <article class="panel panel--form">
        <div class="panel__header">
          <div>
            <span class="step-label">STEP 1</span>
            <h3>输入岗位说明</h3>
          </div>
          <span
            v-if="parseStatus !== 'idle'"
            class="status-badge"
            :class="`status-badge--${parseStatus}`"
          >
            {{ parseStatus === 'loading' ? '解析中' : parseStatus === 'success' ? '解析成功' : '需要确认' }}
          </span>
        </div>
        <label class="field-label" for="jd-text">岗位说明（JD）</label>
        <textarea
          id="jd-text"
          v-model="rawText"
          rows="15"
          placeholder="请粘贴完整的岗位职责、任职要求和加分条件……"
          :disabled="isBusy"
        ></textarea>

        <div
          v-if="parseMessage"
          class="inline-message"
          :class="`inline-message--${parseStatus}`"
          role="status"
        >
          <span v-if="parseStatus === 'loading'" class="loading-spinner" aria-hidden="true"></span>
          {{ parseMessage }}
        </div>

        <div class="form-footer">
          <span class="helper-text">建议包含岗位名称、职责、技能和经验要求。</span>
          <button
            class="button button--primary"
            type="button"
            :disabled="isBusy"
            @click="handleParse"
          >
            {{ parseStatus === 'loading' ? '正在解析…' : 'AI 解析 JD' }}
          </button>
        </div>
      </article>

      <article class="panel panel--form">
        <div class="panel__header">
          <div>
            <span class="step-label">STEP 2</span>
            <h3>HR 确认结果</h3>
          </div>
          <span v-if="!hasParsedJob" class="status-badge status-badge--neutral">等待解析</span>
          <span v-else class="status-badge status-badge--ready">可编辑</span>
        </div>

        <div v-if="!hasParsedJob" class="empty-state empty-state--compact">
          <div class="empty-state__mark">JD</div>
          <h3>尚无解析结果</h3>
          <p>完成解析后，可在这里修改岗位名称、要求、权重及硬性条件。</p>
        </div>

        <div v-else class="jd-editor">
          <div v-if="warnings.length" class="warning-list">
            <strong>解析提示</strong>
            <ul>
              <li v-for="warning in warnings" :key="warning">{{ warning }}</li>
            </ul>
          </div>

          <label class="field-label" for="job-title">岗位名称</label>
          <input id="job-title" v-model="jobTitle" class="text-input" :disabled="isBusy" />

          <div class="requirements-heading">
            <div>
              <h4>岗位要求</h4>
              <p>权重为相对重要度，保存时不会在前端归一化。</p>
            </div>
            <button class="button button--secondary button--small" type="button" :disabled="isBusy" @click="addRequirement">
              ＋ 新增要求
            </button>
          </div>

          <div class="requirements-list">
            <article
              v-for="(requirement, index) in requirements"
              :key="requirement._key"
              class="requirement-card"
            >
              <div class="requirement-card__header">
                <strong>要求 {{ index + 1 }}</strong>
                <button
                  class="danger-link"
                  type="button"
                  :disabled="isBusy"
                  :aria-label="`删除第 ${index + 1} 项要求`"
                  @click="removeRequirement(index)"
                >
                  删除
                </button>
              </div>

              <div class="requirement-fields">
                <label class="field field--name">
                  <span>要求名称</span>
                  <input v-model="requirement.name" class="text-input" :disabled="isBusy" />
                </label>
                <label class="field field--category">
                  <span>分类</span>
                  <select v-model="requirement.category" class="select-input" :disabled="isBusy">
                    <option v-for="option in categoryOptions" :key="option.value" :value="option.value">
                      {{ option.label }}
                    </option>
                  </select>
                </label>
                <label class="field field--weight">
                  <span>相对权重</span>
                  <input
                    v-model.number="requirement.weight"
                    class="text-input"
                    type="number"
                    min="0"
                    max="1000"
                    step="0.1"
                    :disabled="isBusy"
                  />
                </label>
                <label class="checkbox-field">
                  <input v-model="requirement.must_have" type="checkbox" :disabled="isBusy" />
                  <span><strong>硬性条件</strong><small>不满足时需要重点确认</small></span>
                </label>
                <label class="field field--description">
                  <span>详细说明</span>
                  <textarea v-model="requirement.description" rows="3" :disabled="isBusy"></textarea>
                </label>
              </div>
            </article>
          </div>

          <div class="save-area">
            <div>
              <div
                v-if="saveMessage"
                class="inline-message"
                :class="`inline-message--${saveStatus}`"
                role="status"
              >
                <span v-if="saveStatus === 'loading'" class="loading-spinner" aria-hidden="true"></span>
                <span>{{ saveMessage }}</span>
              </div>
              <div v-if="savedJobId" class="saved-job-id">
                <span>Job ID</span>
                <code>{{ savedJobId }}</code>
              </div>
            </div>
            <button class="button button--primary" type="button" :disabled="isBusy" @click="handleSave">
              {{ saveStatus === 'loading' ? '正在保存…' : '保存确认后的 JD' }}
            </button>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>
