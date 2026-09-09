import styled from 'styled-components'

const selectedTitleColors = {
  1: { border: '#38bdf8', background: 'radial-gradient(ellipse at 75% 20%, rgba(56, 189, 248, 0.34), transparent 42%), linear-gradient(135deg, #020617, #082f49 52%, #07111f)', text: '#7dd3fc', glow: 'rgba(56, 189, 248, 0.48)' },
  2: { border: '#a855f7', background: 'radial-gradient(ellipse at 75% 20%, rgba(236, 72, 153, 0.3), transparent 42%), linear-gradient(135deg, #090313, #3b0764 52%, #500724)', text: '#e9d5ff', glow: 'rgba(168, 85, 247, 0.5)' },
  3: { border: '#f59e0b', background: 'radial-gradient(ellipse at 75% 20%, rgba(253, 224, 71, 0.32), transparent 42%), linear-gradient(135deg, #0c0701, #78350f 52%, #713f12)', text: '#fde68a', glow: 'rgba(245, 158, 11, 0.52)' },
  unavailable: { border: '#f82646', background: 'radial-gradient(ellipse at 75% 20%, rgba(244, 63, 94, 0.36), transparent 42%), linear-gradient(135deg, #020203, #35070e 52%, #080102)', text: '#fecdd3' },
}

const getSelectedTitleColor = (level, unavailable) => (
  unavailable ? selectedTitleColors.unavailable : selectedTitleColors[level] || selectedTitleColors[1]
)

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
  gap: 1rem;
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

export const SelectedTitle = styled.div`
  width: fit-content;
  padding: 0.35rem 0.75rem;
  border: 1px solid ${props => props.$selected
    ? getSelectedTitleColor(props.$level, props.$unavailable).border
    : 'rgba(148, 163, 184, 0.3)'};
  border-radius: 9999px;
  background: ${props => props.$selected
    ? getSelectedTitleColor(props.$level, props.$unavailable).background
    : 'rgba(30, 41, 59, 0.45)'};
  color: ${props => props.$selected
    ? getSelectedTitleColor(props.$level, props.$unavailable).text
    : '#94a3b8'};
  font-size: 0.82rem;
  font-weight: 600;
  box-shadow: ${props => props.$selected
    ? props.$unavailable
      ? '0 0 4px rgba(248, 38, 70, 0.16), inset 0 1px 0 rgba(255, 228, 230, 0.09)'
      : `0 0 3px ${getSelectedTitleColor(props.$level, false).glow}, inset 0 1px 0 rgba(255, 255, 255, 0.07)`
    : 'none'};
`

export const ConstellationInfo = styled.div`
  font-size: 1rem;
  font-weight: 500;
  color: #fbbf24;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`

export const BadgeContainer = styled.div`
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
`

export const Badge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border-radius: 9999px;
  background: rgba(76, 29, 149, 0.5);
  border: 1.5px solid ${props => props.$borderColor || 'rgba(147, 51, 234, 0.5)'};
  color: white;
  font-size: 0.875rem;
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
