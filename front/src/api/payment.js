const parseResponse = async response => {
  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json')
    ? await response.json()
    : { detail: await response.text() }

  if (!response.ok) {
    const error = new Error(data.detail || '결제 서비스 요청에 실패했습니다.')
    error.status = response.status
    throw error
  }

  return data
}

const authorizationHeaders = accessToken => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${accessToken}`,
})

export const readyPaymentAPI = async accessToken => {
  const response = await fetch('/api/payment/ready', {
    method: 'POST',
    headers: authorizationHeaders(accessToken),
  })
  return parseResponse(response)
}

export const approvePaymentAPI = async (
  accessToken,
  { partnerOrderId, pgToken },
) => {
  const response = await fetch('/api/payment/approve', {
    method: 'POST',
    headers: authorizationHeaders(accessToken),
    body: JSON.stringify({ partnerOrderId, pgToken }),
  })
  return parseResponse(response)
}

export const getPaymentAccessAPI = async accessToken => {
  const response = await fetch('/api/payment/access', {
    method: 'GET',
    headers: authorizationHeaders(accessToken),
  })
  return parseResponse(response)
}

export const getPaymentHistoryAPI = async accessToken => {
  const response = await fetch('/api/payment/history', {
    method: 'GET',
    headers: authorizationHeaders(accessToken),
  })
  return parseResponse(response)
}
