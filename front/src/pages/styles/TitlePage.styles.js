import styled from 'styled-components'

const tierColors = {
  common: {
    border: 'rgba(56, 189, 248, 0.58)',
    background: 'radial-gradient(ellipse at 78% 12%, rgba(56, 189, 248, 0.3) 0%, rgba(8, 145, 178, 0.13) 25%, transparent 49%), radial-gradient(ellipse at 28% 92%, rgba(34, 211, 238, 0.2) 0%, transparent 42%), linear-gradient(128deg, #020617 0%, #082f49 48%, #07111f 70%, #020617 100%)',
    color: '#7dd3fc',
    accent: 'linear-gradient(90deg, #38bdf8, #22d3ee)',
    badge: 'linear-gradient(135deg, rgba(14, 165, 233, 0.3), rgba(34, 211, 238, 0.16))',
    glow: '0 8px 22px rgba(2, 6, 23, 0.36), 0 0 7px rgba(56, 189, 248, 0.07), inset 0 1px 0 rgba(125, 211, 252, 0.09)',
  },
  rare: {
    border: 'rgba(168, 85, 247, 0.65)',
    background: 'radial-gradient(ellipse at 78% 12%, rgba(236, 72, 153, 0.3) 0%, rgba(126, 34, 206, 0.15) 26%, transparent 50%), radial-gradient(ellipse at 28% 92%, rgba(139, 92, 246, 0.25) 0%, transparent 43%), linear-gradient(128deg, #090313 0%, #3b0764 46%, #500724 61%, #08020f 100%)',
    color: '#d8b4fe',
    accent: 'linear-gradient(90deg, #8b5cf6, #ec4899)',
    badge: 'linear-gradient(135deg, rgba(139, 92, 246, 0.38), rgba(236, 72, 153, 0.22))',
    glow: '0 8px 23px rgba(2, 6, 23, 0.38), 0 0 7px rgba(168, 85, 247, 0.08), inset 0 1px 0 rgba(244, 114, 182, 0.09)',
  },
  legendary: {
    border: 'rgba(245, 158, 11, 0.72)',
    background: 'radial-gradient(ellipse at 78% 12%, rgba(253, 224, 71, 0.3) 0%, rgba(245, 158, 11, 0.15) 25%, transparent 49%), radial-gradient(ellipse at 28% 92%, rgba(249, 115, 22, 0.24) 0%, transparent 43%), linear-gradient(128deg, #0c0701 0%, #78350f 47%, #713f12 61%, #090501 100%)',
    color: '#fcd34d',
    accent: 'linear-gradient(90deg, #f59e0b, #fde047, #f97316)',
    badge: 'linear-gradient(135deg, rgba(245, 158, 11, 0.38), rgba(249, 115, 22, 0.22))',
    glow: '0 9px 24px rgba(2, 6, 23, 0.4), 0 0 8px rgba(245, 158, 11, 0.09), inset 0 1px 0 rgba(254, 240, 138, 0.1)',
  },
  unavailable: {
    border: 'rgba(248, 38, 70, 0.9)',
    background: 'radial-gradient(ellipse at 78% 12%, rgba(255, 82, 103, 0.34) 0%, rgba(127, 29, 29, 0.16) 24%, transparent 48%), radial-gradient(ellipse at 32% 88%, rgba(190, 18, 60, 0.3) 0%, transparent 44%), linear-gradient(128deg, #020203 0%, #100306 34%, #35070e 51%, #0d0204 68%, #000 100%)',
    color: '#fecdd3',
    accent: 'linear-gradient(90deg, #050000, #7f1d1d, #fff1f2, #e11d48, #050000)',
    badge: 'linear-gradient(135deg, rgba(127, 29, 29, 0.9), rgba(15, 0, 3, 0.96))',
    glow: '0 9px 24px rgba(0, 0, 0, 0.46), 0 0 8px rgba(225, 29, 72, 0.1), inset 0 1px 0 rgba(255, 228, 230, 0.09)',
  },
}

const getTierColor = tier => tierColors[tier] || tierColors.common

export const PageContainer = styled.main`
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  padding: 3rem 1.25rem 4rem;
`

export const Header = styled.header`
  display: flex;
  align-items: center;
  gap: 1rem;
  color: #c084fc;
  margin-bottom: 1.5rem;
`

export const PageTitle = styled.h1`
  margin: 0;
  color: #fff;
  font-size: clamp(1.75rem, 4vw, 2.25rem);
`

export const PageDescription = styled.p`
  margin: 0.35rem 0 0;
  color: #94a3b8;
`

export const Progress = styled.section`
  padding: 1rem 1.25rem;
  margin-bottom: 1.25rem;
  border: 1px solid rgba(168, 85, 247, 0.28);
  border-radius: 0.75rem;
  background: rgba(30, 41, 59, 0.65);
  color: #e2e8f0;
  font-weight: 600;
`

export const ProgressBar = styled.div`
  height: 8px;
  margin-top: 0.75rem;
  overflow: hidden;
  border-radius: 999px;
  background: #0f172a;
`

export const ProgressFill = styled.div`
  width: ${props => props.$percent}%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #7c3aed, #c084fc);
  transition: width 250ms ease;
`

export const NewTitleBanner = styled.div`
  padding: 1rem 1.25rem;
  margin-bottom: 1.25rem;
  border: 1px solid rgba(251, 191, 36, 0.55);
  border-radius: 0.75rem;
  background: rgba(120, 53, 15, 0.32);
  color: #fde68a;
  font-weight: 700;
`

export const TitleGrid = styled.section`
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;

  @media (max-width: 720px) {
    grid-template-columns: 1fr;
  }
`

export const TitleCard = styled.article`
  position: relative;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1rem;
  min-height: 128px;
  padding: 1.25rem;
  border: 1px solid ${props => props.$acquired
    ? getTierColor(props.$tier).border
    : 'rgba(100, 116, 139, 0.28)'};
  border-radius: 0.75rem;
  background: ${props => props.$acquired
    ? getTierColor(props.$tier).background
    : 'rgba(15, 23, 42, 0.72)'};
  box-shadow: ${props => props.$acquired
    ? getTierColor(props.$tier).glow
    : 'none'};
  opacity: ${props => props.$acquired ? 1 : 0.68};
  overflow: hidden;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 3px;
    background: ${props => props.$acquired
      ? getTierColor(props.$tier).accent
      : 'linear-gradient(90deg, #475569, #64748b)'};
  }

  &::after {
    content: '';
    position: absolute;
    top: -52px;
    right: -52px;
    width: 130px;
    height: 130px;
    border-radius: 50%;
    background: ${props => props.$acquired
      ? getTierColor(props.$tier).accent
      : '#475569'};
    opacity: ${props => props.$acquired ? 0.07 : 0.025};
    filter: blur(12px);
    pointer-events: none;
  }

  & > * {
    position: relative;
    z-index: 1;
  }

  &:hover {
    transform: translateY(-2px);
    box-shadow: ${props => props.$acquired
      ? getTierColor(props.$tier).glow
      : '0 8px 20px rgba(2, 6, 23, 0.22)'};
  }
`

export const StatusIcon = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid ${props => props.$acquired
    ? getTierColor(props.$tier).border
    : 'rgba(100, 116, 139, 0.35)'};
  background: ${props => props.$acquired
    ? getTierColor(props.$tier).background
    : 'rgba(71, 85, 105, 0.35)'};
  color: ${props => props.$acquired
    ? getTierColor(props.$tier).color
    : '#64748b'};
  box-shadow: ${props => props.$acquired
    ? `0 0 16px ${getTierColor(props.$tier).border}`
    : 'none'};
`

export const TitleName = styled.h2`
  margin: 0;
  color: #f8fafc;
  font-size: 1.05rem;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
`

export const TitleTierBadge = styled.span`
  padding: 0.2rem 0.5rem;
  border: 1px solid ${props => getTierColor(props.$tier).border};
  border-radius: 999px;
  background: ${props => getTierColor(props.$tier).badge};
  color: ${props => getTierColor(props.$tier).color};
  font-size: 0.68rem;
  font-weight: 800;
  line-height: 1;
`

export const TitleDescription = styled.p`
  margin: 0.5rem 0 0;
  color: #cbd5e1;
  font-size: 0.875rem;
  line-height: 1.55;
`

export const AcquiredDate = styled.p`
  margin: 0.65rem 0 0;
  color: #a78bfa;
  font-size: 0.78rem;
`

export const SelectButton = styled.button`
  margin-top: 0.8rem;
  padding: 0.45rem 0.75rem;
  border: 1px solid ${props => props.$selected ? '#a78bfa' : 'rgba(167, 139, 250, 0.45)'};
  border-radius: 0.5rem;
  background: ${props => props.$selected ? '#7c3aed' : 'transparent'};
  color: ${props => props.$selected ? '#fff' : '#c4b5fd'};
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;

  &:hover:not(:disabled) {
    background: rgba(124, 58, 237, 0.3);
  }

  &:disabled {
    cursor: default;
    opacity: ${props => props.$selected ? 1 : 0.55};
  }
`

export const LoadingMessage = styled.p`
  padding: 3rem 1rem;
  text-align: center;
  color: #cbd5e1;
`

export const EmptyMessage = styled(LoadingMessage)``

export const ErrorMessage = styled(LoadingMessage)`
  color: #fca5a5;
`
