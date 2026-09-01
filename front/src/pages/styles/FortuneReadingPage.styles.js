import styled from 'styled-components'

export const PageContainer = styled.div`
  width: 100%;
  padding: 3rem 2rem;
  min-height: calc(100vh - 80px);
`

export const ContentWrapper = styled.div`
  max-width: 900px;
  margin: 0 auto;
`

export const PageTitle = styled.h1`
  font-size: 2rem;
  color: white;
  text-align: center;
  margin-bottom: 0.5rem;

  @media (max-width: 768px) {
    font-size: 1.5rem;
  }
`

export const PageSubtitle = styled.p`
  color: #cbd5e1;
  text-align: center;
  margin-bottom: 3rem;
  font-size: 1rem;
`

export const UserInfoBox = styled.div`
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 1rem;
  padding: 2rem;
  background: rgba(0, 0, 0, 0.3);
  margin-bottom: 2rem;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2rem;
  align-items: center;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    padding: 1.5rem;
  }
`

export const UserInfoContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`

export const ConstellationInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
`

export const ConstellationIcon = styled.div`
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #a78bfa, #d8b4fe);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
`

export const ConstellationDetails = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
`

export const ConstellationName = styled.h2`
  color: white;
  font-size: 1.25rem;
  margin: 0;
`

export const ConstellationMetaInfo = styled.p`
  color: #a78bfa;
  font-size: 0.875rem;
  margin: 0;
`

export const DetailInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #cbd5e1;
  font-size: 0.875rem;
  margin-top: 0.5rem;
`

export const DetailLabel = styled.span`
  color: #a78bfa;
`

export const ActionButton = styled.button`
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #a78bfa, #d8b4fe);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 300ms ease;
  font-size: 0.875rem;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(167, 139, 250, 0.3);
  }

  @media (max-width: 768px) {
    width: 100%;
  }
`

export const FortuneBox = styled.div`
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 1rem;
  padding: 2.5rem;
  background: rgba(0, 0, 0, 0.3);
  margin-bottom: 2rem;

  @media (max-width: 768px) {
    padding: 1.5rem;
  }
`

export const FortuneTitle = styled.h2`
  color: white;
  font-size: 1.5rem;
  margin: 0 0 0.5rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;

  @media (max-width: 768px) {
    font-size: 1.25rem;
  }
`

export const FortuneDate = styled.p`
  color: #cbd5e1;
  font-size: 0.875rem;
  margin: 0 0 1.5rem 0;
`

export const FortuneContent = styled.div`
  color: #cbd5e1;
  line-height: 1.8;
  font-size: 0.95rem;

  p {
    margin: 0 0 1rem 0;

    &:last-child {
      margin-bottom: 0;
    }
  }
`

export const PremiumBox = styled.div`
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 1rem;
  padding: 2rem;
  background: rgba(167, 139, 250, 0.05);
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2rem;
  align-items: center;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    padding: 1.5rem;
  }
`

export const PremiumContent = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 1rem;
`

export const PremiumIcon = styled.div`
  width: 50px;
  height: 50px;
  min-width: 50px;
  border-radius: 50%;
  background: linear-gradient(135deg, #a78bfa, #d8b4fe);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
`

export const PremiumInfo = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
`

export const PremiumTitle = styled.h3`
  color: white;
  font-size: 1rem;
  margin: 0;
`

export const PremiumDescription = styled.p`
  color: #cbd5e1;
  font-size: 0.875rem;
  margin: 0;
`

export const PriceSection = styled.div`
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1rem;

  @media (max-width: 768px) {
    align-items: flex-start;
  }
`

export const Price = styled.span`
  color: #a78bfa;
  font-size: 1.5rem;
  font-weight: 700;
`

export const BuyButton = styled.button`
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #a78bfa, #d8b4fe);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 300ms ease;
  white-space: nowrap;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(167, 139, 250, 0.3);
  }

  @media (max-width: 768px) {
    width: 100%;
  }
`
