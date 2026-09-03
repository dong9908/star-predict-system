import { useNavigate } from 'react-router-dom'
import {
  PaymentActions, PaymentButton, PaymentCard, PaymentDescription,
  PaymentIcon, PaymentPageContainer, PaymentTitle,
} from './styles/PaymentPage.styles'

function PaymentCancelPage() {
  const navigate = useNavigate()

  return (
    <PaymentPageContainer><PaymentCard>
      <PaymentIcon>↩️</PaymentIcon>
      <PaymentTitle>결제가 취소되었습니다</PaymentTitle>
      <PaymentDescription>결제 금액은 청구되지 않았습니다.{`\n`}원할 때 다시 진행할 수 있습니다.</PaymentDescription>
      <PaymentActions>
        <PaymentButton type="button" onClick={() => navigate('/fortune-reading')}>다시 시도</PaymentButton>
        <PaymentButton type="button" $secondary onClick={() => navigate('/')}>메인으로</PaymentButton>
      </PaymentActions>
    </PaymentCard></PaymentPageContainer>
  )
}

export default PaymentCancelPage
