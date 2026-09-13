<script setup>
import { session } from '../state/session'

function joinValues(values) {
  return values.filter(Boolean).join(' · ')
}

function educationSummary(candidate) {
  const education = candidate.education?.[0]
  if (!education) return '暂无教育信息'
  return joinValues([education.school, education.degree, education.major]) || '暂无教育信息'
}

function workSummary(candidate) {
  const work = candidate.work_experience?.[0]
  if (!work) return '暂无工作经历'
  return joinValues([work.company, work.position]) || '暂无工作经历'
}

function candidateName(candidate) {
  return candidate.basic_info?.name || '姓名未提取'
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
        <span>候选人</span><span>教育 / 经历</span><span>技能 / 语言</span><span>来源文件</span><span>分析</span><span></span>
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
          <div class="candidate-summary-cell">
            <strong>{{ educationSummary(candidate) }}</strong>
            <small>{{ workSummary(candidate) }}</small>
          </div>
          <div class="candidate-summary-cell">
            <strong>{{ candidate.skills?.slice(0, 4).join(' · ') || '暂无技能信息' }}</strong>
            <small>{{ candidate.languages?.join(' · ') || '暂无语言信息' }}</small>
          </div>
          <div class="candidate-summary-cell">
            <strong>{{ candidate.extraction_metadata?.source_file || '暂无来源文件名' }}</strong>
            <small>当前会话</small>
          </div>
          <span class="status-badge status-badge--neutral">待分析</span>
          <RouterLink v-if="candidate.id" class="text-link" :to="`/candidates/${candidate.id}`">查看详情</RouterLink>
          <span v-else class="muted-text">缺少 ID</span>
        </article>
      </div>
    </article>
  </section>
</template>
