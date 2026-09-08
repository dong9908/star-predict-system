const requestTitleAPI = async (path, accessToken, options = {}) => {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${accessToken}`,
    },
  })

  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json')
    ? await response.json()
    : { detail: await response.text() }

  if (!response.ok) {
    const error = new Error(data.detail || '칭호 정보를 불러오지 못했습니다.')
    error.status = response.status
    throw error
  }

  return data
}

export const getMyTitlesAPI = accessToken =>
  requestTitleAPI('/api/titles/me', accessToken, { method: 'GET' })

export const evaluateMyTitlesAPI = accessToken =>
  requestTitleAPI('/api/titles/evaluate', accessToken, { method: 'POST' })

export const selectMyTitleAPI = (accessToken, titleId) =>
  requestTitleAPI(`/api/titles/me/selected/${titleId}`, accessToken, { method: 'PUT' })
