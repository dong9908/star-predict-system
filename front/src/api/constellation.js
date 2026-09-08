export async function recognizeConstellation(image) {
  const formData = new FormData()
  formData.append('image', image)

  const response = await fetch('/api/constellation/recognize', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    let message = '별자리 분석에 실패했습니다.'
    try {
      const payload = await response.json()
      message = payload.detail || message
    } catch {
      // Keep the user-friendly fallback for non-JSON server errors.
    }
    throw new Error(message)
  }

  return response.json()
}
