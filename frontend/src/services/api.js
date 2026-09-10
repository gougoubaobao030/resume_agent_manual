class ApiError extends Error {
  constructor(message, status, detail) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request(path, options = {}) {
  let response

  try {
    response = await fetch(path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
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

export function getFriendlyApiError(error, actionLabel) {
  console.error(`${actionLabel} failed`, error)

  if (!(error instanceof ApiError) || error.status === 0) {
    return '无法连接后端服务，请确认 FastAPI 已在 18000 端口启动后重试。'
  }

  if (error.status === 400 || error.status === 422) {
    return '提交内容不符合要求，请检查 JD 文本和各项字段后重试。'
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
