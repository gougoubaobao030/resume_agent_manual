import { createRouter, createWebHistory } from 'vue-router'

import AnalysisResultView from '../views/AnalysisResultView.vue'
import CandidateDetailView from '../views/CandidateDetailView.vue'
import CandidateListView from '../views/CandidateListView.vue'
import DashboardView from '../views/DashboardView.vue'
import JdManagementView from '../views/JdManagementView.vue'
import ResumeUploadView from '../views/ResumeUploadView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: DashboardView },
    { path: '/jobs', name: 'jobs', component: JdManagementView },
    { path: '/resumes', name: 'resumes', component: ResumeUploadView },
    { path: '/candidates', name: 'candidates', component: CandidateListView },
    {
      path: '/candidates/:id',
      name: 'candidate-detail',
      component: CandidateDetailView,
    },
    { path: '/analysis', name: 'analysis', component: AnalysisResultView },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

export default router
