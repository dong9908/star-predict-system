import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { cancelPaymentAPI } from '../api/payment'
import {
  PaymentActions, PaymentButton, PaymentCard, PaymentDescription,
  PaymentError, PaymentIcon, PaymentPageContainer, PaymentTitle,
} from './styles/PaymentPage.styles'

function PaymentCancelPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [processing, setProcessing] = useState(true)
  const [error, setError] = useState('')
  const cancellationStarted = useRef(false)

  useEffect(() => {
    if (cancellationStarted.current) return undefined
    cancellationStarted.current = true

    const recordCancellation = async () => {
      const accessToken = localStorage.getItem('accessToken')
      const partnerOrderId = searchParams.get('partnerOrderId')
        || sessionStorage.getItem('pendingPaymentOrderId')

      if (!accessToken || !partnerOrderId) {
        setError('취소된 결제의 주문 정보를 확인하지 못했습니다.')
        setProcessing(false)
        return
      }

      try {
        await cancelPaymentAPI(accessToken, partnerOrderId)
        sessionStorage.removeItem('pendingPaymentOrderId')
      } catch (requestError) {
        setError(requestError.message || '결제 취소 상태를 저장하지 못했습니다.')
      } finally {
        setProcessing(false)
      }
    }

    recordCancellation()
    return undefined
  }, [searchParams])

  return (
    <PaymentPageContainer><PaymentCard>
      <PaymentIcon>{processing ? '⏳' : '↩️'}</PaymentIcon>
      <PaymentTitle>{processing ? '결제 취소를 확인하고 있습니다' : '결제가 취소되었습니다'}</PaymentTitle>
      <PaymentDescription>{processing ? '잠시만 기다려주세요.' : `결제 금액은 청구되지 않았습니다.\n원할 때 다시 진행할 수 있습니다.`}</PaymentDescription>
      {error && <PaymentError role="alert">{error}</PaymentError>}
      <PaymentActions>
        <PaymentButton type="button" disabled={processing} onClick={() => navigate('/fortune-reading')}>다시 시도</PaymentButton>
        <PaymentButton type="button" $secondary disabled={processing} onClick={() => navigate('/')}>메인으로</PaymentButton>
      </PaymentActions>
    </PaymentCard></PaymentPageContainer>
  )
}

export default PaymentCancelPage
