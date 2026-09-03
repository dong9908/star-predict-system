import { useNavigate } from 'react-router-dom'
import {
  PaymentActions, PaymentButton, PaymentCard, PaymentDescription,
  PaymentIcon, PaymentPageContainer, PaymentTitle,
} from './styles/PaymentPage.styles'

function PaymentFailPage() {
  const navigate = useNavigate()

  return (
    <PaymentPageContainer><PaymentCard>
      <PaymentIcon>⚠️</PaymentIcon>
      <PaymentTitle>결제를 완료하지 못했습니다</PaymentTitle>
      <PaymentDescription>일시적인 오류가 발생했거나 결제가 승인되지 않았습니다.{`\n`}잠시 후 다시 시도해주세요.</PaymentDescription>
      <PaymentActions>
        <PaymentButton type="button" onClick={() => navigate('/fortune-reading')}>결제 다시 시도</PaymentButton>
        <PaymentButton type="button" $secondary onClick={() => navigate('/')}>메인으로</PaymentButton>
      </PaymentActions>
    </PaymentCard></PaymentPageContainer>
  )
}

export default PaymentFailPage
