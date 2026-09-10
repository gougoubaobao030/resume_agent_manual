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
        <div><strong>当前候选人</strong><span>0 人</span></div>
        <span class="status-badge status-badge--neutral">当前会话</span>
      </div>
      <div class="candidate-table candidate-table--header" aria-hidden="true">
        <span>候选人</span><span>解析状态</span><span>岗位匹配</span><span>人工复核</span><span></span>
      </div>
      <div class="empty-state">
        <div class="empty-state__mark">CV</div>
        <h3>还没有候选人</h3>
        <p>完成简历导入后，解析成功的候选人会出现在这里。</p>
        <RouterLink class="text-link" to="/resumes">前往简历导入 →</RouterLink>
      </div>
    </article>
  </section>
</template>
