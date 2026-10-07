<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import TalentSettings from '../components/TalentSettings.vue'
import {
  getCandidate,
  getCandidateResumeUrl,
  getFriendlyApiError,
  scoreJobMatch,
} from '../services/api'
import { analyzeTalent, talentLevelLabel } from '../services/talent'
import {
  session,
  setJobMatchError,
  setJobMatchLoading,
  setJobMatchResult,
} from '../state/session'

const route = useRoute()
const { locale, t } = useI18n()
const props = defineProps({ poolMode: { type: Boolean, default: false } })
const poolCandidate = ref(null)
const poolLoading = ref(false)
const poolLoadFailed = ref(false)
const rescoreMessage = ref('')
const rescoreStatus = ref('idle')
const showSpecifiedEditor = ref(false)
const candidate = computed(() =>
  poolCandidate.value || session.candidates.find((item) => item.id === route.params.id),
)
const matchResult = computed(() => session.jobMatches[route.params.id])
const matchStatus = computed(() => session.jobMatchStatuses[route.params.id])
const autoTalentResult = computed(() => session.talentResults[route.params.id]?.auto)
const specifiedTalentResult = computed(() => session.talentResults[route.params.id]?.specified)
const isRescoring = computed(() => matchStatus.value === 'loading')

const statusLabels = {
  matched: 'common.requirementStatus.matched',
  partially_matched: 'common.requirementStatus.partiallyMatched',
  not_matched: 'common.requirementStatus.notMatched',
  insufficient_evidence: 'common.requirementStatus.insufficientEvidence',
}

const confidenceLabels = {
  high: 'common.confidence.high',
  medium: 'common.confidence.medium',
  low: 'common.confidence.low',
}

const highlightedRequirements = computed(() => (matchResult.value?.requirement_results ?? [])
  .filter((item) => item.status === 'matched')
  .sort((a, b) => b.score - a.score)
  .slice(0, 3))

const riskRequirements = computed(() => (matchResult.value?.requirement_results ?? [])
  .filter((item) => item.status !== 'matched')
  .sort((a, b) => Number(b.must_have) - Number(a.must_have) || a.score - b.score)
  .slice(0, 3))

function evidenceSource(evidence) {
  const sourceKey = {
    projects: 'common.sources.projects',
    project: 'common.sources.projects',
    work_experience: 'common.sources.workExperience',
    education: 'common.sources.education',
    candidate_evidence: 'common.sources.candidateEvidence',
    skills: 'common.sources.skills',
    languages: 'common.sources.languages',
    certifications: 'common.sources.certifications',
    achievements: 'common.sources.achievements',
    raw_text: 'common.sources.rawText',
    mock_profile: 'common.sources.mockProfile',
  }[evidence.source_type]
  const source = sourceKey ? t(sourceKey) : evidence.source_type
  return source
    ? evidence.source_index == null ? source : t('common.sourceNameWithIndex', { source, index: evidence.source_index + 1 })
    : ''
}

const mustHaveState = computed(() => {
  const summary = matchResult.value?.must_have_summary
  if (!summary) return { label: t('common.match.waiting'), className: 'status-badge--neutral' }
  if (summary.has_failure) return { label: t('common.match.mustHaveFailed'), className: 'status-badge--error' }
  if (summary.needs_confirmation) return { label: t('common.match.mustHaveConfirmation'), className: 'status-badge--warning' }
  return { label: t('common.match.mustHavePassed'), className: 'status-badge--success' }
})

const formattedScore = computed(() => {
  const score = matchResult.value?.score
  if (typeof score !== 'number') return '—'
  return Number.isInteger(score) ? String(score) : score.toFixed(1)
})

function display(value) {
  return value === null || value === undefined || value === '' ? t('common.noInformation') : value
}

function dateRange(item) {
  const values = [item.start_date, item.end_date].filter(Boolean)
  return values.length ? values.join(' – ') : t('common.dateMissing')
}

function hasValues(object) {
  return object && Object.keys(object).length > 0
}

function customValue(value) {
  if (value === null || value === undefined || value === '') return t('common.noInformation')
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

function talentStatus(mode) {
  return session.talentStatuses[route.params.id]?.[mode] || 'idle'
}

function talentStatusLabel(mode) {
  const status = talentStatus(mode)
  return t(status === 'loading' ? 'common.talent.analyzing'
    : status === 'success' ? 'common.talent.completed'
      : status === 'error' ? 'common.talent.failed' : 'common.talent.notAnalyzed')
}

function talentStatusClass(mode) {
  const status = talentStatus(mode)
  return status === 'error' ? 'status-badge--error'
    : status === 'success' ? 'status-badge--success'
      : status === 'loading' ? 'status-badge--loading' : 'status-badge--neutral'
}

function canAnalyzeTalent(mode) {
  return candidate.value && talentStatus(mode) !== 'loading'
    && (mode !== 'specified' || session.desiredTraits.length > 0)
}

function handleAnalyzeTalent(mode) {
  void analyzeTalent(
    candidate.value,
    mode,
    [...session.desiredTraits],
    locale.value,
  )
}

function handleSpecifiedAnalysis() {
  handleAnalyzeTalent('specified')
  showSpecifiedEditor.value = false
}

async function handleRescore() {
  const candidateId = candidate.value?.id
  const jobId = session.currentJob?.id
  if (!candidateId || !jobId || isRescoring.value) return

  rescoreStatus.value = 'loading'
  rescoreMessage.value = t('candidateDetail.actions.rescoring')
  setJobMatchLoading(candidateId)
  try {
    const result = await scoreJobMatch(jobId, candidateId, locale.value)
    if (session.currentJob?.id === jobId) {
      setJobMatchResult(candidateId, result)
      rescoreStatus.value = 'success'
      rescoreMessage.value = t('candidateDetail.messages.rescoreSuccess')
    }
  } catch (error) {
    if (session.currentJob?.id === jobId) {
      const message = getFriendlyApiError(error, t('candidates.operations.rescore'))
      setJobMatchError(candidateId, message)
      rescoreStatus.value = 'error'
      rescoreMessage.value = message
    }
  }
}

function requirementStatus(status) {
  return statusLabels[status] ? t(statusLabels[status]) : status
}

function statusClass(status) {
  if (status === 'matched') return 'status-badge--success'
  if (status === 'not_matched') return 'status-badge--error'
  if (status === 'partially_matched' || status === 'insufficient_evidence') return 'status-badge--warning'
  return 'status-badge--neutral'
}

function confidenceLabel(confidence) {
  return confidenceLabels[confidence] ? t(confidenceLabels[confidence]) : confidence
}

function formatScore(score) {
  if (typeof score !== 'number') return '—'
  return Number.isInteger(score) ? String(score) : score.toFixed(1)
}

watch(
  () => route.params.id,
  async (candidateId) => {
    showSpecifiedEditor.value = false
    if (!props.poolMode) return
    poolCandidate.value = null
    poolLoadFailed.value = false
    poolLoading.value = true
    try {
      poolCandidate.value = await getCandidate(candidateId)
    } catch {
      poolLoadFailed.value = true
    } finally {
      poolLoading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <section class="page-stack candidate-detail-page">
    <div class="page-heading page-heading--split candidate-detail-heading">
      <div class="candidate-detail-heading__identity">
        <RouterLink class="back-link" :to="poolMode ? '/candidate-pool' : '/candidates'">{{ t(poolMode ? 'candidateDetail.backToPool' : 'candidateDetail.back') }}</RouterLink>
        <h2>{{ candidate?.basic_info?.name || t('candidateDetail.title') }}</h2>
        <div v-if="candidate" class="candidate-contact-line">
          <span>{{ display(candidate.basic_info?.location) }}</span>
          <span>{{ display(candidate.basic_info?.email) }}</span>
          <span>{{ display(candidate.basic_info?.phone) }}</span>
        </div>
        <p v-if="candidate && !poolMode" class="candidate-current-job">
          <span>{{ t('candidateDetail.currentJob') }}</span>
          <strong>{{ session.currentJob?.job_title || t('common.noInformation') }}</strong>
        </p>
        <p v-else-if="!candidate">{{ t(poolLoading ? 'common.loading' : 'candidateDetail.notFound') }}</p>
      </div>
      <div v-if="candidate" class="candidate-detail-heading__actions">
        <a class="button button--secondary button--small" :href="getCandidateResumeUrl(candidate.id)" target="_blank" rel="noopener">{{ t('candidateDetail.viewResume') }}</a>
        <button v-if="!poolMode" class="button button--primary button--small" type="button" :disabled="isRescoring || !session.currentJob?.id" @click="handleRescore">
          {{ t(isRescoring ? 'candidateDetail.actions.rescoring' : 'candidateDetail.actions.rescore') }}
        </button>
      </div>
    </div>

    <p v-if="rescoreMessage" class="inline-message" :class="`inline-message--${rescoreStatus}`" role="status" aria-live="polite">
      <span v-if="rescoreStatus === 'loading'" class="loading-spinner" aria-hidden="true"></span>{{ rescoreMessage }}
    </p>

    <article v-if="poolLoading" class="panel empty-state">
      <span class="loading-spinner" aria-hidden="true"></span>
      <p>{{ t('common.loading') }}</p>
    </article>

    <article v-else-if="!candidate || poolLoadFailed" class="panel empty-state">
      <div class="empty-state__mark">CV</div>
      <h3>{{ t('candidateDetail.empty.title') }}</h3>
      <p>{{ t('candidateDetail.empty.description') }}</p>
      <RouterLink class="text-link" :to="poolMode ? '/candidate-pool' : '/candidates'">{{ t(poolMode ? 'candidateDetail.empty.poolAction' : 'candidateDetail.empty.action') }}</RouterLink>
    </article>

    <div v-else-if="poolMode" class="detail-grid candidate-resume-grid">
      <article class="panel detail-grid__full compact-panel">
        <div class="panel__header"><h3>{{ t('candidateDetail.basicInfo.title') }}</h3></div>
        <div class="definition-grid">
          <div><span>{{ t('candidateDetail.basicInfo.name') }}</span><strong>{{ display(candidate.basic_info?.name) }}</strong></div>
          <div><span>{{ t('candidateDetail.basicInfo.location') }}</span><strong>{{ display(candidate.basic_info?.location) }}</strong></div>
          <div><span>{{ t('candidateDetail.basicInfo.email') }}</span><strong>{{ display(candidate.basic_info?.email) }}</strong></div>
          <div><span>{{ t('candidateDetail.basicInfo.phone') }}</span><strong>{{ display(candidate.basic_info?.phone) }}</strong></div>
        </div>
      </article>
    </div>

    <template v-else>
      <div class="candidate-metrics" aria-label="Decision summary">
        <article class="candidate-metric">
          <span>{{ t('candidateDetail.match.score') }}</span>
          <strong class="match-score">{{ formattedScore }}</strong>
        </article>
        <article class="candidate-metric">
          <span>{{ t('candidateDetail.metrics.mustHave') }}</span>
          <strong><span class="status-badge" :class="mustHaveState.className">{{ mustHaveState.label }}</span></strong>
        </article>
        <article class="candidate-metric">
          <span>{{ t('candidateDetail.metrics.autoTalent') }}</span>
          <strong>{{ autoTalentResult ? talentLevelLabel(autoTalentResult.attention_level) : talentStatusLabel('auto') }}</strong>
        </article>
        <article class="candidate-metric">
          <span>{{ t('candidateDetail.metrics.specifiedTalent') }}</span>
          <strong>{{ specifiedTalentResult ? talentLevelLabel(specifiedTalentResult.specified_fit_level) : talentStatusLabel('specified') }}</strong>
        </article>
      </div>

      <article class="panel compact-panel candidate-match-card">
        <div class="panel__header compact-panel__header">
          <div>
            <h3>{{ t('candidateDetail.match.title') }}</h3>
            <p v-if="matchResult">{{ matchResult.summary || t('common.match.noSummary') }}</p>
          </div>
        </div>

        <div v-if="matchResult" class="candidate-decision-columns">
          <section>
            <h4>{{ t('candidateDetail.match.highlights') }}</h4>
            <ul v-if="highlightedRequirements.length" class="compact-decision-list compact-decision-list--positive">
              <li v-for="item in highlightedRequirements" :key="item.requirement_id"><strong>{{ item.requirement_name }}</strong><span>{{ formatScore(item.score) }}</span></li>
            </ul>
            <p v-else class="empty-copy">{{ t('candidateDetail.match.noHighlights') }}</p>
          </section>
          <section>
            <h4>{{ t('candidateDetail.match.risks') }}</h4>
            <ul v-if="riskRequirements.length" class="compact-decision-list compact-decision-list--risk">
              <li v-for="item in riskRequirements" :key="item.requirement_id"><strong>{{ item.requirement_name }}</strong><span>{{ requirementStatus(item.status) }}</span></li>
            </ul>
            <p v-else class="empty-copy">{{ t('candidateDetail.match.noRisks') }}</p>
          </section>
        </div>

        <div v-else class="pending-analysis">
          <span class="status-badge" :class="matchStatus === 'error' ? 'status-badge--error' : 'status-badge--neutral'">
            {{ t(matchStatus === 'loading' ? 'common.match.scoringShort' : matchStatus === 'error' ? 'common.match.scoringFailed' : 'common.match.noScore') }}
          </span>
          <p>{{ session.jobMatchErrors[candidate.id] || t('candidateDetail.match.noResult') }}</p>
        </div>
      </article>

      <article v-if="matchResult" class="panel compact-panel candidate-requirements-card">
        <div class="panel__header compact-panel__header"><div><h3>{{ t('candidateDetail.match.requirements') }}</h3></div></div>
        <div class="compact-requirement-list">
          <details v-for="requirement in matchResult.requirement_results" :key="requirement.requirement_id" class="compact-disclosure">
            <summary>
              <span class="compact-disclosure__title">
                <strong>{{ requirement.requirement_name }}</strong>
                <span v-if="requirement.must_have" class="must-have-label">{{ t('analysis.mustHave') }}</span>
              </span>
              <span class="compact-disclosure__summary">{{ requirement.reason }}</span>
              <strong class="compact-disclosure__score">{{ formatScore(requirement.score) }}</strong>
              <span class="status-badge" :class="statusClass(requirement.status)">{{ requirementStatus(requirement.status) }}</span>
              <span class="disclosure-action">{{ t('candidateDetail.viewEvidence') }}</span>
            </summary>
            <div class="compact-disclosure__content">
              <p><strong>{{ t('analysis.reason') }}：</strong>{{ requirement.reason }}</p>
              <p class="requirement-confidence">{{ t('analysis.confidence', { value: confidenceLabel(requirement.confidence) }) }}</p>
              <div v-if="requirement.evidence?.length">
                <h5>{{ t('analysis.resumeEvidence') }}</h5>
                <ul class="plain-list"><li v-for="(evidence, index) in requirement.evidence" :key="index">{{ evidence.text }} <small>{{ evidenceSource(evidence) }}</small></li></ul>
              </div>
              <div v-if="requirement.missing_information?.length">
                <h5>{{ t('analysis.missingInformation') }}</h5>
                <ul class="plain-list"><li v-for="item in requirement.missing_information" :key="item">{{ item }}</li></ul>
              </div>
              <div v-if="requirement.needs_raw_review" class="requirement-raw-review"><strong>{{ t('analysis.rawReview.title') }}</strong><p v-if="requirement.raw_review_reason">{{ requirement.raw_review_reason }}</p></div>
            </div>
          </details>
        </div>
      </article>

      <div class="talent-summary-grid">
        <article class="panel compact-panel talent-summary-card">
          <div class="panel__header compact-panel__header">
            <div><h3>{{ t('candidateDetail.talent.autoTitle') }}</h3><p v-if="autoTalentResult">{{ autoTalentResult.summary }}</p></div>
            <span class="status-badge" :class="talentStatusClass('auto')">{{ talentStatusLabel('auto') }}</span>
          </div>
          <div v-if="autoTalentResult" class="compact-talent-list">
            <details v-for="item in autoTalentResult.abilities" :key="item.ability_name" class="compact-disclosure compact-disclosure--talent">
              <summary><strong>{{ item.ability_name }}</strong><span class="status-badge status-badge--neutral">{{ talentLevelLabel(item.level) }}</span><span class="disclosure-action">{{ t('candidateDetail.viewEvidence') }}</span></summary>
              <div class="compact-disclosure__content"><p>{{ item.reason }}</p><div v-if="item.evidence?.length"><h5>{{ t('candidateDetail.talent.evidence') }}</h5><ul class="plain-list"><li v-for="(evidence, index) in item.evidence" :key="index">{{ evidence.text }} <small>{{ evidenceSource(evidence) }}</small></li></ul></div></div>
            </details>
            <p v-if="!autoTalentResult.abilities.length" class="empty-copy">{{ t('candidateDetail.talent.noAbilities') }}</p>
            <details v-if="autoTalentResult.warnings?.length" class="talent-notes">
              <summary>{{ t('candidateDetail.talent.warnings') }}</summary>
              <ul class="plain-list"><li v-for="warning in autoTalentResult.warnings" :key="warning">{{ warning }}</li></ul>
            </details>
          </div>
          <p v-else-if="talentStatus('auto') === 'error'" class="talent-error">{{ session.talentErrors[candidate.id]?.auto }}</p>
          <p v-else class="empty-copy">{{ talentStatusLabel('auto') }}</p>
          <div class="talent-summary-card__footer"><button class="button button--secondary button--small" type="button" :disabled="!canAnalyzeTalent('auto')" @click="handleAnalyzeTalent('auto')">{{ t(talentStatus('auto') === 'loading' ? 'common.talent.analyzingProgress' : autoTalentResult ? 'common.talent.reanalyze' : 'common.talent.analyze') }}</button></div>
        </article>

        <article class="panel compact-panel talent-summary-card">
          <div class="panel__header compact-panel__header">
            <div><h3>{{ t('candidateDetail.talent.specifiedTitle') }}</h3><p v-if="specifiedTalentResult">{{ specifiedTalentResult.summary }}</p></div>
            <span class="status-badge" :class="talentStatusClass('specified')">{{ talentStatusLabel('specified') }}</span>
          </div>
          <div v-if="specifiedTalentResult" class="compact-talent-list">
            <details v-for="item in specifiedTalentResult.specified_traits" :key="item.trait" class="compact-disclosure compact-disclosure--talent">
              <summary><strong>{{ item.trait }}</strong><span class="status-badge status-badge--neutral">{{ talentLevelLabel(item.fit_level) }}</span><span class="disclosure-action">{{ t('candidateDetail.viewEvidence') }}</span></summary>
              <div class="compact-disclosure__content"><p>{{ item.reason }}</p><div v-if="item.evidence?.length"><h5>{{ t('candidateDetail.talent.evidence') }}</h5><ul class="plain-list"><li v-for="(evidence, index) in item.evidence" :key="index">{{ evidence.text }} <small>{{ evidenceSource(evidence) }}</small></li></ul></div><div v-if="item.missing_information?.length"><h5>{{ t('candidateDetail.talent.missingInformation') }}</h5><ul class="plain-list"><li v-for="info in item.missing_information" :key="info">{{ info }}</li></ul></div></div>
            </details>
            <details v-for="item in specifiedTalentResult.abilities" :key="item.ability_name" class="compact-disclosure compact-disclosure--talent">
              <summary><strong>{{ item.ability_name }}</strong><span class="status-badge status-badge--neutral">{{ talentLevelLabel(item.level) }}</span><span class="disclosure-action">{{ t('candidateDetail.viewEvidence') }}</span></summary>
              <div class="compact-disclosure__content"><p>{{ item.reason }}</p><div v-if="item.evidence?.length"><h5>{{ t('candidateDetail.talent.evidence') }}</h5><ul class="plain-list"><li v-for="(evidence, index) in item.evidence" :key="index">{{ evidence.text }} <small>{{ evidenceSource(evidence) }}</small></li></ul></div></div>
            </details>
            <p v-if="!specifiedTalentResult.specified_traits.length && !specifiedTalentResult.abilities.length" class="empty-copy">{{ t('candidateDetail.talent.noAbilities') }}</p>
            <details v-if="specifiedTalentResult.warnings?.length" class="talent-notes">
              <summary>{{ t('candidateDetail.talent.warnings') }}</summary>
              <ul class="plain-list"><li v-for="warning in specifiedTalentResult.warnings" :key="warning">{{ warning }}</li></ul>
            </details>
          </div>
          <p v-else-if="talentStatus('specified') === 'error'" class="talent-error">{{ session.talentErrors[candidate.id]?.specified }}</p>
          <p v-else class="empty-copy">{{ talentStatusLabel('specified') }}</p>
          <div v-if="showSpecifiedEditor" class="specified-trait-editor">
            <TalentSettings specified-only :disabled="talentStatus('specified') === 'loading'" />
            <div class="specified-trait-editor__actions">
              <button class="button button--secondary button--small" type="button" @click="showSpecifiedEditor = false">{{ t('candidateDetail.actions.cancel') }}</button>
              <button class="button button--primary button--small" type="button" :disabled="!canAnalyzeTalent('specified')" @click="handleSpecifiedAnalysis">{{ t('candidateDetail.actions.runSpecifiedAnalysis') }}</button>
            </div>
          </div>
          <div v-else class="talent-summary-card__footer"><button class="button button--secondary button--small" type="button" :disabled="talentStatus('specified') === 'loading'" @click="showSpecifiedEditor = true">{{ t(talentStatus('specified') === 'loading' ? 'common.talent.analyzingProgress' : specifiedTalentResult ? 'common.talent.reanalyze' : 'common.talent.analyze') }}</button></div>
        </article>
      </div>

    </template>

    <div v-if="candidate" class="detail-grid candidate-resume-grid">
      <article class="panel detail-grid__main resume-section">
        <div class="panel__header"><h3>{{ t('candidateDetail.resume.education') }}</h3></div>
        <div v-if="candidate.education?.length" class="record-list">
          <div v-for="(item, index) in candidate.education" :key="index" class="record-item">
            <div class="record-item__heading">
              <strong>{{ display(item.school) }}</strong><span>{{ dateRange(item) }}</span>
            </div>
            <p>{{ [item.degree, item.major].filter(Boolean).join(' · ') || t('candidateDetail.resume.degreeMissing') }}</p>
          </div>
        </div>
        <p v-else class="empty-copy">{{ t('candidateDetail.resume.noEducation') }}</p>

        <div class="subsection-heading"><h3>{{ t('candidateDetail.resume.workExperience') }}</h3></div>
        <div v-if="candidate.work_experience?.length" class="record-list">
          <div v-for="(item, index) in candidate.work_experience" :key="index" class="record-item">
            <div class="record-item__heading">
              <strong>{{ [item.company, item.position].filter(Boolean).join(' · ') || t('candidateDetail.resume.workExperience') }}</strong>
              <span>{{ dateRange(item) }}</span>
            </div>
            <p>{{ display(item.description) }}</p>
          </div>
        </div>
        <p v-else class="empty-copy">{{ t('candidateDetail.resume.noWorkExperience') }}</p>

        <div class="subsection-heading"><h3>{{ t('candidateDetail.resume.projects') }}</h3></div>
        <div v-if="candidate.projects?.length" class="record-list">
          <div v-for="(item, index) in candidate.projects" :key="index" class="record-item">
            <strong>{{ display(item.name) }}</strong>
            <p>{{ display(item.description) }}</p>
            <div v-if="item.technologies?.length" class="tag-list">
              <span v-for="technology in item.technologies" :key="technology">{{ technology }}</span>
            </div>
            <ul v-if="item.achievements?.length" class="plain-list">
              <li v-for="achievement in item.achievements" :key="achievement">{{ achievement }}</li>
            </ul>
          </div>
        </div>
        <p v-else class="empty-copy">{{ t('candidateDetail.resume.noProjects') }}</p>
      </article>

      <article class="panel detail-grid__side resume-section">
        <div class="panel__header"><h3>{{ t('candidateDetail.resume.skillsAndLanguages') }}</h3></div>
        <div class="detail-block">
          <strong>{{ t('candidateDetail.resume.skills') }}</strong>
          <div v-if="candidate.skills?.length" class="tag-list">
            <span v-for="skill in candidate.skills" :key="skill">{{ skill }}</span>
          </div>
          <p v-else class="empty-copy">{{ t('candidateDetail.resume.noSkills') }}</p>
        </div>
        <div class="detail-block">
          <strong>{{ t('candidateDetail.resume.languages') }}</strong>
          <div v-if="candidate.languages?.length" class="tag-list">
            <span v-for="language in candidate.languages" :key="language">{{ language }}</span>
          </div>
          <p v-else class="empty-copy">{{ t('candidateDetail.resume.noLanguages') }}</p>
        </div>
        <div class="detail-block">
          <strong>{{ t('candidateDetail.resume.certifications') }}</strong>
          <ul v-if="candidate.certifications?.length" class="plain-list">
            <li v-for="item in candidate.certifications" :key="item">{{ item }}</li>
          </ul>
          <p v-else class="empty-copy">{{ t('candidateDetail.resume.noCertifications') }}</p>
        </div>
        <div class="detail-block">
          <strong>{{ t('candidateDetail.resume.achievements') }}</strong>
          <ul v-if="candidate.achievements?.length" class="plain-list">
            <li v-for="item in candidate.achievements" :key="item">{{ item }}</li>
          </ul>
          <p v-else class="empty-copy">{{ t('candidateDetail.resume.noAchievements') }}</p>
        </div>
      </article>

      <article class="panel detail-grid__main resume-section">
        <div class="panel__header"><h3>{{ t('candidateDetail.evidence.title') }}</h3></div>
        <div v-if="candidate.candidate_evidence?.length" class="evidence-list">
          <div v-for="(item, index) in candidate.candidate_evidence" :key="index" class="evidence-item">
            <span v-if="item.category" class="status-badge status-badge--neutral">{{ item.category }}</span>
            <h4>{{ item.title || t('candidateDetail.evidence.defaultTitle') }}</h4>
            <p v-if="item.description">{{ item.description }}</p>
            <ul v-if="item.evidence?.length" class="plain-list">
              <li v-for="evidence in item.evidence" :key="evidence">{{ evidence }}</li>
            </ul>
          </div>
        </div>
        <p v-else class="empty-copy">{{ t('candidateDetail.evidence.empty') }}</p>
      </article>

      <article class="panel detail-grid__side resume-section">
        <div class="panel__header"><h3>{{ t('candidateDetail.metadata.title') }}</h3></div>
        <dl class="metadata-list">
          <div><dt>{{ t('candidateDetail.metadata.sourceFile') }}</dt><dd>{{ display(candidate.extraction_metadata?.source_file) }}</dd></div>
          <div><dt>{{ t('candidateDetail.metadata.parser') }}</dt><dd>{{ display(candidate.extraction_metadata?.parser) }}</dd></div>
          <div v-if="candidate.extraction_metadata?.model"><dt>{{ t('candidateDetail.metadata.model') }}</dt><dd>{{ candidate.extraction_metadata.model }}</dd></div>
          <div v-if="candidate.extraction_metadata?.confidence !== null && candidate.extraction_metadata?.confidence !== undefined">
            <dt>{{ t('candidateDetail.metadata.confidence') }}</dt><dd>{{ candidate.extraction_metadata.confidence }}</dd>
          </div>
        </dl>

        <div v-if="hasValues(candidate.custom_attributes)" class="detail-block">
          <strong>{{ t('candidateDetail.metadata.customFields') }}</strong>
          <dl class="metadata-list">
            <div v-for="(value, key) in candidate.custom_attributes" :key="key">
              <dt>{{ key }}</dt><dd>{{ customValue(value) }}</dd>
            </div>
          </dl>
        </div>
        <p v-else class="empty-copy">{{ t('candidateDetail.metadata.noCustomFields') }}</p>
      </article>

      <article class="panel detail-grid__full raw-text-panel">
        <details>
          <summary>{{ t('candidateDetail.rawText.title') }}</summary>
          <pre v-if="candidate.raw_text">{{ candidate.raw_text }}</pre>
          <p v-else class="empty-copy">{{ t('candidateDetail.rawText.empty') }}</p>
        </details>
      </article>
    </div>
  </section>
</template>
