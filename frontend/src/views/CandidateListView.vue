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
function mustHaveItems(candidate) {
  return (matchResult(candidate)?.requirement_results || []).filter((item) => item.must_have)
}
function mustHaveState(candidate) {
  const summary = matchResult(candidate)?.must_have_summary
  if (!summary) return { label: t('common.match.waiting'), className: 'status-badge--neutral' }
  const items = mustHaveItems(candidate)
  const passed = items.filter((item) => item.status === 'matched').length
  const unmet = items.length - passed
  return {
    label: unmet
      ? t('candidates.mustHaveSummary.unmet', { passed, total: items.length, count: unmet })
      : t('candidates.mustHaveSummary.allMet', { passed, total: items.length }),
    className: summary.has_failure
      ? 'status-badge--error'
      : summary.needs_confirmation || unmet
        ? 'status-badge--warning'
        : 'status-badge--success',
  }
}
function matchSummary(candidate) {
  const status = session.jobMatchStatuses[candidate.id]
  if (status === 'loading') return t('common.match.scoring')
  if (status === 'error') return t('common.match.scoringFailed')
  return matchResult(candidate)?.summary || t('common.match.noResult')
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
function talentItems(candidate, mode) {
  const result = talentResult(candidate, mode)
  if (!result) return []
  return mode === 'specified'
    ? (result.specified_traits || []).map((item) => ({ name: item.trait, level: item.fit_level }))
    : (result.abilities || []).map((item) => ({ name: item.ability_name, level: item.level }))
}
function talentKeywords(candidate, mode) {
  return talentItems(candidate, mode)
    .slice(0, 2)
    .map((item) => `${item.name} ${talentLevelLabel(item.level)}`)
    .join(' · ')
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
          <div class="candidate-identity"><span class="candidate-avatar">{{ candidateName(candidate).slice(0, 1) }}</span><strong>{{ candidateName(candidate) }}</strong></div>
          <strong class="match-score match-score--table">{{ formattedScore(candidate) }}</strong>
          <div class="candidate-tooltip-cell" :tabindex="mustHaveItems(candidate).length ? 0 : undefined">
            <span class="status-badge" :class="mustHaveState(candidate).className">{{ mustHaveState(candidate).label }}</span>
            <div v-if="mustHaveItems(candidate).length" class="candidate-tooltip" role="tooltip">
              <span v-for="item in mustHaveItems(candidate)" :key="item.requirement_id" :class="item.status === 'matched' ? 'tooltip-item--met' : 'tooltip-item--unmet'">{{ item.status === 'matched' ? '✓' : '✕' }} {{ item.requirement_name }}</span>
            </div>
          </div>
          <div class="candidate-tooltip-cell candidate-assessment" :class="{ 'muted-text': !matchResult(candidate) }" :tabindex="matchResult(candidate)?.summary ? 0 : undefined">
            <p class="candidate-match-summary">{{ matchSummary(candidate) }}</p>
            <div v-if="matchResult(candidate)?.summary" class="candidate-tooltip candidate-tooltip--wide" role="tooltip">{{ matchResult(candidate).summary }}</div>
          </div>
          <div class="candidate-tooltip-cell talent-list-summary" :tabindex="talentItems(candidate, 'auto').length ? 0 : undefined">
            <strong>{{ talentLabel(candidate, 'auto') }}</strong>
            <small v-if="talentKeywords(candidate, 'auto')">{{ talentKeywords(candidate, 'auto') }}</small>
            <div v-if="talentItems(candidate, 'auto').length" class="candidate-tooltip" role="tooltip"><span v-for="item in talentItems(candidate, 'auto')" :key="item.name">{{ item.name }}：{{ talentLevelLabel(item.level) }}</span></div>
          </div>
          <div class="candidate-tooltip-cell talent-list-summary" :tabindex="talentItems(candidate, 'specified').length ? 0 : undefined">
            <strong>{{ talentLabel(candidate, 'specified') }}</strong>
            <small v-if="talentKeywords(candidate, 'specified')">{{ talentKeywords(candidate, 'specified') }}</small>
            <div v-if="talentItems(candidate, 'specified').length" class="candidate-tooltip" role="tooltip"><span v-for="item in talentItems(candidate, 'specified')" :key="item.name">{{ item.name }}：{{ talentLevelLabel(item.level) }}</span></div>
          </div>
          <div v-if="candidate.id" class="candidate-row__actions">
            <a class="text-link" :href="getCandidateResumeUrl(candidate.id)" target="_blank" rel="noopener">{{ t('candidates.actions.viewResume') }}</a>
            <RouterLink class="text-link" :to="`/candidates/${candidate.id}`">{{ t('candidates.actions.viewDetails') }}</RouterLink>
            <details class="candidate-more-actions">
              <summary :aria-label="t('candidates.actions.more')">…</summary>
              <div class="candidate-more-actions__menu">
                <button class="danger-link" type="button" :disabled="removingCandidateIds.includes(candidate.id)" @click="handleRemoveFromJob(candidate)">{{ t(removingCandidateIds.includes(candidate.id) ? 'candidates.removing' : 'candidates.removeFromJob') }}</button>
              </div>
            </details>
          </div>
        </article>
      </div>
    </article>
  </section>
</template>
