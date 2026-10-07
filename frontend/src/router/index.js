import { createRouter, createWebHistory } from 'vue-router'

import CandidateDetailView from '../views/CandidateDetailView.vue'
import CandidateListView from '../views/CandidateListView.vue'
import CandidatePoolView from '../views/CandidatePoolView.vue'
import DashboardView from '../views/DashboardView.vue'
import JdManagementView from '../views/JdManagementView.vue'
import LoginView from '../views/LoginView.vue'
import ResumeUploadView from '../views/ResumeUploadView.vue'
import { auth, initializeAuth } from '../state/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
    { path: '/', name: 'dashboard', component: DashboardView },
    { path: '/jobs', name: 'jobs', component: JdManagementView },
    { path: '/resumes', name: 'resumes', component: ResumeUploadView },
    { path: '/candidates', name: 'candidates', component: CandidateListView },
    { path: '/candidate-pool', name: 'candidate-pool', component: CandidatePoolView },
    {
      path: '/candidate-pool/:id',
      name: 'candidate-pool-detail',
      component: CandidateDetailView,
      props: { poolMode: true },
    },
    {
      path: '/candidates/:id',
      name: 'candidate-detail',
      component: CandidateDetailView,
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  if (!auth.initialized) await initializeAuth()
  if (!to.meta.public && !auth.user) {
    return { name: 'login', query: { redirect: to.fullPath }, replace: true }
  }
  if (to.name === 'login' && auth.user) return { name: 'dashboard' }
  return true
})

export default router
