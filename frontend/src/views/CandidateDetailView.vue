<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div>
        <RouterLink class="back-link" to="/candidates">← 返回候选人列表</RouterLink>
        <h2>候选人详情</h2>
        <p>选择候选人后展示其结构化简历信息。</p>
      </div>
      <span class="status-badge status-badge--neutral">等待选择</span>
    </div>

    <div class="detail-grid">
      <article class="panel detail-grid__main">
        <div class="panel__header"><h3>基本信息</h3></div>
        <div class="definition-grid">
          <div><span>姓名</span><strong>—</strong></div>
          <div><span>所在地</span><strong>—</strong></div>
          <div><span>邮箱</span><strong>—</strong></div>
          <div><span>电话</span><strong>—</strong></div>
        </div>
      </article>
      <article class="panel detail-grid__side">
        <div class="panel__header"><h3>分析状态</h3></div>
        <div class="pending-analysis">
          <span class="status-badge status-badge--neutral">待分析</span>
          <p>评分后端尚未完成，本区域暂不展示模拟结论。</p>
        </div>
      </article>
      <article class="panel detail-grid__main">
        <div class="panel__header"><h3>履历信息</h3></div>
        <div class="section-placeholder"><strong>教育经历</strong><span>暂无数据</span></div>
        <div class="section-placeholder"><strong>工作经历</strong><span>暂无数据</span></div>
        <div class="section-placeholder"><strong>项目经历</strong><span>暂无数据</span></div>
      </article>
      <article class="panel detail-grid__side">
        <div class="panel__header"><h3>技能与语言</h3></div>
        <div class="section-placeholder"><strong>技能</strong><span>暂无数据</span></div>
        <div class="section-placeholder"><strong>语言</strong><span>暂无数据</span></div>
      </article>
    </div>
  </section>
</template>
