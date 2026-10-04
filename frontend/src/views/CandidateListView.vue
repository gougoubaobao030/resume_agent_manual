<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { session } from '../state/session'
import TalentSettings from '../components/TalentSettings.vue'
import { analyzeTalent, talentLevelLabel } from '../services/talent'

const { locale, t } = useI18n()
const sortDirection = ref('desc')
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
  && (session.talentMode !== 'specified' || session.desiredTraits.length > 0)
  && selectedIds.value.some((id) => session.talentStatuses[id]?.[session.talentMode] !== 'loading'))

function toggleAll() {
  session.selectedTalentCandidateIds = allSelected.value ? [] : sortedCandidates.value.map((item) => item.id)
}

function toggleCandidate(id) {
  session.selectedTalentCandidateIds = selectedIds.value.includes(id)
    ? selectedIds.value.filter((value) => value !== id)
    : [...selectedIds.value, id]
}

function analyzeSelected() {
  const mode = session.talentMode
  const traits = [...session.desiredTraits]
  const selected = sortedCandidates.value.filter((item) => selectedIds.value.includes(item.id))
  void Promise.allSettled(selected.map((item) => analyzeTalent(item, mode, traits, locale.value)))
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
function talentResult(candidate) { return session.talentResults[candidate.id]?.[session.talentMode] }
function talentStatus(candidate) { return session.talentStatuses[candidate.id]?.[session.talentMode] || 'idle' }
function talentLabel(candidate) {
  const result = talentResult(candidate)
  if (!result) {
    const status = talentStatus(candidate)
    return t(status === 'loading' ? 'common.talent.analyzing' : status === 'error' ? 'common.talent.failed' : 'common.talent.notAnalyzed')
  }
  const label = t(result.mode === 'specified' ? 'common.talent.specifiedFit' : 'common.talent.attention')
  return `${label}：${talentLevelLabel(result.mode === 'specified' ? result.specified_fit_level : result.attention_level)}`
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
        <TalentSettings />
        <div class="talent-batch-actions">
          <label><input type="checkbox" :checked="allSelected" @change="toggleAll" /> {{ t('candidates.selectAll') }}</label>
          <button class="button button--secondary button--small" type="button" :disabled="!selectedIds.length" @click="session.selectedTalentCandidateIds = []">{{ t('candidates.clearSelection') }}</button>
          <span>{{ t('candidates.selectedCount', { count: selectedIds.length }) }}</span>
          <button class="button button--primary button--small" type="button" :disabled="!canAnalyze" @click="analyzeSelected">{{ t('candidates.analyzeSelected') }}</button>
        </div>
      </div>
      <div v-if="session.candidates.length" class="candidate-table candidate-table--header" aria-hidden="true">
        <span>{{ t('candidates.table.select') }}</span><span>{{ t('candidates.table.candidate') }}</span><span>{{ t('candidates.table.matchScore') }}</span><span>{{ t('candidates.table.mustHave') }}</span><span>{{ t('candidates.table.assessment') }}</span><span>{{ t('candidates.table.talent') }}</span><span></span>
      </div>
      <div v-if="!session.candidates.length" class="empty-state"><div class="empty-state__mark">CV</div><h3>{{ t('candidates.empty.title') }}</h3><p>{{ t('candidates.empty.description') }}</p><RouterLink class="text-link" to="/resumes">{{ t('candidates.empty.action') }}</RouterLink></div>
      <div v-else class="candidate-rows">
        <article v-for="candidate in sortedCandidates" :key="candidate.id" class="candidate-row">
          <input type="checkbox" :checked="selectedIds.includes(candidate.id)" :aria-label="t('candidates.selectCandidate', { name: candidateName(candidate) })" @change="toggleCandidate(candidate.id)" />
          <div class="candidate-identity"><span class="candidate-avatar">{{ candidateName(candidate).slice(0, 1) }}</span><div><strong>{{ candidateName(candidate) }}</strong><small>{{ candidate.basic_info?.location || t('candidates.locationMissing') }}</small></div></div>
          <strong class="match-score match-score--table">{{ formattedScore(candidate) }}</strong>
          <span class="status-badge" :class="mustHaveState(candidate).className">{{ mustHaveState(candidate).label }}</span>
          <p class="candidate-match-summary" :class="{ 'muted-text': !matchResult(candidate) }">{{ session.jobMatchStatuses[candidate.id] === 'loading' ? t('common.match.scoring') : session.jobMatchStatuses[candidate.id] === 'error' ? t('common.match.scoringFailed') : matchResult(candidate)?.summary || t('common.match.noResult') }}</p>
          <div class="talent-list-summary"><strong>{{ talentLabel(candidate) }}</strong><small v-if="talentResult(candidate)">{{ t('candidates.highlights') }}{{ talentResult(candidate).abilities.slice(0, 3).map((item) => item.ability_name).join(' · ') || t('candidates.noHighlights') }}</small><small v-else-if="talentStatus(candidate) === 'error'" class="talent-error">{{ session.talentErrors[candidate.id]?.[session.talentMode] }}</small></div>
          <RouterLink v-if="candidate.id" class="text-link" :to="`/candidates/${candidate.id}`">{{ t('candidates.viewDetails') }}</RouterLink>
        </article>
      </div>
    </article>
  </section>
</template>
