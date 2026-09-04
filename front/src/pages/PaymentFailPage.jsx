import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { failPaymentAPI } from '../api/payment'
import {
  PaymentActions, PaymentButton, PaymentCard, PaymentDescription,
  PaymentError, PaymentIcon, PaymentPageContainer, PaymentTitle,
} from './styles/PaymentPage.styles'

function PaymentFailPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [processing, setProcessing] = useState(true)
  const [error, setError] = useState('')
  const failureStarted = useRef(false)

  useEffect(() => {
    if (failureStarted.current) return undefined
    failureStarted.current = true

    const recordFailure = async () => {
      const accessToken = localStorage.getItem('accessToken')
      const partnerOrderId = searchParams.get('partnerOrderId')
        || sessionStorage.getItem('pendingPaymentOrderId')

      if (!accessToken || !partnerOrderId) {
        setError('실패한 결제의 주문 정보를 확인하지 못했습니다.')
        setProcessing(false)
        return
      }

      try {
        await failPaymentAPI(accessToken, partnerOrderId)
        sessionStorage.removeItem('pendingPaymentOrderId')
      } catch (requestError) {
        setError(requestError.message || '결제 실패 상태를 저장하지 못했습니다.')
      } finally {
        setProcessing(false)
      }
    }

    recordFailure()
    return undefined
  }, [searchParams])

  return (
    <PaymentPageContainer><PaymentCard>
      <PaymentIcon>{processing ? '⏳' : '⚠️'}</PaymentIcon>
      <PaymentTitle>{processing ? '결제 상태를 확인하고 있습니다' : '결제를 완료하지 못했습니다'}</PaymentTitle>
      <PaymentDescription>{processing ? '잠시만 기다려주세요.' : `일시적인 오류가 발생했거나 결제가 승인되지 않았습니다.\n잠시 후 다시 시도해주세요.`}</PaymentDescription>
      {error && <PaymentError role="alert">{error}</PaymentError>}
      <PaymentActions>
        <PaymentButton type="button" disabled={processing} onClick={() => navigate('/fortune-reading')}>결제 다시 시도</PaymentButton>
        <PaymentButton type="button" $secondary disabled={processing} onClick={() => navigate('/')}>메인으로</PaymentButton>
      </PaymentActions>
    </PaymentCard></PaymentPageContainer>
  )
}

export default PaymentFailPage
