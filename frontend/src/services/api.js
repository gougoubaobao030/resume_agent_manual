import { i18n } from '../i18n'

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request(path, options = {}) {
  let response
  const headers = new Headers(options.headers ?? {})

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  try {
    response = await fetch(path, {
      ...options,
      headers,
      credentials: 'include',
    })
  } catch (error) {
    throw new ApiError('Network request failed', 0, error)
  }

  const contentType = response.headers.get('content-type') ?? ''
  const body = response.status === 204
    ? null
    : contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    throw new ApiError('API request failed', response.status, body?.detail ?? body)
  }

  return body
}

export function login(username, password) {
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function logout() {
  return request('/api/auth/logout', { method: 'POST' })
}

export function getCurrentUser() {
  return request('/api/auth/me')
}

export function updatePreferredLanguage(preferredLanguage) {
  return request('/api/users/me/preferences/language', {
    method: 'PATCH',
    body: JSON.stringify({ preferred_language: preferredLanguage }),
  })
}

export function changePassword(currentPassword, newPassword) {
  return request('/api/users/me/password', {
    method: 'PUT',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  })
}

export function getJds() {
  return request('/api/jd')
}

export function updateJd(jobId, job) {
  return request(`/api/jd/${encodeURIComponent(jobId)}`, {
    method: 'PUT',
    body: JSON.stringify(job),
  })
}

export function deleteJd(jobId) {
  return request(`/api/jd/${encodeURIComponent(jobId)}`, { method: 'DELETE' })
}

export function getCandidates(jobId) {
  return request(`/api/candidates?job_id=${encodeURIComponent(jobId)}`)
}

export function getCandidatePool() {
  return request('/api/candidates/pool')
}

export function getCandidate(candidateId) {
  return request(`/api/candidates/${encodeURIComponent(candidateId)}`)
}

export function getCandidateResumeUrl(candidateId) {
  return `/api/candidates/${encodeURIComponent(candidateId)}/resume`
}

export function deleteCandidate(candidateId) {
  return request(`/api/candidates/${encodeURIComponent(candidateId)}`, { method: 'DELETE' })
}

export function removeCandidateFromJob(candidateId, jobId) {
  return request(`/api/candidates/${encodeURIComponent(candidateId)}/jobs/${encodeURIComponent(jobId)}`, {
    method: 'DELETE',
  })
}

export function getJobMatches(jobId) {
  return request(`/api/scoring/job-match?job_id=${encodeURIComponent(jobId)}`)
}

export function getTalentResult(candidateId, mode) {
  return request(`/api/talent/discover/${encodeURIComponent(candidateId)}?mode=${encodeURIComponent(mode)}`)
}

export function parseJd(rawText) {
  return request('/api/jd/parse', {
    method: 'POST',
    body: JSON.stringify({ raw_text: rawText }),
  })
}

export function saveJd(job) {
  return request('/api/jd', {
    method: 'POST',
    body: JSON.stringify(job),
  })
}

export function parseResumeBatch(files) {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))

  return request('/api/resume/parse-batch', {
    method: 'POST',
    body: formData,
  })
}

export function createResumeTask(files, jobId) {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  formData.append('job_id', jobId)

  return request('/api/resume/tasks', {
    method: 'POST',
    body: formData,
  })
}

export function getResumeTask(taskId) {
  return request(`/api/resume/tasks/${encodeURIComponent(taskId)}`)
}

export function retryResumeTaskItem(taskId, itemId) {
  return request(
    `/api/resume/tasks/${encodeURIComponent(taskId)}/items/${encodeURIComponent(itemId)}/retry`,
    { method: 'POST' },
  )
}

export function scoreJobMatch(jobId, candidateId, analysisLanguage) {
  return request('/api/scoring/job-match', {
    method: 'POST',
    body: JSON.stringify({
      job_id: jobId,
      candidate_id: candidateId,
      analysis_language: analysisLanguage,
    }),
  })
}

export function discoverTalent(candidateId, mode = 'auto', desiredTraits = [], analysisLanguage) {
  return request('/api/talent/discover', {
    method: 'POST',
    body: JSON.stringify({
      candidate_id: candidateId,
      mode,
      desired_traits: mode === 'specified' ? desiredTraits : [],
      analysis_language: analysisLanguage,
    }),
  })
}

export function getFriendlyResumeItemError(detail) {
  const t = i18n.global.t

  if (typeof detail !== 'string' || !detail.trim()) {
    return t('common.errors.resumeNoReason')
  }

  const message = detail.trim()

  if (message.includes('无法解析简历') || message.includes('简历文本为空')) {
    return t('common.errors.resumeUnreadable')
  }

  if (message.includes('配置') || message.includes('API key')) {
    return t('common.errors.server')
  }

  if (message.includes('请求失败') || message.includes('连接') || message.includes('timeout')) {
    return t('common.errors.unavailable')
  }

  if (message.includes('返回格式') || message.includes('校验')) {
    return t('common.errors.invalidResponse')
  }

  return t('common.errors.resumeGeneric')
}

export function getFriendlyApiError(error, actionLabel) {
  console.error(`${actionLabel} failed`, error)
  const t = i18n.global.t

  if (!(error instanceof ApiError) || error.status === 0) {
    return t('common.errors.network')
  }

  if (error.status === 400 || error.status === 422) {
    return t('common.errors.invalidRequest', { action: actionLabel })
  }

  if (error.status === 401) {
    return t('common.errors.sessionExpired')
  }

  if (error.status === 403) {
    return t('common.errors.permissionDenied')
  }

  if (error.status === 404) {
    return t('common.errors.notFound', { action: actionLabel })
  }

  if (error.status === 500) {
    return t('common.errors.server')
  }

  if (error.status === 502) {
    return t('common.errors.invalidResponse')
  }

  if (error.status === 503) {
    return t('common.errors.unavailable')
  }

  return t('common.errors.operationFailed', { action: actionLabel })
}
