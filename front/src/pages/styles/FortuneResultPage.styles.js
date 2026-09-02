import styled from 'styled-components'

export const PageContainer = styled.div`
  width: 100%;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  padding: 2rem 1rem;
  min-height: 100vh;
`

export const ContentWrapper = styled.div`
  max-width: 1000px;
  margin: 0 auto;
`

export const PageHeader = styled.div`
  text-align: center;
  margin-bottom: 3rem;
`

export const PageTitle = styled.h1`
  font-size: 2.25rem;
  font-weight: 700;
  color: white;
  margin: 0 0 0.5rem 0;

  @media (max-width: 768px) {
    font-size: 1.75rem;
  }
`

export const PageSubtitle = styled.p`
  font-size: 0.875rem;
  color: #cbd5e1;
  margin: 0;
`

export const UserInfoSection = styled.div`
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2rem;
  padding: 1.5rem;
  border-radius: 0.75rem;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(147, 51, 234, 0.3);
  margin-bottom: 2rem;
  align-items: center;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`

export const UserInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
`

export const ConstellationIcon = styled.div`
  width: 60px;
  height: 60px;
  min-width: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #9333ea, #a855f7);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  box-shadow: 0 4px 15px rgba(147, 51, 234, 0.3);
`

export const UserDetails = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`

export const UserName = styled.h2`
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
  margin: 0;
`

export const UserMeta = styled.p`
  font-size: 0.875rem;
  color: #cbd5e1;
  margin: 0;
`

export const FortuneScore = styled.div`
  text-align: center;
  padding: 1rem;
  background: rgba(147, 51, 234, 0.2);
  border-radius: 0.5rem;
  border: 1px solid rgba(147, 51, 234, 0.4);
`

export const ScoreLabel = styled.p`
  font-size: 0.75rem;
  color: #a78bfa;
  margin: 0 0 0.5rem 0;
  font-weight: 600;
`

export const ScoreValue = styled.p`
  font-size: 1.75rem;
  font-weight: 700;
  color: #fbbf24;
  margin: 0;
`

export const DateSection = styled.div`
  text-align: center;
  padding: 1rem 1.5rem;
  background: rgba(76, 29, 149, 0.2);
  border-radius: 0.75rem;
  border: 1px solid rgba(147, 51, 234, 0.2);
  margin-bottom: 2rem;
`

export const DateText = styled.p`
  font-size: 0.875rem;
  color: #d8b4fe;
  margin: 0;
  font-weight: 600;
`

export const SummarySection = styled.div`
  padding: 1.5rem;
  border-radius: 0.75rem;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(147, 51, 234, 0.3);
  margin-bottom: 2rem;
`

export const SectionTitle = styled.h2`
  font-size: 1.125rem;
  font-weight: 700;
  color: white;
  margin: 0 0 1rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`

export const SummaryContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;

  p {
    font-size: 0.875rem;
    color: #cbd5e1;
    line-height: 1.6;
    margin: 0;
  }
`

export const CategoriesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  margin-bottom: 2rem;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`

export const CategoryCard = styled.div`
  padding: 1.5rem;
  border-radius: 0.75rem;
  background: rgba(15, 23, 42, 0.8);
  border-left: 3px solid ${props => props.$borderColor || '#a78bfa'};
  border: 1px solid rgba(147, 51, 234, 0.2);
  border-left: 3px solid ${props => props.$borderColor || '#a78bfa'};
  transition: all 150ms ease-in-out;
  cursor: pointer;

  &:hover {
    background: rgba(30, 41, 59, 0.9);
    transform: translateY(-4px);
    box-shadow: 0 8px 24px ${props => `${props.$borderColor}40` || 'rgba(147, 51, 234, 0.2)'};
  }
`

export const CardHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
`

export const CardIcon = styled.span`
  font-size: 1.5rem;
`

export const CardTitle = styled.h3`
  font-size: 1rem;
  font-weight: 700;
  color: white;
  margin: 0;
`

export const StarRating = styled.div`
  display: flex;
  gap: 0.25rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
`

export const Star = styled.span`
  color: ${props => (props.$filled ? '#fbbf24' : '#475569')};
  font-weight: bold;
`

export const CardContent = styled.p`
  font-size: 0.875rem;
  color: #cbd5e1;
  line-height: 1.6;
  margin: 0;
`

export const AdviceSection = styled.div`
  padding: 2rem;
  border-radius: 0.75rem;
  background: linear-gradient(135deg, rgba(147, 51, 234, 0.1), rgba(99, 102, 241, 0.1));
  border: 1px solid rgba(147, 51, 234, 0.3);
  margin-bottom: 2rem;
`

export const AdviceContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;

  p {
    font-size: 0.875rem;
    color: #cbd5e1;
    line-height: 1.6;
    margin: 0;
  }
`

export const FooterInfo = styled.div`
  text-align: center;
  padding: 1.5rem;
  border-top: 1px solid rgba(147, 51, 234, 0.2);
  margin-top: 2rem;
`

export const FooterText = styled.p`
  font-size: 0.75rem;
  color: #64748b;
  margin: 0.5rem 0;

  &:first-child {
    color: #a78bfa;
    font-weight: 600;
    margin-top: 0;
  }
`

export const BackButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  background-color: transparent;
  color: #a78bfa;
  border: 1px solid rgba(147, 51, 234, 0.5);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 150ms ease-in-out;
  margin-bottom: 1.5rem;

  &:hover {
    background-color: rgba(147, 51, 234, 0.1);
    border-color: rgba(147, 51, 234, 0.8);
    color: #d8b4fe;
  }
`
