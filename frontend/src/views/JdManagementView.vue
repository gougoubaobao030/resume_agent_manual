<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { deleteJd, getFriendlyApiError, parseJd, saveJd, updateJd } from '../services/api'
import { session, setCandidates, setCurrentJob } from '../state/session'
import { refreshJobs, selectJob } from '../state/workspace'

const { t } = useI18n()
const currentSampleJd = computed(() => t('jd.sample'))

const warningKeys = {
  '未解析出明确的岗位要求，请HR检查原文并手动补充。': 'jd.warnings.noRequirements',
  'JD中未解析出明确的学历要求，如有需要请HR手动补充。': 'jd.warnings.noEducation',
  '所有要求的建议权重均为0，后续评分时将按等权处理。': 'jd.warnings.zeroWeights',
}

function localizeWarning(warning) {
  return warningKeys[warning] ? t(warningKeys[warning]) : warning
}

const categoryOptions = [
  { value: 'technical', labelKey: 'jd.categories.technical' },
  { value: 'experience', labelKey: 'jd.categories.experience' },
  { value: 'education', labelKey: 'jd.categories.education' },
  { value: 'other', labelKey: 'jd.categories.other' },
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
const saveMessage = ref(session.currentJob ? t('jd.messages.loaded') : '')
const deleteStatus = ref('idle')
const deleteMessage = ref('')

const hasParsedJob = computed(() => requirements.value.length > 0)
const canDeleteJob = computed(
  () => Boolean(savedJobId.value && session.currentJob?.id === savedJobId.value),
)
const isBusy = computed(
  () => parseStatus.value === 'loading'
    || saveStatus.value === 'loading'
    || deleteStatus.value === 'loading',
)

function loadJobIntoEditor(job) {
  rawText.value = job?.raw_text ?? ''
  jobTitle.value = job?.job_title ?? ''
  requirements.value = (job?.requirements ?? []).map(editableRequirement)
  savedJobId.value = job?.id ?? ''
  saveStatus.value = job ? 'success' : 'idle'
  saveMessage.value = job ? t('jd.messages.loaded') : ''
}

watch(() => session.currentJob?.id, () => loadJobIntoEditor(session.currentJob))

async function handleJobSelection(event) {
  const job = session.jobs.find((item) => item.id === event.target.value)
  if (job) {
    deleteStatus.value = 'idle'
    deleteMessage.value = ''
    await selectJob(job)
  }
}

function startNewJob() {
  loadJobIntoEditor(null)
  warnings.value = []
  parseStatus.value = 'idle'
  parseMessage.value = ''
  deleteStatus.value = 'idle'
  deleteMessage.value = ''
}

async function handleDeleteJob() {
  const job = session.currentJob
  if (!job?.id || job.id !== savedJobId.value || deleteStatus.value === 'loading') return

  if (!window.confirm(t('jd.messages.deleteConfirm', { title: job.job_title }))) return

  const deletedJobId = job.id
  const deletedJobTitle = job.job_title
  let deleteSucceeded = false

  deleteStatus.value = 'loading'
  deleteMessage.value = ''

  try {
    await deleteJd(deletedJobId)
    deleteSucceeded = true

    session.jobs = session.jobs.filter((item) => item.id !== deletedJobId)
    setCurrentJob(null)
    setCandidates([])
    localStorage.removeItem('current-job-id')
    loadJobIntoEditor(null)
    warnings.value = []
    parseStatus.value = 'idle'
    parseMessage.value = ''

    const jobs = await refreshJobs()
    if (jobs.length) await selectJob(jobs[0])

    deleteStatus.value = 'success'
    deleteMessage.value = t('jd.messages.deleteSuccess', { title: deletedJobTitle })
  } catch (error) {
    if (!deleteSucceeded) {
      deleteStatus.value = 'error'
      deleteMessage.value = getFriendlyApiError(error, t('jd.operations.delete'))
      return
    }

    setCurrentJob(null)
    setCandidates([])
    localStorage.removeItem('current-job-id')
    loadJobIntoEditor(null)
    deleteStatus.value = 'error'
    deleteMessage.value = t('jd.messages.deleteReloadFailed')
  }
}

async function handleParse() {
  const cleanedText = rawText.value.trim() || currentSampleJd.value

  if (cleanedText.length < 10) {
    parseStatus.value = 'error'
    parseMessage.value = t('jd.messages.tooShort')
    return
  }

  parseStatus.value = 'loading'
  parseMessage.value = t('jd.messages.parsing')
  saveStatus.value = 'idle'
  saveMessage.value = ''
  savedJobId.value = ''

  try {
    const result = await parseJd(cleanedText)
    const job = result.job

    rawText.value = job.raw_text
    jobTitle.value = job.job_title
    requirements.value = job.requirements.map(editableRequirement)
    warnings.value = (result.warnings ?? []).map(localizeWarning)
    parseStatus.value = 'success'
    parseMessage.value = t('jd.messages.parsed', { count: requirements.value.length })
  } catch (error) {
    parseStatus.value = 'error'
    parseMessage.value = getFriendlyApiError(error, t('jd.operations.parse'))
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
    return t('jd.validation.jobTitle')
  }

  if (requirements.value.length === 0) {
    return t('jd.validation.requirementRequired')
  }

  const invalidNameIndex = requirements.value.findIndex((item) => !item.name.trim())
  if (invalidNameIndex >= 0) {
    return t('jd.validation.requirementName', { index: invalidNameIndex + 1 })
  }

  const invalidWeightIndex = requirements.value.findIndex((item) => {
    const weight = Number(item.weight)
    return !Number.isFinite(weight) || weight < 0 || weight > 1000
  })
  if (invalidWeightIndex >= 0) {
    return t('jd.validation.requirementWeight', { index: invalidWeightIndex + 1 })
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
  saveMessage.value = t('jd.messages.saving')

  const payload = {
    job_title: jobTitle.value.trim(),
    raw_text: rawText.value.trim(),
    requirements: requirements.value.map(requirementPayload),
  }

  try {
    const savedJob = savedJobId.value
      ? await updateJd(savedJobId.value, {
          job_title: payload.job_title,
          requirements: payload.requirements,
        })
      : (await saveJd(payload)).job

    await refreshJobs()
    await selectJob(savedJob)
    jobTitle.value = savedJob.job_title
    requirements.value = savedJob.requirements.map(editableRequirement)
    savedJobId.value = savedJob.id
    saveStatus.value = 'success'
    saveMessage.value = t('jd.messages.saved')
  } catch (error) {
    saveStatus.value = 'error'
    saveMessage.value = getFriendlyApiError(error, t('jd.operations.save'))
  }
}
</script>

<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div><p class="eyebrow">{{ t('jd.eyebrow') }}</p><h2>{{ t('jd.title') }}</h2><p>{{ t('jd.description') }}</p></div>
      <div class="job-selector">
        <select class="select-input" :value="session.currentJob?.id || ''" :disabled="isBusy" @change="handleJobSelection">
          <option value="" disabled>{{ t('jd.actions.selectJob') }}</option>
          <option v-for="job in session.jobs" :key="job.id" :value="job.id">{{ job.job_title }}</option>
        </select>
        <button class="button button--secondary button--small" type="button" :disabled="isBusy" @click="startNewJob">{{ t('jd.actions.newJob') }}</button>
        <button
          v-if="canDeleteJob"
          class="danger-link"
          type="button"
          :disabled="isBusy"
          @click="handleDeleteJob"
        >
          {{ t(deleteStatus === 'loading' ? 'jd.actions.deletingJob' : 'jd.actions.deleteJob') }}
        </button>
      </div>
    </div>

    <p
      v-if="deleteMessage"
      class="inline-message"
      :class="`inline-message--${deleteStatus}`"
      :role="deleteStatus === 'error' ? 'alert' : 'status'"
    >
      {{ deleteMessage }}
    </p>

    <div class="jd-workspace">
      <article class="panel panel--form">
        <div class="panel__header">
          <div>
            <span class="step-label">{{ t('jd.step1.label') }}</span>
            <h3>{{ t('jd.step1.title') }}</h3>
          </div>
          <span
            v-if="parseStatus !== 'idle'"
            class="status-badge"
            :class="`status-badge--${parseStatus}`"
          >
            {{ t(parseStatus === 'loading' ? 'jd.status.parsing' : parseStatus === 'success' ? 'jd.status.parseSuccess' : 'jd.status.needsAttention') }}
          </span>
        </div>
        <label class="field-label" for="jd-text">{{ t('jd.fields.rawText') }}</label>
        <textarea
          id="jd-text"
          v-model="rawText"
          rows="26"
          :placeholder="currentSampleJd"
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
          <span class="helper-text">{{ t('jd.step1.helper') }}</span>
          <button
            class="button button--primary"
            type="button"
            :disabled="isBusy"
            @click="handleParse"
          >
            {{ t(parseStatus === 'loading' ? 'jd.actions.parsing' : 'jd.actions.parse') }}
          </button>
        </div>
      </article>

      <article class="panel panel--form">
        <div class="panel__header">
          <div>
            <span class="step-label">{{ t('jd.step2.label') }}</span>
            <h3>{{ t('jd.step2.title') }}</h3>
          </div>
          <span v-if="!hasParsedJob" class="status-badge status-badge--neutral">{{ t('jd.status.waiting') }}</span>
          <span v-else class="status-badge status-badge--ready">{{ t('jd.status.editable') }}</span>
        </div>

        <div v-if="!hasParsedJob" class="empty-state empty-state--compact">
          <div class="empty-state__mark">JD</div>
          <h3>{{ t('jd.empty.title') }}</h3>
          <p>{{ t('jd.empty.description') }}</p>
        </div>

        <div v-else class="jd-editor">
          <div v-if="warnings.length" class="warning-list">
            <strong>{{ t('jd.parseWarnings') }}</strong>
            <ul>
              <li v-for="warning in warnings" :key="warning">{{ warning }}</li>
            </ul>
          </div>

          <label class="field-label" for="job-title">{{ t('jd.fields.jobTitle') }}</label>
          <input id="job-title" v-model="jobTitle" class="text-input" :disabled="isBusy" />

          <div class="requirements-heading">
            <div>
              <h4>{{ t('jd.requirements.title') }}</h4>
              <p>{{ t('jd.requirements.weightNote') }}</p>
            </div>
            <button class="button button--secondary button--small" type="button" :disabled="isBusy" @click="addRequirement">
              {{ t('jd.actions.addRequirement') }}
            </button>
          </div>

          <div class="requirements-list">
            <article
              v-for="(requirement, index) in requirements"
              :key="requirement._key"
              class="requirement-card"
            >
              <div class="requirement-card__header">
                <strong>{{ t('jd.requirements.item', { index: index + 1 }) }}</strong>
                <button
                  class="danger-link"
                  type="button"
                  :disabled="isBusy"
                  :aria-label="t('jd.actions.deleteRequirementLabel', { index: index + 1 })"
                  @click="removeRequirement(index)"
                >
                  {{ t('jd.actions.delete') }}
                </button>
              </div>

              <div class="requirement-fields">
                <label class="field field--name">
                  <span>{{ t('jd.fields.requirementName') }}</span>
                  <input v-model="requirement.name" class="text-input" :disabled="isBusy" />
                </label>
                <label class="field field--category">
                  <span>{{ t('jd.fields.category') }}</span>
                  <select v-model="requirement.category" class="select-input" :disabled="isBusy">
                    <option v-for="option in categoryOptions" :key="option.value" :value="option.value">
                      {{ t(option.labelKey) }}
                    </option>
                  </select>
                </label>
                <label class="field field--weight">
                  <span>{{ t('jd.fields.weight') }}</span>
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
                  <span><strong>{{ t('jd.fields.mustHave') }}</strong><small>{{ t('jd.fields.mustHaveHint') }}</small></span>
                </label>
                <label class="field field--description">
                  <span>{{ t('jd.fields.description') }}</span>
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
                <span>{{ t('jd.fields.jobId') }}</span>
                <code>{{ savedJobId }}</code>
              </div>
            </div>
            <button class="button button--primary" type="button" :disabled="isBusy" @click="handleSave">
              {{ t(saveStatus === 'loading' ? 'jd.actions.saving' : 'jd.actions.save') }}
            </button>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
#jd-text::placeholder {
  color: #94a3b8;
  opacity: 1;
}
.job-selector { display: flex; align-items: center; gap: 10px; }
</style>
