<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { session } from '../state/session'

const route = useRoute()
const candidate = computed(() =>
  session.candidates.find((item) => item.id === route.params.id),
)
const matchResult = computed(() => session.jobMatches[route.params.id])
const matchStatus = computed(() => session.jobMatchStatuses[route.params.id])

const mustHaveState = computed(() => {
  const summary = matchResult.value?.must_have_summary
  if (!summary) return { label: '等待评分', className: 'status-badge--neutral' }
  if (summary.has_failure) return { label: '硬条件不满足', className: 'status-badge--error' }
  if (summary.needs_confirmation) return { label: '硬条件需确认', className: 'status-badge--warning' }
  return { label: '硬条件满足', className: 'status-badge--success' }
})

const formattedScore = computed(() => {
  const score = matchResult.value?.score
  if (typeof score !== 'number') return '—'
  return Number.isInteger(score) ? String(score) : score.toFixed(1)
})

function display(value) {
  return value === null || value === undefined || value === '' ? '暂无信息' : value
}

function dateRange(item) {
  const values = [item.start_date, item.end_date].filter(Boolean)
  return values.length ? values.join(' – ') : '时间暂无信息'
}

function hasValues(object) {
  return object && Object.keys(object).length > 0
}

function customValue(value) {
  if (value === null || value === undefined || value === '') return '暂无信息'
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}
</script>

<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div>
        <RouterLink class="back-link" to="/candidates">← 返回候选人列表</RouterLink>
        <h2>{{ candidate?.basic_info?.name || '候选人详情' }}</h2>
        <p v-if="candidate">{{ candidate.extraction_metadata?.source_file || '来源文件名暂无信息' }}</p>
        <p v-else>当前会话中未找到这位候选人。</p>
      </div>
      <span class="status-badge" :class="mustHaveState.className">{{ mustHaveState.label }}</span>
    </div>

    <article v-if="!candidate" class="panel empty-state">
      <div class="empty-state__mark">CV</div>
      <h3>候选人数据不可用</h3>
      <p>数据仅保存在当前前端运行会话中，刷新页面后需要重新导入简历。</p>
      <RouterLink class="text-link" to="/candidates">返回候选人列表 →</RouterLink>
    </article>

    <div v-else class="detail-grid">
      <article class="panel detail-grid__main">
        <div class="panel__header"><h3>基本信息</h3></div>
        <div class="definition-grid">
          <div><span>姓名</span><strong>{{ display(candidate.basic_info?.name) }}</strong></div>
          <div><span>所在地</span><strong>{{ display(candidate.basic_info?.location) }}</strong></div>
          <div><span>邮箱</span><strong>{{ display(candidate.basic_info?.email) }}</strong></div>
          <div><span>电话</span><strong>{{ display(candidate.basic_info?.phone) }}</strong></div>
        </div>
      </article>
      <article class="panel detail-grid__side">
        <div class="panel__header"><h3>岗位匹配</h3></div>
        <div v-if="matchResult" class="match-overview match-overview--compact">
          <div>
            <span>岗位匹配分</span>
            <strong class="match-score">{{ formattedScore }}</strong>
          </div>
          <span class="status-badge" :class="mustHaveState.className">{{ mustHaveState.label }}</span>
          <p>{{ matchResult.summary || '后端未返回总体摘要。' }}</p>
          <RouterLink class="button button--secondary button--small" :to="`/analysis?candidate_id=${candidate.id}`">
            查看完整评分依据
          </RouterLink>
        </div>
        <div v-else class="pending-analysis">
          <span class="status-badge" :class="matchStatus === 'error' ? 'status-badge--error' : 'status-badge--neutral'">
            {{ matchStatus === 'loading' ? '评分中' : matchStatus === 'error' ? '评分失败' : '暂无评分' }}
          </span>
          <p>{{ session.jobMatchErrors[candidate.id] || '当前会话中没有这位候选人的岗位匹配结果。' }}</p>
        </div>
      </article>
      <article class="panel detail-grid__main resume-section">
        <div class="panel__header"><h3>教育经历</h3></div>
        <div v-if="candidate.education?.length" class="record-list">
          <div v-for="(item, index) in candidate.education" :key="index" class="record-item">
            <div class="record-item__heading">
              <strong>{{ display(item.school) }}</strong><span>{{ dateRange(item) }}</span>
            </div>
            <p>{{ [item.degree, item.major].filter(Boolean).join(' · ') || '学历及专业暂无信息' }}</p>
          </div>
        </div>
        <p v-else class="empty-copy">暂无教育信息</p>

        <div class="subsection-heading"><h3>工作经历</h3></div>
        <div v-if="candidate.work_experience?.length" class="record-list">
          <div v-for="(item, index) in candidate.work_experience" :key="index" class="record-item">
            <div class="record-item__heading">
              <strong>{{ [item.company, item.position].filter(Boolean).join(' · ') || '工作经历' }}</strong>
              <span>{{ dateRange(item) }}</span>
            </div>
            <p>{{ display(item.description) }}</p>
          </div>
        </div>
        <p v-else class="empty-copy">暂无工作经历</p>

        <div class="subsection-heading"><h3>项目经历</h3></div>
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
        <p v-else class="empty-copy">暂无项目经历</p>
      </article>

      <article class="panel detail-grid__side resume-section">
        <div class="panel__header"><h3>技能与语言</h3></div>
        <div class="detail-block">
          <strong>技能</strong>
          <div v-if="candidate.skills?.length" class="tag-list">
            <span v-for="skill in candidate.skills" :key="skill">{{ skill }}</span>
          </div>
          <p v-else class="empty-copy">暂无技能信息</p>
        </div>
        <div class="detail-block">
          <strong>语言能力</strong>
          <div v-if="candidate.languages?.length" class="tag-list">
            <span v-for="language in candidate.languages" :key="language">{{ language }}</span>
          </div>
          <p v-else class="empty-copy">暂无语言信息</p>
        </div>
        <div class="detail-block">
          <strong>证书</strong>
          <ul v-if="candidate.certifications?.length" class="plain-list">
            <li v-for="item in candidate.certifications" :key="item">{{ item }}</li>
          </ul>
          <p v-else class="empty-copy">暂无证书信息</p>
        </div>
        <div class="detail-block">
          <strong>成果</strong>
          <ul v-if="candidate.achievements?.length" class="plain-list">
            <li v-for="item in candidate.achievements" :key="item">{{ item }}</li>
          </ul>
          <p v-else class="empty-copy">暂无成果信息</p>
        </div>
      </article>

      <article class="panel detail-grid__main resume-section">
        <div class="panel__header"><h3>其他能力 / 事实证据</h3></div>
        <div v-if="candidate.candidate_evidence?.length" class="evidence-list">
          <div v-for="(item, index) in candidate.candidate_evidence" :key="index" class="evidence-item">
            <span v-if="item.category" class="status-badge status-badge--neutral">{{ item.category }}</span>
            <h4>{{ item.title || '事实证据' }}</h4>
            <p v-if="item.description">{{ item.description }}</p>
            <ul v-if="item.evidence?.length" class="plain-list">
              <li v-for="evidence in item.evidence" :key="evidence">{{ evidence }}</li>
            </ul>
          </div>
        </div>
        <p v-else class="empty-copy">暂无其他事实证据</p>
      </article>

      <article class="panel detail-grid__side resume-section">
        <div class="panel__header"><h3>解析信息</h3></div>
        <dl class="metadata-list">
          <div><dt>来源文件</dt><dd>{{ display(candidate.extraction_metadata?.source_file) }}</dd></div>
          <div><dt>解析工具</dt><dd>{{ display(candidate.extraction_metadata?.parser) }}</dd></div>
          <div v-if="candidate.extraction_metadata?.model"><dt>模型</dt><dd>{{ candidate.extraction_metadata.model }}</dd></div>
          <div v-if="candidate.extraction_metadata?.confidence !== null && candidate.extraction_metadata?.confidence !== undefined">
            <dt>提取置信度</dt><dd>{{ candidate.extraction_metadata.confidence }}</dd>
          </div>
        </dl>

        <div v-if="hasValues(candidate.custom_attributes)" class="detail-block">
          <strong>自定义字段</strong>
          <dl class="metadata-list">
            <div v-for="(value, key) in candidate.custom_attributes" :key="key">
              <dt>{{ key }}</dt><dd>{{ customValue(value) }}</dd>
            </div>
          </dl>
        </div>
        <p v-else class="empty-copy">暂无自定义字段</p>
      </article>

      <article class="panel detail-grid__full raw-text-panel">
        <details>
          <summary>查看简历原文</summary>
          <pre v-if="candidate.raw_text">{{ candidate.raw_text }}</pre>
          <p v-else class="empty-copy">暂无简历原文</p>
        </details>
      </article>
    </div>
  </section>
</template>
