<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { session } from '../state/session'
import TalentSettings from '../components/TalentSettings.vue'
import { analyzeTalent, talentLevelLabel } from '../services/talent'

const route = useRoute()
const { locale, t } = useI18n()
const candidate = computed(() =>
  session.candidates.find((item) => item.id === route.params.id),
)
const matchResult = computed(() => session.jobMatches[route.params.id])
const matchStatus = computed(() => session.jobMatchStatuses[route.params.id])
const talentResult = computed(() => session.talentResults[route.params.id]?.[session.talentMode])
const talentStatus = computed(() => session.talentStatuses[route.params.id]?.[session.talentMode] || 'idle')
const canAnalyzeTalent = computed(() => candidate.value && talentStatus.value !== 'loading'
  && (session.talentMode !== 'specified' || session.desiredTraits.length > 0))

function evidenceSource(evidence) {
  const sourceKey = { projects: 'common.sources.projects', work_experience: 'common.sources.workExperience', candidate_evidence: 'common.sources.candidateEvidence', skills: 'common.sources.skills', mock_profile: 'common.sources.mockProfile' }[evidence.source_type]
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

function handleAnalyzeTalent() {
  void analyzeTalent(
    candidate.value,
    session.talentMode,
    [...session.desiredTraits],
    locale.value,
  )
}
</script>

<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div>
        <RouterLink class="back-link" to="/candidates">{{ t('candidateDetail.back') }}</RouterLink>
        <h2>{{ candidate?.basic_info?.name || t('candidateDetail.title') }}</h2>
        <p v-if="candidate">{{ candidate.extraction_metadata?.source_file || t('candidateDetail.sourceFileMissing') }}</p>
        <p v-else>{{ t('candidateDetail.notFound') }}</p>
      </div>
      <span class="status-badge" :class="mustHaveState.className">{{ mustHaveState.label }}</span>
    </div>

    <article v-if="!candidate" class="panel empty-state">
      <div class="empty-state__mark">CV</div>
      <h3>{{ t('candidateDetail.empty.title') }}</h3>
      <p>{{ t('candidateDetail.empty.description') }}</p>
      <RouterLink class="text-link" to="/candidates">{{ t('candidateDetail.empty.action') }}</RouterLink>
    </article>

    <div v-else class="detail-grid">
      <article class="panel detail-grid__main">
        <div class="panel__header"><h3>{{ t('candidateDetail.basicInfo.title') }}</h3></div>
        <div class="definition-grid">
          <div><span>{{ t('candidateDetail.basicInfo.name') }}</span><strong>{{ display(candidate.basic_info?.name) }}</strong></div>
          <div><span>{{ t('candidateDetail.basicInfo.location') }}</span><strong>{{ display(candidate.basic_info?.location) }}</strong></div>
          <div><span>{{ t('candidateDetail.basicInfo.email') }}</span><strong>{{ display(candidate.basic_info?.email) }}</strong></div>
          <div><span>{{ t('candidateDetail.basicInfo.phone') }}</span><strong>{{ display(candidate.basic_info?.phone) }}</strong></div>
        </div>
      </article>
      <article class="panel detail-grid__side">
        <div class="panel__header"><h3>{{ t('candidateDetail.match.title') }}</h3></div>
        <div v-if="matchResult" class="match-overview match-overview--compact">
          <div>
            <span>{{ t('candidateDetail.match.score') }}</span>
            <strong class="match-score">{{ formattedScore }}</strong>
          </div>
          <span class="status-badge" :class="mustHaveState.className">{{ mustHaveState.label }}</span>
          <p>{{ matchResult.summary || t('common.match.noSummary') }}</p>
          <RouterLink class="button button--secondary button--small" :to="`/analysis?candidate_id=${candidate.id}`">
            {{ t('candidateDetail.match.viewDetails') }}
          </RouterLink>
        </div>
        <div v-else class="pending-analysis">
          <span class="status-badge" :class="matchStatus === 'error' ? 'status-badge--error' : 'status-badge--neutral'">
            {{ t(matchStatus === 'loading' ? 'common.match.scoringShort' : matchStatus === 'error' ? 'common.match.scoringFailed' : 'common.match.noScore') }}
          </span>
          <p>{{ session.jobMatchErrors[candidate.id] || t('candidateDetail.match.noResult') }}</p>
        </div>
      </article>
      <article class="panel detail-grid__full talent-detail">
        <div class="panel__header"><h3>{{ t('candidateDetail.talent.title') }}</h3><span class="status-badge" :class="talentStatus === 'error' ? 'status-badge--error' : talentStatus === 'success' ? 'status-badge--success' : talentStatus === 'loading' ? 'status-badge--loading' : 'status-badge--neutral'">{{ t(talentStatus === 'loading' ? 'common.talent.analyzing' : talentStatus === 'success' ? 'common.talent.completed' : talentStatus === 'error' ? 'common.talent.failed' : 'common.talent.notAnalyzed') }}</span></div>
        <div class="talent-detail__controls"><TalentSettings /><button class="button button--primary button--small" type="button" :disabled="!canAnalyzeTalent" @click="handleAnalyzeTalent">{{ t(talentStatus === 'loading' ? 'common.talent.analyzingProgress' : talentResult ? 'common.talent.reanalyze' : 'common.talent.analyze') }}</button></div>
        <p v-if="talentStatus === 'error'" class="talent-error">{{ session.talentErrors[candidate.id]?.[session.talentMode] }}</p>
        <div v-if="talentResult" class="talent-detail__result">
          <div class="talent-detail__overview"><strong>{{ t(talentResult.mode === 'specified' ? 'common.talent.specifiedFit' : 'common.talent.attention') }}{{ t('common.colon') }}{{ talentLevelLabel(talentResult.mode === 'specified' ? talentResult.specified_fit_level : talentResult.attention_level) }}</strong><p>{{ talentResult.summary }}</p></div>
          <section v-if="talentResult.mode === 'specified'" class="talent-detail__section">
            <h4>{{ t('candidateDetail.talent.specifiedProfile') }}</h4>
            <div v-for="item in talentResult.specified_traits" :key="item.trait" class="talent-finding">
              <div class="talent-finding__heading"><strong>{{ item.trait }}</strong><span class="status-badge status-badge--neutral">{{ talentLevelLabel(item.fit_level) }}</span></div>
              <p>{{ item.reason }}</p>
              <div v-if="item.evidence.length"><b>{{ t('candidateDetail.talent.evidence') }}</b><ul class="plain-list"><li v-for="(evidence, index) in item.evidence" :key="index">{{ evidence.text }} <small>{{ evidenceSource(evidence) }}</small></li></ul></div>
              <div v-if="item.missing_information.length"><b>{{ t('candidateDetail.talent.missingInformation') }}</b><ul class="plain-list"><li v-for="info in item.missing_information" :key="info">{{ info }}</li></ul></div>
            </div>
          </section>
          <section class="talent-detail__section"><h4>{{ t(talentResult.mode === 'specified' ? 'candidateDetail.talent.additionalFindings' : 'candidateDetail.talent.abilityProfile') }}</h4>
            <div v-for="item in talentResult.abilities" :key="item.ability_name" class="talent-finding">
              <div class="talent-finding__heading"><strong>{{ item.ability_name }}</strong><span class="status-badge status-badge--neutral">{{ talentLevelLabel(item.level) }}</span></div>
              <p>{{ item.reason }}</p>
              <div v-if="item.evidence.length"><b>{{ t('candidateDetail.talent.evidence') }}</b><ul class="plain-list"><li v-for="(evidence, index) in item.evidence" :key="index">{{ evidence.text }} <small>{{ evidenceSource(evidence) }}</small></li></ul></div>
            </div>
            <p v-if="!talentResult.abilities.length" class="empty-copy">{{ t('candidateDetail.talent.noAbilities') }}</p>
          </section>
          <section v-if="talentResult.warnings.length" class="talent-detail__section"><h4>{{ t('candidateDetail.talent.warnings') }}</h4><ul class="plain-list"><li v-for="warning in talentResult.warnings" :key="warning">{{ warning }}</li></ul></section>
        </div>
      </article>
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
