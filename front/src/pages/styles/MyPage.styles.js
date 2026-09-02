import styled from 'styled-components'

export const PageContainer = styled.div`
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
`

export const ProfileSection = styled.div`
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 2rem;
  align-items: center;
  padding: 2rem;
  border-radius: 0.75rem;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(147, 51, 234, 0.3);
  margin-bottom: 2rem;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
`

export const ProfileIcon = styled.div`
  width: 100px;
  height: 100px;
  min-width: 100px;
  border-radius: 0.75rem;
  border: 2px solid rgba(147, 51, 234, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(76, 29, 149, 0.2);
  font-size: 3rem;
`

export const ProfileInfo = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
`

export const UserName = styled.h1`
  font-size: 1.875rem;
  font-weight: 700;
  color: white;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 1rem;
`

export const ConstellationInfo = styled.div`
  font-size: 0.875rem;
  color: #cbd5e1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`

export const BadgeContainer = styled.div`
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
`

export const Badge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  background: rgba(76, 29, 149, 0.4);
  border: 1px solid ${props => props.$borderColor || 'rgba(147, 51, 234, 0.5)'};
  color: #d8b4fe;
  font-size: 0.75rem;
  font-weight: 600;
`

export const EditButton = styled.button`
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  background-color: #9333ea;
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: background-color 150ms ease-in-out;
  white-space: nowrap;

  &:hover {
    background-color: #a855f7;
  }

  @media (max-width: 768px) {
    width: 100%;
  }
`

export const TabMenu = styled.div`
  display: flex;
  gap: 0;
  margin-bottom: 2rem;
  border-bottom: 1px solid rgba(147, 51, 234, 0.2);
`

export const Tab = styled.button`
  padding: 1rem 1.5rem;
  background: ${props => (props.$active ? '#9333ea' : 'transparent')};
  color: ${props => (props.$active ? 'white' : '#cbd5e1')};
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  border-bottom: ${props => (props.$active ? 'none' : '1px solid transparent')};
  transition: all 150ms ease-in-out;

  &:hover {
    color: white;
  }
`

export const ContentArea = styled.div`
  width: 100%;
`

export const SectionTitle = styled.h2`
  font-size: 1.125rem;
  font-weight: 700;
  color: white;
  margin: 0 0 1.5rem 0;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(147, 51, 234, 0.2);
`

export const CardGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  margin-bottom: 2rem;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`

export const CharacteristicCard = styled.div`
  padding: 1.5rem;
  border-radius: 0.75rem;
  border: 2px solid ${props => props.$borderColor || 'rgba(147, 51, 234, 0.5)'};
  background: rgba(15, 23, 42, 0.8);
  display: flex;
  gap: 1rem;
  transition: all 150ms ease-in-out;
  cursor: pointer;

  &:hover {
    background: rgba(30, 41, 59, 0.9);
    transform: translateY(-2px);
  }
`

export const CardIcon = styled.div`
  width: 48px;
  height: 48px;
  min-width: 48px;
  border-radius: 50%;
  border: 2px solid ${props => props.$borderColor || 'rgba(147, 51, 234, 0.5)'};
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  color: ${props => props.$borderColor || '#a78bfa'};
`

export const CardContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`

export const CardTitle = styled.h3`
  font-size: 1rem;
  font-weight: 700;
  color: white;
  margin: 0;
`

export const CardDescription = styled.p`
  font-size: 0.875rem;
  color: #cbd5e1;
  margin: 0;
`

export const FooterText = styled.p`
  text-align: center;
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(147, 51, 234, 0.2);
`
