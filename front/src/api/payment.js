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

const updatePaymentStatusAPI = async (accessToken, path, partnerOrderId) => {
  const response = await fetch(`/api/payment/${path}`, {
    method: 'POST',
    headers: authorizationHeaders(accessToken),
    body: JSON.stringify({ partnerOrderId }),
  })
  return parseResponse(response)
}

export const cancelPaymentAPI = async (accessToken, partnerOrderId) => (
  updatePaymentStatusAPI(accessToken, 'cancel', partnerOrderId)
)

export const failPaymentAPI = async (accessToken, partnerOrderId) => (
  updatePaymentStatusAPI(accessToken, 'fail', partnerOrderId)
)

export const refundPaymentAPI = async accessToken => {
  const response = await fetch('/api/payment/refund', {
    method: 'POST',
    headers: authorizationHeaders(accessToken),
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
