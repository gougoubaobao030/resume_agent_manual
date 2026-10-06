<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  deleteCandidate,
  getCandidatePool,
  getCandidateResumeUrl,
  getFriendlyApiError,
} from '../services/api'
import { removeCandidateFromSession } from '../state/session'

const { locale, t } = useI18n()
const candidates = ref([])
const loading = ref(true)
const errorMessage = ref('')
const successMessage = ref('')
const deletingIds = ref([])

function formatDate(value) {
  if (!value) return t('common.noInformation')
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return t('common.noInformation')
  return new Intl.DateTimeFormat(locale.value, {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(date)
}

function candidateName(candidate) {
  return candidate.name || t('common.candidateNameMissing')
}

async function loadCandidatePool() {
  loading.value = true
  errorMessage.value = ''
  try {
    candidates.value = await getCandidatePool()
  } catch (error) {
    errorMessage.value = getFriendlyApiError(error, t('candidatePool.operations.load'))
  } finally {
    loading.value = false
  }
}

async function handleDelete(candidate) {
  if (!window.confirm(t('candidatePool.deleteConfirm', { name: candidateName(candidate) }))) return

  deletingIds.value = [...deletingIds.value, candidate.id]
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await deleteCandidate(candidate.id)
    candidates.value = candidates.value.filter((item) => item.id !== candidate.id)
    removeCandidateFromSession(candidate.id)
    successMessage.value = t('candidatePool.messages.deleteSuccess', {
      name: candidateName(candidate),
    })
  } catch (error) {
    errorMessage.value = getFriendlyApiError(error, t('candidatePool.operations.delete'))
  } finally {
    deletingIds.value = deletingIds.value.filter((id) => id !== candidate.id)
  }
}

onMounted(loadCandidatePool)
</script>

<template>
  <section class="page-stack">
    <div class="page-heading">
      <p class="eyebrow">{{ t('candidatePool.eyebrow') }}</p>
      <h2>{{ t('candidatePool.title') }}</h2>
      <p>{{ t('candidatePool.description') }}</p>
    </div>

    <p v-if="errorMessage" class="inline-message inline-message--error" role="alert">{{ errorMessage }}</p>
    <p v-if="successMessage" class="inline-message inline-message--success" role="status">{{ successMessage }}</p>

    <article class="panel panel--candidate-pool">
      <div class="table-toolbar">
        <div><strong>{{ t('candidatePool.allCandidates') }}</strong><span>{{ t('candidatePool.personCount', { count: candidates.length }) }}</span></div>
      </div>

      <div v-if="loading" class="empty-state">
        <span class="loading-spinner" aria-hidden="true"></span>
        <p>{{ t('common.loading') }}</p>
      </div>
      <div v-else-if="!candidates.length" class="empty-state">
        <div class="empty-state__mark">CV</div>
        <h3>{{ t('candidatePool.empty.title') }}</h3>
        <p>{{ t('candidatePool.empty.description') }}</p>
      </div>
      <div v-else class="candidate-pool-list">
        <article v-for="candidate in candidates" :key="candidate.id" class="candidate-pool-card">
          <div class="candidate-pool-card__identity">
            <span class="candidate-avatar">{{ candidateName(candidate).slice(0, 1) }}</span>
            <div>
              <strong>{{ candidateName(candidate) }}</strong>
              <small>{{ candidate.experience_summary || t('candidatePool.experienceMissing') }}</small>
            </div>
          </div>

          <div class="candidate-pool-card__section">
            <span>{{ t('candidatePool.skills') }}</span>
            <div v-if="candidate.skills.length" class="tag-list">
              <span v-for="skill in candidate.skills.slice(0, 8)" :key="skill">{{ skill }}</span>
            </div>
            <small v-else>{{ t('candidatePool.skillsMissing') }}</small>
          </div>

          <div class="candidate-pool-card__section">
            <span>{{ t('candidatePool.jobs') }}</span>
            <div v-if="candidate.jobs.length" class="tag-list">
              <span v-for="job in candidate.jobs" :key="job.id">{{ job.job_title }}</span>
            </div>
            <small v-else>{{ t('candidatePool.jobsMissing') }}</small>
          </div>

          <dl class="candidate-pool-card__meta">
            <div><dt>{{ t('candidatePool.sourceFile') }}</dt><dd>{{ candidate.source_file || t('common.noInformation') }}</dd></div>
            <div><dt>{{ t('candidatePool.createdAt') }}</dt><dd>{{ formatDate(candidate.created_at) }}</dd></div>
          </dl>

          <div class="candidate-pool-card__actions">
            <RouterLink class="text-link" :to="`/candidate-pool/${candidate.id}`">{{ t('candidatePool.viewDetails') }}</RouterLink>
            <a v-if="candidate.has_resume" class="text-link" :href="getCandidateResumeUrl(candidate.id)" target="_blank" rel="noopener">{{ t('candidatePool.viewResume') }}</a>
            <span v-else class="muted-text">{{ t('candidatePool.resumeMissing') }}</span>
            <button class="danger-link" type="button" :disabled="deletingIds.includes(candidate.id)" @click="handleDelete(candidate)">
              {{ t(deletingIds.includes(candidate.id) ? 'candidatePool.deleting' : 'candidatePool.deleteCandidate') }}
            </button>
          </div>
        </article>
      </div>
    </article>
  </section>
</template>
