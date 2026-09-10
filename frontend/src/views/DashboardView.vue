<script setup>
import { computed } from 'vue'

import { session } from '../state/session'

const hasCurrentJob = computed(() => Boolean(session.currentJob?.id))
</script>

<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div>
        <p class="eyebrow">Overview</p>
        <h2>开始本次候选人筛选</h2>
        <p>从岗位说明开始，依次完成 JD 确认、简历导入与候选人查看。</p>
      </div>
      <RouterLink class="button button--primary" to="/jobs">
        {{ hasCurrentJob ? '查看当前 JD' : '创建并解析 JD' }}
      </RouterLink>
    </div>

    <div class="workflow-card">
      <div class="workflow-card__header">
        <div>
          <span class="section-kicker">CORE FLOW</span>
          <h3>当前招聘流程</h3>
        </div>
        <span class="status-badge" :class="hasCurrentJob ? 'status-badge--success' : 'status-badge--neutral'">
          {{ hasCurrentJob ? 'JD 已确认' : '尚未开始' }}
        </span>
      </div>
      <ol class="workflow-steps">
        <li class="workflow-step workflow-step--current">
          <span>01</span>
          <div><strong>确认岗位要求</strong><small>输入并解析 JD，由 HR 修改确认</small></div>
        </li>
        <li class="workflow-step">
          <span>02</span>
          <div><strong>批量导入简历</strong><small>上传 1–30 份文本型 PDF</small></div>
        </li>
        <li class="workflow-step">
          <span>03</span>
          <div><strong>查看候选人</strong><small>检查结构化资料与解析结果</small></div>
        </li>
        <li class="workflow-step">
          <span>04</span>
          <div><strong>分析与人工复核</strong><small>评分模块尚在开发中</small></div>
        </li>
      </ol>
    </div>

    <div class="dashboard-grid">
      <article class="panel">
        <div class="panel__header">
          <div>
            <span class="section-kicker">CURRENT SESSION</span>
            <h3>本次处理</h3>
          </div>
        </div>
        <div class="session-summary">
          <div>
            <span>当前 JD</span>
            <strong>{{ session.currentJob?.job_title ?? '未设置' }}</strong>
            <small v-if="session.currentJob?.id">{{ session.currentJob.id }}</small>
          </div>
          <div><span>候选人</span><strong>0</strong></div>
          <div><span>待人工查看</span><strong>0</strong></div>
        </div>
        <p class="helper-text">这里只展示当前浏览器会话的数据，不生成虚假历史统计。</p>
      </article>

      <article class="panel">
        <div class="panel__header">
          <div>
            <span class="section-kicker">SYSTEM SCOPE</span>
            <h3>当前可用范围</h3>
          </div>
        </div>
        <ul class="capability-list">
          <li><span class="status-dot"></span>JD 解析与人工确认接口已具备</li>
          <li><span class="status-dot"></span>单份及批量简历解析接口已具备</li>
          <li><span class="status-dot status-dot--muted"></span>候选人评分暂未接入</li>
        </ul>
      </article>
    </div>
  </section>
</template>
