<script setup>
import { computed, ref } from 'vue'
import { session } from '../state/session'
import TalentSettings from '../components/TalentSettings.vue'
import { analyzeTalent, talentLevelLabel } from '../services/talent'

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
  && selectedIds.value.some((id) => session.talentStatuses[id] !== 'loading'))

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
  void Promise.allSettled(selected.map((item) => analyzeTalent(item, mode, traits)))
}

function candidateName(candidate) { return candidate.basic_info?.name || '姓名未提取' }
function matchResult(candidate) { return session.jobMatches[candidate.id] }
function formattedScore(candidate) {
  const score = matchResult(candidate)?.score
  if (typeof score !== 'number') return '—'
  return Number.isInteger(score) ? String(score) : score.toFixed(1)
}
function mustHaveState(candidate) {
  const summary = matchResult(candidate)?.must_have_summary
  if (!summary) return { label: '等待评分', className: 'status-badge--neutral' }
  if (summary.has_failure) return { label: '硬条件不满足', className: 'status-badge--error' }
  if (summary.needs_confirmation) return { label: '硬条件需确认', className: 'status-badge--warning' }
  return { label: '硬条件满足', className: 'status-badge--success' }
}
function talentResult(candidate) { return session.talentResults[candidate.id] }
function talentStatus(candidate) { return session.talentStatuses[candidate.id] || 'idle' }
function talentLabel(candidate) {
  const result = talentResult(candidate)
  if (!result) {
    const status = talentStatus(candidate)
    return status === 'loading' ? '分析中' : status === 'error' ? '分析失败' : '未分析'
  }
  const label = result.mode === 'specified' ? '指定人才像符合度' : '人才关注度'
  return `${label}：${talentLevelLabel(result.mode === 'specified' ? result.specified_fit_level : result.attention_level)}`
}
</script>

<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div><p class="eyebrow">CANDIDATES</p><h2>候选人列表</h2><p>先查看岗位匹配，再选择值得进一步了解的人才。</p></div>
      <RouterLink class="button button--secondary" to="/resumes">导入简历</RouterLink>
    </div>
    <article class="panel panel--candidate-list">
      <div class="table-toolbar">
        <div><strong>当前候选人</strong><span>{{ session.candidates.length }} 人</span></div>
        <label class="sort-control">岗位匹配分
          <select v-model="sortDirection" class="select-input" aria-label="岗位匹配分排序"><option value="desc">从高到低</option><option value="asc">从低到高</option></select>
        </label>
      </div>
      <div v-if="session.candidates.length" class="talent-batch-controls">
        <TalentSettings />
        <div class="talent-batch-actions">
          <label><input type="checkbox" :checked="allSelected" @change="toggleAll" /> 全选当前候选人</label>
          <button class="button button--secondary button--small" type="button" :disabled="!selectedIds.length" @click="session.selectedTalentCandidateIds = []">取消选择</button>
          <span>已选 {{ selectedIds.length }} 人</span>
          <button class="button button--primary button--small" type="button" :disabled="!canAnalyze" @click="analyzeSelected">分析已选候选人能力</button>
        </div>
      </div>
      <div v-if="session.candidates.length" class="candidate-table candidate-table--header" aria-hidden="true">
        <span>选择</span><span>候选人</span><span>岗位匹配分</span><span>硬条件</span><span>岗位判断</span><span>人才能力</span><span></span>
      </div>
      <div v-if="!session.candidates.length" class="empty-state"><div class="empty-state__mark">CV</div><h3>还没有候选人</h3><p>完成简历导入后，解析成功的候选人会出现在这里。</p><RouterLink class="text-link" to="/resumes">前往简历导入 →</RouterLink></div>
      <div v-else class="candidate-rows">
        <article v-for="candidate in sortedCandidates" :key="candidate.id" class="candidate-row">
          <input type="checkbox" :checked="selectedIds.includes(candidate.id)" :aria-label="`选择 ${candidateName(candidate)}`" @change="toggleCandidate(candidate.id)" />
          <div class="candidate-identity"><span class="candidate-avatar">{{ candidateName(candidate).slice(0, 1) }}</span><div><strong>{{ candidateName(candidate) }}</strong><small>{{ candidate.basic_info?.location || '所在地暂无信息' }}</small></div></div>
          <strong class="match-score match-score--table">{{ formattedScore(candidate) }}</strong>
          <span class="status-badge" :class="mustHaveState(candidate).className">{{ mustHaveState(candidate).label }}</span>
          <p class="candidate-match-summary" :class="{ 'muted-text': !matchResult(candidate) }">{{ session.jobMatchStatuses[candidate.id] === 'loading' ? '评分中…' : session.jobMatchStatuses[candidate.id] === 'error' ? '评分失败' : matchResult(candidate)?.summary || '尚无岗位匹配结果' }}</p>
          <div class="talent-list-summary"><strong>{{ talentLabel(candidate) }}</strong><small v-if="talentResult(candidate)">能力亮点：{{ talentResult(candidate).abilities.slice(0, 3).map((item) => item.ability_name).join(' · ') || '暂无明确亮点' }}</small><small v-else-if="talentStatus(candidate) === 'error'" class="talent-error">{{ session.talentErrors[candidate.id] }}</small></div>
          <RouterLink v-if="candidate.id" class="text-link" :to="`/candidates/${candidate.id}`">查看详情</RouterLink>
        </article>
      </div>
    </article>
  </section>
</template>
