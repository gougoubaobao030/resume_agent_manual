<script setup>
import { computed } from 'vue'

import { session } from '../state/session'

const hasCurrentJob = computed(() => Boolean(session.currentJob?.id))
const scoredCandidateCount = computed(() => Object.keys(session.jobMatches).length)
</script>

<template>
  <section class="page-stack">
    <div class="page-heading page-heading--split">
      <div>
        <p class="eyebrow">{{ $t('dashboard.eyebrow') }}</p>
        <h2>{{ $t('dashboard.title') }}</h2>
        <p>{{ $t('dashboard.description') }}</p>
      </div>
      <RouterLink class="button button--primary" to="/jobs">
        {{ $t(hasCurrentJob ? 'dashboard.actions.viewJob' : 'dashboard.actions.createJob') }}
      </RouterLink>
    </div>

    <div class="workflow-card">
      <div class="workflow-card__header">
        <div>
          <span class="section-kicker">{{ $t('dashboard.flow.eyebrow') }}</span>
          <h3>{{ $t('dashboard.flow.title') }}</h3>
        </div>
        <span class="status-badge" :class="hasCurrentJob ? 'status-badge--success' : 'status-badge--neutral'">
          {{ $t(hasCurrentJob ? 'dashboard.flow.confirmed' : 'dashboard.flow.notStarted') }}
        </span>
      </div>
      <ol class="workflow-steps">
        <li class="workflow-step workflow-step--current">
          <span>01</span>
          <div><strong>{{ $t('dashboard.flow.steps.confirm.title') }}</strong><small>{{ $t('dashboard.flow.steps.confirm.description') }}</small></div>
        </li>
        <li class="workflow-step">
          <span>02</span>
          <div><strong>{{ $t('dashboard.flow.steps.import.title') }}</strong><small>{{ $t('dashboard.flow.steps.import.description') }}</small></div>
        </li>
        <li class="workflow-step">
          <span>03</span>
          <div><strong>{{ $t('dashboard.flow.steps.candidates.title') }}</strong><small>{{ $t('dashboard.flow.steps.candidates.description') }}</small></div>
        </li>
        <li class="workflow-step">
          <span>04</span>
          <div><strong>{{ $t('dashboard.flow.steps.review.title') }}</strong><small>{{ $t('dashboard.flow.steps.review.description') }}</small></div>
        </li>
      </ol>
    </div>

    <div class="dashboard-grid">
      <article class="panel">
        <div class="panel__header">
          <div>
            <span class="section-kicker">{{ $t('dashboard.session.eyebrow') }}</span>
            <h3>{{ $t('dashboard.session.title') }}</h3>
          </div>
        </div>
        <div class="session-summary">
          <div>
            <span>{{ $t('dashboard.session.currentJob') }}</span>
            <strong>{{ session.currentJob?.job_title ?? $t('dashboard.session.notSet') }}</strong>
            <small v-if="session.currentJob?.id">{{ session.currentJob.id }}</small>
          </div>
          <div><span>{{ $t('dashboard.session.candidates') }}</span><strong>{{ session.candidates.length }}</strong></div>
          <div><span>{{ $t('dashboard.session.scored') }}</span><strong>{{ scoredCandidateCount }} / {{ session.candidates.length }}</strong></div>
        </div>
        <p class="helper-text">{{ $t('dashboard.session.note') }}</p>
      </article>

      <article class="panel">
        <div class="panel__header">
          <div>
            <span class="section-kicker">{{ $t('dashboard.scope.eyebrow') }}</span>
            <h3>{{ $t('dashboard.scope.title') }}</h3>
          </div>
        </div>
        <ul class="capability-list">
          <li><span class="status-dot"></span>{{ $t('dashboard.scope.jd') }}</li>
          <li><span class="status-dot"></span>{{ $t('dashboard.scope.resume') }}</li>
          <li><span class="status-dot"></span>{{ $t('dashboard.scope.scoring') }}</li>
        </ul>
      </article>
    </div>
  </section>
</template>
