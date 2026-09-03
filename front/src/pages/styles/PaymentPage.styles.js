import styled from 'styled-components'

export const PaymentPageContainer = styled.div`
  min-height: calc(100vh - 80px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem 1.5rem;
`

export const PaymentCard = styled.section`
  width: min(100%, 540px);
  padding: 3rem;
  border: 1px solid rgba(167, 139, 250, 0.35);
  border-radius: 1rem;
  background: rgba(15, 23, 42, 0.92);
  color: white;
  text-align: center;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);

  @media (max-width: 600px) {
    padding: 2rem 1.25rem;
  }
`

export const PaymentIcon = styled.div`
  font-size: 3rem;
  margin-bottom: 1rem;
`

export const PaymentTitle = styled.h1`
  margin: 0 0 0.75rem;
  font-size: 1.75rem;
`

export const PaymentDescription = styled.p`
  margin: 0;
  color: #cbd5e1;
  line-height: 1.7;
  white-space: pre-line;
`

export const PaymentError = styled.p`
  margin: 1.25rem 0 0;
  color: #fca5a5;
  line-height: 1.6;
`

export const PaymentActions = styled.div`
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 2rem;

  @media (max-width: 480px) {
    flex-direction: column;
  }
`

export const PaymentButton = styled.button`
  padding: 0.8rem 1.4rem;
  border: ${({ $secondary }) => $secondary ? '1px solid #64748b' : 'none'};
  border-radius: 0.6rem;
  background: ${({ $secondary }) => $secondary
    ? 'transparent'
    : 'linear-gradient(135deg, #9333ea, #a855f7)'};
  color: white;
  font-weight: 700;
  cursor: pointer;

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
`
