const parseResponse = async (response) => {
  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json')
    ? await response.json()
    : { detail: await response.text() }

  if (!response.ok) {
    const error = new Error(data.detail || '운세 서비스 요청에 실패했습니다.')
    error.status = response.status
    throw error
  }

  return data
}

const authorizationHeaders = (accessToken) => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${accessToken}`,
})

export const createInitialFortuneAPI = async (accessToken) => {
  const response = await fetch('/api/fortune/initial', {
    method: 'POST',
    headers: authorizationHeaders(accessToken),
  })

  return parseResponse(response)
}

export const createFortuneChatAPI = async (
  accessToken,
  { conversationId = null, message, category = 'general', history = [] },
) => {
  const response = await fetch('/api/fortune/chat', {
    method: 'POST',
    headers: authorizationHeaders(accessToken),
    body: JSON.stringify({ conversationId, message, category, history }),
  })

  return parseResponse(response)
}

export const getFortuneConversationsAPI = async accessToken => {
  const response = await fetch('/api/fortune/conversations', {
    method: 'GET',
    headers: authorizationHeaders(accessToken),
  })

  return parseResponse(response)
}

export const getFortuneConversationMessagesAPI = async (
  accessToken,
  conversationId,
) => {
  const response = await fetch(
    `/api/fortune/conversations/${conversationId}/messages`,
    {
      method: 'GET',
      headers: authorizationHeaders(accessToken),
    },
  )

  return parseResponse(response)
}

export const deleteFortuneConversationAPI = async (
  accessToken,
  conversationId,
) => {
  const response = await fetch(
    `/api/fortune/conversations/${conversationId}`,
    {
      method: 'DELETE',
      headers: authorizationHeaders(accessToken),
    },
  )

  return parseResponse(response)
}
