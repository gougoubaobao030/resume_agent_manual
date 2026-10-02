<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { session } from '../state/session'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const scoredCandidates = computed(() =>
  session.candidates.filter((candidate) => session.jobMatches[candidate.id]),
)

const selectedCandidate = computed(() => {
  const requestedId = route.query.candidate_id
  return scoredCandidates.value.find((candidate) => candidate.id === requestedId)
    || scoredCandidates.value[0]
    || null
})

const matchResult = computed(() =>
  selectedCandidate.value ? session.jobMatches[selectedCandidate.value.id] : null,
)

const candidateName = computed(() =>
  selectedCandidate.value?.basic_info?.name || t('common.candidateNameMissing'),
)

const mustHaveState = computed(() => {
  const summary = matchResult.value?.must_have_summary
  if (!summary) return { label: t('common.match.noAssessment'), className: 'status-badge--neutral' }
  if (summary.has_failure) return { label: t('common.match.mustHaveFailed'), className: 'status-badge--error' }
  if (summary.needs_confirmation) return { label: t('common.match.mustHaveConfirmation'), className: 'status-badge--warning' }
  return { label: t('common.match.mustHavePassed'), className: 'status-badge--success' }
})

const statusLabels = {
  matched: 'common.requirementStatus.matched',
  partially_matched: 'common.requirementStatus.partiallyMatched',
  not_matched: 'common.requirementStatus.notMatched',
  insufficient_evidence: 'common.requirementStatus.insufficientEvidence',
}

const confidenceLabels = { high: 'common.confidence.high', medium: 'common.confidence.medium', low: 'common.confidence.low' }

const sourceLabels = {
  work_experience: 'common.sources.workExperience',
  projects: 'common.sources.projects',
  project: 'common.sources.projects',
  education: 'common.sources.education',
  skills: 'common.sources.skills',
  languages: 'common.sources.languages',
  certifications: 'common.sources.certifications',
  achievements: 'common.sources.achievements',
  candidate_evidence: 'common.sources.candidateEvidence',
  raw_text: 'common.sources.rawText',
}

function formattedScore(score) {
  if (typeof score !== 'number') return '—'
  return Number.isInteger(score) ? String(score) : score.toFixed(1)
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

function evidenceSource(evidence) {
  if (!evidence.source_type && evidence.source_index === null) return ''
  if (!evidence.source_type && evidence.source_index === undefined) return ''
  const source = sourceLabels[evidence.source_type]
    ? t(sourceLabels[evidence.source_type])
    : evidence.source_type || t('common.sources.resume')
  return evidence.source_index === null || evidence.source_index === undefined
    ? t('common.sourceLabel', { source })
    : t('common.sourceWithIndex', { source, index: evidence.source_index + 1 })
}

function selectCandidate(event) {
  router.replace({ name: 'analysis', query: { candidate_id: event.target.value } })
}
</script>

<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div>
        <p class="eyebrow">{{ t('analysis.eyebrow') }}</p>
        <h2>{{ t('analysis.title') }}</h2>
        <p v-if="matchResult">{{ candidateName }} · {{ session.currentJob?.job_title || t('analysis.currentJob') }}</p>
        <p v-else>{{ t('analysis.description') }}</p>
      </div>
      <label v-if="scoredCandidates.length > 1" class="analysis-candidate-select">
        <span>{{ t('analysis.candidate') }}</span>
        <select :value="selectedCandidate?.id" class="select-input" @change="selectCandidate">
          <option v-for="candidate in scoredCandidates" :key="candidate.id" :value="candidate.id">
            {{ candidate.basic_info?.name || t('common.candidateNameMissing') }}
          </option>
        </select>
      </label>
    </div>

    <article v-if="!matchResult" class="panel empty-state">
      <div class="empty-state__mark">AI</div>
      <h3>{{ t('analysis.empty.title') }}</h3>
      <p>{{ t('analysis.empty.description') }}</p>
      <RouterLink class="text-link" to="/resumes">{{ t('analysis.empty.action') }}</RouterLink>
    </article>

    <template v-else>
      <article class="panel match-hero">
        <div class="match-hero__score">
          <span>{{ t('analysis.matchScore') }}</span>
          <strong>{{ formattedScore(matchResult.score) }}</strong>
          <small>/ 100</small>
        </div>
        <div class="match-hero__summary">
          <span class="status-badge" :class="mustHaveState.className">{{ mustHaveState.label }}</span>
          <h3>{{ t('analysis.overallAssessment') }}</h3>
          <p>{{ matchResult.summary || t('common.match.noSummary') }}</p>
          <div v-if="matchResult.needs_raw_review" class="raw-review-notice">
            <strong>{{ t('analysis.rawReview.title') }}</strong>
            <span>{{ t('analysis.rawReview.description') }}</span>
          </div>
        </div>
      </article>

      <div class="requirements-results">
        <article
          v-for="requirement in matchResult.requirement_results"
          :key="requirement.requirement_id"
          class="panel match-requirement"
        >
          <div class="match-requirement__header">
            <div>
              <div class="requirement-title-line">
                <h3>{{ requirement.requirement_name }}</h3>
                <span v-if="requirement.must_have" class="must-have-label">{{ t('analysis.mustHave') }}</span>
              </div>
              <span class="requirement-confidence">{{ t('analysis.confidence', { value: confidenceLabel(requirement.confidence) }) }}</span>
            </div>
            <div class="requirement-score-block">
              <strong>{{ formattedScore(requirement.score) }}</strong>
              <span class="status-badge" :class="statusClass(requirement.status)">
                {{ requirementStatus(requirement.status) }}
              </span>
            </div>
          </div>

          <div class="match-reason">
            <strong>{{ t('analysis.reason') }}</strong>
            <p>{{ requirement.reason }}</p>
          </div>

          <div v-if="requirement.evidence.length" class="match-section">
            <h4>{{ t('analysis.resumeEvidence') }}</h4>
            <div class="match-evidence-list">
              <div v-for="(evidence, index) in requirement.evidence" :key="index" class="match-evidence">
                <p>{{ evidence.text }}</p>
                <small v-if="evidenceSource(evidence)">{{ evidenceSource(evidence) }}</small>
              </div>
            </div>
          </div>

          <div v-if="requirement.missing_information.length" class="match-section confirmation-block">
            <h4>{{ t('analysis.missingInformation') }}</h4>
            <ul class="plain-list">
              <li v-for="item in requirement.missing_information" :key="item">{{ item }}</li>
            </ul>
          </div>

          <div v-if="requirement.needs_raw_review" class="requirement-raw-review">
            <strong>{{ t('analysis.rawReview.title') }}</strong>
            <p v-if="requirement.raw_review_reason">{{ requirement.raw_review_reason }}</p>
          </div>
        </article>
      </div>

      <article v-if="matchResult.missing_information.length" class="panel overall-confirmation">
        <div class="panel__header"><h3>{{ t('analysis.overallMissingInformation') }}</h3></div>
        <ul class="plain-list">
          <li v-for="item in matchResult.missing_information" :key="item">{{ item }}</li>
        </ul>
      </article>
    </template>
  </section>
</template>
