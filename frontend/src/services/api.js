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
  const body = contentType.includes('application/json')
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

export function getCandidate(candidateId) {
  return request(`/api/candidates/${encodeURIComponent(candidateId)}`)
}

export function deleteCandidate(candidateId) {
  return request(`/api/candidates/${encodeURIComponent(candidateId)}`, { method: 'DELETE' })
}

export function getJobMatches(jobId) {
  return request(`/api/scoring/job-match?job_id=${encodeURIComponent(jobId)}`)
}

export function getTalentResult(candidateId) {
  return request(`/api/talent/discover/${encodeURIComponent(candidateId)}`)
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
  if (typeof detail !== 'string' || !detail.trim()) {
    return '解析失败，后端未返回具体原因。'
  }

  const message = detail.trim()

  if (message.includes('无法解析简历') || message.includes('简历文本为空')) {
    return message
  }

  if (message.includes('配置') || message.includes('API key')) {
    return 'AI 服务配置暂时不可用，请联系系统维护人员。'
  }

  if (message.includes('请求失败') || message.includes('连接') || message.includes('timeout')) {
    return 'AI 服务暂时无法响应，请稍后重试。'
  }

  if (message.includes('返回格式') || message.includes('校验')) {
    return 'AI 返回的内容暂时无法识别。'
  }

  if (!message.includes('\n') && message.length <= 160) {
    return message
  }

  return '该简历解析失败，请检查文件内容后重试。'
}

export function getFriendlyApiError(error, actionLabel) {
  console.error(`${actionLabel} failed`, error)

  if (!(error instanceof ApiError) || error.status === 0) {
    return '无法连接后端服务，请确认 FastAPI 已在 18000 端口启动后重试。'
  }

  if (error.status === 400 || error.status === 422) {
    if (typeof error.detail === 'string' && error.detail.length <= 160) {
      return error.detail
    }
    return `提交内容不符合要求，请检查${actionLabel}内容后重试。`
  }

  if (error.status === 500) {
    return 'AI 服务配置暂时不可用，请联系系统维护人员。'
  }

  if (error.status === 502) {
    return 'AI 返回的内容暂时无法识别，请稍后重新解析。'
  }

  if (error.status === 503) {
    return 'AI 服务暂时无法响应，请稍后重试。'
  }

  return `${actionLabel}失败，请稍后重试。`
}
