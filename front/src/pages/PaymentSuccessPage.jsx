import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getMyInfoAPI } from '../api/auth'
import { createInitialFortuneAPI } from '../api/fortune'
import { approvePaymentAPI } from '../api/payment'
import {
  PaymentActions, PaymentButton, PaymentCard, PaymentDescription,
  PaymentError, PaymentIcon, PaymentPageContainer, PaymentTitle,
} from './styles/PaymentPage.styles'

function PaymentSuccessPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [error, setError] = useState('')
  const [processing, setProcessing] = useState(true)
  const approvalStarted = useRef(false)

  useEffect(() => {
    if (approvalStarted.current) return undefined
    approvalStarted.current = true

    const completePayment = async () => {
      const accessToken = localStorage.getItem('accessToken')
      const pgToken = searchParams.get('pg_token')
      const partnerOrderId = searchParams.get('partnerOrderId')
        || sessionStorage.getItem('pendingPaymentOrderId')

      if (!accessToken) {
        navigate('/login', { replace: true })
        return
      }
      if (!pgToken || !partnerOrderId) {
        setError('결제 승인 정보가 없습니다. 운세 페이지에서 다시 시도해주세요.')
        setProcessing(false)
        return
      }

      try {
        await approvePaymentAPI(accessToken, { partnerOrderId, pgToken })
        const [myInfo, initialFortune] = await Promise.all([
          getMyInfoAPI(accessToken),
          createInitialFortuneAPI(accessToken),
        ])
        const resultState = { fortune: initialFortune, user: myInfo }
        sessionStorage.removeItem('pendingPaymentOrderId')
        sessionStorage.removeItem('fortuneConversationId')
        sessionStorage.setItem('fortuneResult', JSON.stringify(resultState))
        navigate('/fortune-result', { replace: true, state: resultState })
      } catch (requestError) {
        if (requestError.status === 401) {
          localStorage.removeItem('accessToken')
          localStorage.removeItem('user')
          navigate('/login', { replace: true })
          return
        }
        setError(requestError.message || '결제를 승인하지 못했습니다.')
        setProcessing(false)
      }
    }

    completePayment()
    return undefined
  }, [navigate, searchParams])

  return (
    <PaymentPageContainer>
      <PaymentCard>
        <PaymentIcon>{processing ? '⏳' : '⚠️'}</PaymentIcon>
        <PaymentTitle>{processing ? '결제를 확인하고 있습니다' : '결제 확인이 필요합니다'}</PaymentTitle>
        <PaymentDescription>
          {processing ? '창을 닫지 말고 잠시만 기다려주세요.' : '결제 상태를 확인한 후 다시 시도해주세요.'}
        </PaymentDescription>
        {error && <PaymentError role="alert">{error}</PaymentError>}
        {!processing && (
          <PaymentActions>
            <PaymentButton type="button" onClick={() => navigate('/fortune-reading')}>
              운세 페이지로 이동
            </PaymentButton>
          </PaymentActions>
        )}
      </PaymentCard>
    </PaymentPageContainer>
  )
}

export default PaymentSuccessPage
