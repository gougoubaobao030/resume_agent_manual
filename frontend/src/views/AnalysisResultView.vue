<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { session } from '../state/session'

const route = useRoute()
const router = useRouter()

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
  selectedCandidate.value?.basic_info?.name || '姓名未提取',
)

const mustHaveState = computed(() => {
  const summary = matchResult.value?.must_have_summary
  if (!summary) return { label: '暂无判断', className: 'status-badge--neutral' }
  if (summary.has_failure) return { label: '硬条件不满足', className: 'status-badge--error' }
  if (summary.needs_confirmation) return { label: '硬条件需确认', className: 'status-badge--warning' }
  return { label: '硬条件满足', className: 'status-badge--success' }
})

const statusLabels = {
  matched: '满足',
  partially_matched: '部分满足',
  not_matched: '不满足',
  insufficient_evidence: '证据不足',
}

const confidenceLabels = { high: '高', medium: '中', low: '低' }

const sourceLabels = {
  work_experience: '工作经历',
  projects: '项目经历',
  project: '项目经历',
  education: '教育经历',
  skills: '技能',
  languages: '语言能力',
  certifications: '证书',
  achievements: '成果',
  candidate_evidence: '事实证据',
  raw_text: '简历原文',
}

function formattedScore(score) {
  if (typeof score !== 'number') return '—'
  return Number.isInteger(score) ? String(score) : score.toFixed(1)
}

function requirementStatus(status) {
  return statusLabels[status] || status
}

function statusClass(status) {
  if (status === 'matched') return 'status-badge--success'
  if (status === 'not_matched') return 'status-badge--error'
  if (status === 'partially_matched' || status === 'insufficient_evidence') return 'status-badge--warning'
  return 'status-badge--neutral'
}

function confidenceLabel(confidence) {
  return confidenceLabels[confidence] || confidence
}

function evidenceSource(evidence) {
  if (!evidence.source_type && evidence.source_index === null) return ''
  if (!evidence.source_type && evidence.source_index === undefined) return ''
  const source = sourceLabels[evidence.source_type] || evidence.source_type || '简历'
  return evidence.source_index === null || evidence.source_index === undefined
    ? `来源：${source}`
    : `来源：${source} #${evidence.source_index + 1}`
}

function selectCandidate(event) {
  router.replace({ name: 'analysis', query: { candidate_id: event.target.value } })
}
</script>

<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div>
        <p class="eyebrow">JOB MATCH</p>
        <h2>岗位匹配分析</h2>
        <p v-if="matchResult">{{ candidateName }} · {{ session.currentJob?.job_title || '当前岗位' }}</p>
        <p v-else>展示当前会话中后端已完成的真实岗位匹配结果。</p>
      </div>
      <label v-if="scoredCandidates.length > 1" class="analysis-candidate-select">
        <span>候选人</span>
        <select :value="selectedCandidate?.id" class="select-input" @change="selectCandidate">
          <option v-for="candidate in scoredCandidates" :key="candidate.id" :value="candidate.id">
            {{ candidate.basic_info?.name || '姓名未提取' }}
          </option>
        </select>
      </label>
    </div>

    <article v-if="!matchResult" class="panel empty-state">
      <div class="empty-state__mark">AI</div>
      <h3>暂无岗位匹配结果</h3>
      <p>请先保存 JD 并导入简历，系统会调用现有岗位匹配接口。</p>
      <RouterLink class="text-link" to="/resumes">前往简历导入 →</RouterLink>
    </article>

    <template v-else>
      <article class="panel match-hero">
        <div class="match-hero__score">
          <span>岗位匹配分</span>
          <strong>{{ formattedScore(matchResult.score) }}</strong>
          <small>/ 100</small>
        </div>
        <div class="match-hero__summary">
          <span class="status-badge" :class="mustHaveState.className">{{ mustHaveState.label }}</span>
          <h3>总体判断</h3>
          <p>{{ matchResult.summary || '后端未返回总体摘要。' }}</p>
          <div v-if="matchResult.needs_raw_review" class="raw-review-notice">
            <strong>建议回查原始简历</strong>
            <span>部分要求需要结合原始简历进一步确认。</span>
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
                <span v-if="requirement.must_have" class="must-have-label">硬性条件</span>
              </div>
              <span class="requirement-confidence">判断可信度：{{ confidenceLabel(requirement.confidence) }}</span>
            </div>
            <div class="requirement-score-block">
              <strong>{{ formattedScore(requirement.score) }}</strong>
              <span class="status-badge" :class="statusClass(requirement.status)">
                {{ requirementStatus(requirement.status) }}
              </span>
            </div>
          </div>

          <div class="match-reason">
            <strong>判断理由</strong>
            <p>{{ requirement.reason }}</p>
          </div>

          <div v-if="requirement.evidence.length" class="match-section">
            <h4>简历证据</h4>
            <div class="match-evidence-list">
              <div v-for="(evidence, index) in requirement.evidence" :key="index" class="match-evidence">
                <p>{{ evidence.text }}</p>
                <small v-if="evidenceSource(evidence)">{{ evidenceSource(evidence) }}</small>
              </div>
            </div>
          </div>

          <div v-if="requirement.missing_information.length" class="match-section confirmation-block">
            <h4>待确认信息</h4>
            <ul class="plain-list">
              <li v-for="item in requirement.missing_information" :key="item">{{ item }}</li>
            </ul>
          </div>

          <div v-if="requirement.needs_raw_review" class="requirement-raw-review">
            <strong>建议回查原始简历</strong>
            <p v-if="requirement.raw_review_reason">{{ requirement.raw_review_reason }}</p>
          </div>
        </article>
      </div>

      <article v-if="matchResult.missing_information.length" class="panel overall-confirmation">
        <div class="panel__header"><h3>整体待确认信息</h3></div>
        <ul class="plain-list">
          <li v-for="item in matchResult.missing_information" :key="item">{{ item }}</li>
        </ul>
      </article>
    </template>
  </section>
</template>
