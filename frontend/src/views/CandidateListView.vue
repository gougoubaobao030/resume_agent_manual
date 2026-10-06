<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getCandidateResumeUrl,
  getFriendlyApiError,
  removeCandidateFromJob,
  scoreJobMatch,
} from '../services/api'
import {
  removeCandidateFromCurrentJob,
  session,
  setJobMatchError,
  setJobMatchLoading,
  setJobMatchResult,
} from '../state/session'
import TalentSettings from '../components/TalentSettings.vue'
import { analyzeTalent, talentLevelLabel } from '../services/talent'

const { locale, t } = useI18n()
const sortDirection = ref('desc')
const selectedTalentModes = ref([])
const rescoringSelected = ref(false)
const rescoreStatus = ref('idle')
const rescoreMessage = ref('')
const removingCandidateIds = ref([])
const removeStatus = ref('idle')
const removeMessage = ref('')
const sortedCandidates = computed(() => [...session.candidates].sort((a, b) => {
  const first = session.jobMatches[a.id]?.score
  const second = session.jobMatches[b.id]?.score
  if (typeof first !== 'number') return typeof second === 'number' ? 1 : 0
  if (typeof second !== 'number') return -1
  return sortDirection.value === 'desc' ? second - first : first - second
}))
const selectedIds = computed(() => session.selectedTalentCandidateIds)
const allSelected = computed(() => sortedCandidates.value.length > 0
  && sortedCandidates.value.every((item) => selectedIds.value.includes(item.id)))
const canAnalyze = computed(() => selectedIds.value.length > 0
  && selectedTalentModes.value.length > 0
  && (!selectedTalentModes.value.includes('specified') || session.desiredTraits.length > 0)
  && selectedIds.value.some((id) => selectedTalentModes.value.some(
    (mode) => session.talentStatuses[id]?.[mode] !== 'loading',
  )))
const canRescore = computed(() => Boolean(session.currentJob?.id)
  && selectedIds.value.length > 0
  && !rescoringSelected.value)

function toggleAll() {
  session.selectedTalentCandidateIds = allSelected.value ? [] : sortedCandidates.value.map((item) => item.id)
}

function toggleCandidate(id) {
  session.selectedTalentCandidateIds = selectedIds.value.includes(id)
    ? selectedIds.value.filter((value) => value !== id)
    : [...selectedIds.value, id]
}

function analyzeSelected() {
  const modes = [...selectedTalentModes.value]
  const traits = [...session.desiredTraits]
  const selected = sortedCandidates.value.filter((item) => selectedIds.value.includes(item.id))
  void Promise.allSettled(selected.flatMap((item) =>
    modes.map((mode) => analyzeTalent(item, mode, traits, locale.value)),
  ))
}

async function rescoreSelected() {
  if (!canRescore.value) return

  const jobId = session.currentJob.id
  const candidateIds = [...selectedIds.value]
  const analysisLanguage = locale.value
  rescoringSelected.value = true
  rescoreStatus.value = 'loading'
  rescoreMessage.value = t('candidates.actions.rescoring')

  candidateIds.forEach((candidateId) => setJobMatchLoading(candidateId))

  try {
    const results = await Promise.allSettled(candidateIds.map(async (candidateId) => {
      try {
        const result = await scoreJobMatch(jobId, candidateId, analysisLanguage)
        if (session.currentJob?.id === jobId) setJobMatchResult(candidateId, result)
        return result
      } catch (error) {
        if (session.currentJob?.id === jobId) {
          setJobMatchError(
            candidateId,
            getFriendlyApiError(error, t('candidates.operations.rescore')),
          )
        }
        throw error
      }
    }))

    if (session.currentJob?.id !== jobId) {
      rescoreStatus.value = 'idle'
      rescoreMessage.value = ''
      return
    }

    const failedCount = results.filter((result) => result.status === 'rejected').length
    const successCount = results.length - failedCount
    if (!failedCount) {
      rescoreStatus.value = 'success'
      rescoreMessage.value = t('candidates.messages.rescoreSuccess')
    } else if (successCount) {
      rescoreStatus.value = 'error'
      rescoreMessage.value = t('candidates.messages.rescorePartialFailed', {
        success: successCount,
        failed: failedCount,
      })
    } else {
      rescoreStatus.value = 'error'
      rescoreMessage.value = t('candidates.messages.rescoreFailed', { failed: failedCount })
    }
  } finally {
    rescoringSelected.value = false
  }
}

async function handleRemoveFromJob(candidate) {
  const jobId = session.currentJob?.id
  if (!jobId || !window.confirm(t('candidates.removeConfirm', {
    name: candidateName(candidate),
  }))) return

  removingCandidateIds.value = [...removingCandidateIds.value, candidate.id]
  removeStatus.value = 'idle'
  removeMessage.value = ''
  try {
    await removeCandidateFromJob(candidate.id, jobId)
    if (session.currentJob?.id === jobId) {
      removeCandidateFromCurrentJob(candidate.id)
      removeStatus.value = 'success'
      removeMessage.value = t('candidates.messages.removeSuccess', {
        name: candidateName(candidate),
      })
    }
  } catch (error) {
    removeStatus.value = 'error'
    removeMessage.value = getFriendlyApiError(error, t('candidates.operations.remove'))
  } finally {
    removingCandidateIds.value = removingCandidateIds.value.filter(
      (id) => id !== candidate.id,
    )
  }
}

function candidateName(candidate) { return candidate.basic_info?.name || t('common.candidateNameMissing') }
function matchResult(candidate) { return session.jobMatches[candidate.id] }
function formattedScore(candidate) {
  const score = matchResult(candidate)?.score
  if (typeof score !== 'number') return '—'
  return Number.isInteger(score) ? String(score) : score.toFixed(1)
}
function mustHaveState(candidate) {
  const summary = matchResult(candidate)?.must_have_summary
  if (!summary) return { label: t('common.match.waiting'), className: 'status-badge--neutral' }
  if (summary.has_failure) return { label: t('common.match.mustHaveFailed'), className: 'status-badge--error' }
  if (summary.needs_confirmation) return { label: t('common.match.mustHaveConfirmation'), className: 'status-badge--warning' }
  return { label: t('common.match.mustHavePassed'), className: 'status-badge--success' }
}
function talentResult(candidate, mode) { return session.talentResults[candidate.id]?.[mode] }
function talentStatus(candidate, mode) { return session.talentStatuses[candidate.id]?.[mode] || 'idle' }
function talentLabel(candidate, mode) {
  const result = talentResult(candidate, mode)
  if (!result) {
    const status = talentStatus(candidate, mode)
    return t(status === 'loading' ? 'common.talent.analyzing' : status === 'error' ? 'common.talent.failed' : 'common.talent.notAnalyzed')
  }
  return talentLevelLabel(mode === 'specified' ? result.specified_fit_level : result.attention_level)
}
</script>

<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div><p class="eyebrow">{{ t('candidates.eyebrow') }}</p><h2>{{ t('candidates.title') }}</h2><p>{{ t('candidates.description') }}</p></div>
      <RouterLink class="button button--secondary" to="/resumes">{{ t('candidates.importResumes') }}</RouterLink>
    </div>
    <article class="panel panel--candidate-list">
      <div class="table-toolbar">
        <div><strong>{{ t('candidates.currentCandidates') }}</strong><span>{{ t('candidates.personCount', { count: session.candidates.length }) }}</span></div>
        <label class="sort-control">{{ t('candidates.matchScore') }}
          <select v-model="sortDirection" class="select-input" :aria-label="t('candidates.sortLabel')"><option value="desc">{{ t('candidates.sortDescending') }}</option><option value="asc">{{ t('candidates.sortAscending') }}</option></select>
        </label>
      </div>
      <div v-if="session.candidates.length" class="talent-batch-controls">
        <TalentSettings v-model="selectedTalentModes" multiple />
        <div class="talent-batch-actions">
          <label><input type="checkbox" :checked="allSelected" @change="toggleAll" /> {{ t('candidates.selectAll') }}</label>
          <button class="button button--secondary button--small" type="button" :disabled="!selectedIds.length" @click="session.selectedTalentCandidateIds = []">{{ t('candidates.clearSelection') }}</button>
          <span>{{ t('candidates.selectedCount', { count: selectedIds.length }) }}</span>
          <button class="button button--secondary button--small" type="button" :disabled="!canRescore" @click="rescoreSelected">{{ t(rescoringSelected ? 'candidates.actions.rescoring' : 'candidates.actions.rescoreSelected') }}</button>
          <button class="button button--primary button--small" type="button" :disabled="!canAnalyze" @click="analyzeSelected">{{ t('candidates.analyzeSelected') }}</button>
        </div>
        <p v-if="rescoreMessage" class="inline-message" :class="`inline-message--${rescoreStatus}`" role="status" aria-live="polite"><span v-if="rescoreStatus === 'loading'" class="loading-spinner" aria-hidden="true"></span>{{ rescoreMessage }}</p>
      </div>
      <p v-if="removeMessage" class="inline-message" :class="`inline-message--${removeStatus}`" role="status" aria-live="polite">{{ removeMessage }}</p>
      <div v-if="session.candidates.length" class="candidate-table candidate-table--header" aria-hidden="true">
        <span>{{ t('candidates.table.select') }}</span><span>{{ t('candidates.table.candidate') }}</span><span>{{ t('candidates.table.matchScore') }}</span><span>{{ t('candidates.table.mustHave') }}</span><span>{{ t('candidates.table.assessment') }}</span><span>{{ t('candidates.table.autoTalent') }}</span><span>{{ t('candidates.table.specifiedTalent') }}</span><span>{{ t('candidates.table.actions') }}</span>
      </div>
      <div v-if="!session.candidates.length" class="empty-state"><div class="empty-state__mark">CV</div><h3>{{ t('candidates.empty.title') }}</h3><p>{{ t('candidates.empty.description') }}</p><RouterLink class="text-link" to="/resumes">{{ t('candidates.empty.action') }}</RouterLink></div>
      <div v-else class="candidate-rows">
        <article v-for="candidate in sortedCandidates" :key="candidate.id" class="candidate-row">
          <input type="checkbox" :checked="selectedIds.includes(candidate.id)" :aria-label="t('candidates.selectCandidate', { name: candidateName(candidate) })" @change="toggleCandidate(candidate.id)" />
          <div class="candidate-identity"><span class="candidate-avatar">{{ candidateName(candidate).slice(0, 1) }}</span><div><strong>{{ candidateName(candidate) }}</strong><small>{{ candidate.basic_info?.location || t('candidates.locationMissing') }}</small></div></div>
          <strong class="match-score match-score--table">{{ formattedScore(candidate) }}</strong>
          <span class="status-badge" :class="mustHaveState(candidate).className">{{ mustHaveState(candidate).label }}</span>
          <p class="candidate-match-summary" :class="{ 'muted-text': !matchResult(candidate) }">{{ session.jobMatchStatuses[candidate.id] === 'loading' ? t('common.match.scoring') : session.jobMatchStatuses[candidate.id] === 'error' ? t('common.match.scoringFailed') : matchResult(candidate)?.summary || t('common.match.noResult') }}</p>
          <div class="talent-list-summary"><strong>{{ talentLabel(candidate, 'auto') }}</strong></div>
          <div class="talent-list-summary"><strong>{{ talentLabel(candidate, 'specified') }}</strong></div>
          <div v-if="candidate.id" class="candidate-row__actions">
            <a class="text-link" :href="getCandidateResumeUrl(candidate.id)" target="_blank" rel="noopener">{{ t('candidates.viewResume') }}</a>
            <span aria-hidden="true">|</span>
            <RouterLink class="text-link" :to="`/candidates/${candidate.id}`">{{ t('candidates.viewDetails') }}</RouterLink>
            <span aria-hidden="true">|</span>
            <button class="danger-link" type="button" :disabled="removingCandidateIds.includes(candidate.id)" @click="handleRemoveFromJob(candidate)">{{ t(removingCandidateIds.includes(candidate.id) ? 'candidates.removing' : 'candidates.removeFromJob') }}</button>
          </div>
        </article>
      </div>
    </article>
  </section>
</template>
