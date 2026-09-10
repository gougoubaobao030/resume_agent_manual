<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div>
        <p class="eyebrow">RESUME IMPORT</p>
        <h2>批量导入候选人</h2>
        <p>选择当前岗位后，上传 1–30 份文本型 PDF 简历。</p>
      </div>
      <span class="status-badge status-badge--warning">请先完成 JD</span>
    </div>

    <article class="panel upload-panel">
      <div class="upload-zone">
        <div class="upload-zone__mark">PDF</div>
        <h3>拖放简历到此处</h3>
        <p>仅支持文本型 PDF，单次最多 30 份。扫描版 PDF 暂不支持。</p>
        <button class="button button--secondary" type="button" disabled>选择 PDF 文件</button>
      </div>
      <div class="upload-note">
        <strong>处理说明</strong>
        <span>每份简历独立解析；单份失败不会中断其他文件。</span>
      </div>
    </article>
  </section>
</template>
