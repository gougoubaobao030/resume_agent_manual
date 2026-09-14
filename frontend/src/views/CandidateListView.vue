<script setup>
import { session } from '../state/session'

function candidateName(candidate) {
  return candidate.basic_info?.name || '姓名未提取'
}

function matchResult(candidate) {
  return session.jobMatches[candidate.id]
}

function formattedScore(candidate) {
  const score = matchResult(candidate)?.score
  if (typeof score !== 'number') return '—'
  return Number.isInteger(score) ? String(score) : score.toFixed(1)
}

function mustHaveState(candidate) {
  const summary = matchResult(candidate)?.must_have_summary

  if (!summary) {
    return { label: '等待评分', className: 'status-badge--neutral' }
  }
  if (summary.has_failure) {
    return { label: '硬条件不满足', className: 'status-badge--error' }
  }
  if (summary.needs_confirmation) {
    return { label: '硬条件需确认', className: 'status-badge--warning' }
  }
  return { label: '硬条件满足', className: 'status-badge--success' }
}

function analysisLabel(candidate) {
  const status = session.jobMatchStatuses[candidate.id]
  if (status === 'loading') return '评分中…'
  if (status === 'error') return '评分失败'
  return matchResult(candidate)?.summary || '尚无岗位匹配结果'
}
</script>

<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div>
        <p class="eyebrow">CANDIDATES</p>
        <h2>候选人列表</h2>
        <p>展示当前会话中成功解析的候选人，不保存历史数据。</p>
      </div>
      <RouterLink class="button button--secondary" to="/resumes">导入简历</RouterLink>
    </div>

    <article class="panel">
      <div class="table-toolbar">
        <div><strong>当前候选人</strong><span>{{ session.candidates.length }} 人</span></div>
        <span class="status-badge status-badge--neutral">当前会话</span>
      </div>
      <div v-if="session.candidates.length" class="candidate-table candidate-table--header" aria-hidden="true">
        <span>候选人</span><span>岗位匹配分</span><span>硬条件</span><span>判断摘要</span><span></span>
      </div>
      <div v-if="!session.candidates.length" class="empty-state">
        <div class="empty-state__mark">CV</div>
        <h3>还没有候选人</h3>
        <p>完成简历导入后，解析成功的候选人会出现在这里。</p>
        <RouterLink class="text-link" to="/resumes">前往简历导入 →</RouterLink>
      </div>

      <div v-else class="candidate-rows">
        <article v-for="candidate in session.candidates" :key="candidate.id" class="candidate-row">
          <div class="candidate-identity">
            <span class="candidate-avatar">{{ candidateName(candidate).slice(0, 1) }}</span>
            <div>
              <strong>{{ candidateName(candidate) }}</strong>
              <small>{{ candidate.basic_info?.location || '所在地暂无信息' }}</small>
            </div>
          </div>
          <strong class="match-score match-score--table">{{ formattedScore(candidate) }}</strong>
          <span class="status-badge" :class="mustHaveState(candidate).className">
            {{ mustHaveState(candidate).label }}
          </span>
          <p class="candidate-match-summary" :class="{ 'muted-text': !matchResult(candidate) }">
            {{ analysisLabel(candidate) }}
          </p>
          <RouterLink v-if="candidate.id" class="text-link" :to="`/candidates/${candidate.id}`">查看详情</RouterLink>
          <span v-else class="muted-text">缺少 ID</span>
        </article>
      </div>
    </article>
  </section>
</template>
