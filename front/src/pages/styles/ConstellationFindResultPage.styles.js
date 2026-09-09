import styled from 'styled-components'

export const ResultPageShell = styled.div`
  width: 100%;
  max-width: 1800px;
  margin: 0 auto;
  padding-top: 2rem;
`

export const PageWrapper = styled.div`
  display: flex;
  gap: 2rem;
  padding: 2rem;
  background: transparent;
  min-height: calc(100vh - 190px);
  max-width: 1800px;
  margin: 0 auto;

  @media (max-width: 1024px) {
    flex-direction: column;
    gap: 1.5rem;
  }
`

export const LeftSection = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;

  @media (max-width: 1024px) {
    flex: none;
    width: 100%;
  }
`

export const ImageVisualizationPanel = styled.div`
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 1rem;
  height: 560px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;

  &:hover {
    border-color: rgba(167, 139, 250, 0.4);
  }

  @media (max-width: 1024px) {
    height: 520px;
  }
`

export const EmptyResultCard = styled.section`
  width: calc(100% - 2.5rem);
  max-width: 760px;
  min-height: 610px;
  margin: 0 auto 4rem;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: #e2e8f0;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 1.25rem;
  background: rgba(15, 15, 46, 0.6);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.4);

  h2 { margin: 0; color: white; font-size: 1.7rem; }
  > p { margin: 0; color: #cbd5e1; line-height: 1.6; }
`

export const EmptyPreview = styled.img`
  width: 100%;
  height: 210px;
  object-fit: contain;
  border-radius: 0.85rem;
  background: rgba(2, 6, 23, 0.64);
`

export const EmptyTipGrid = styled.div`
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;

  @media (max-width: 680px) { grid-template-columns: 1fr; }
`

export const EmptyTipItem = styled.div`
  min-height: 135px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.85rem;
  background: rgba(30, 41, 59, 0.4);

  span { font-size: 1.55rem; }
  strong { color: #f5f3ff; font-size: 0.9rem; }
  small { color: #94a3b8; line-height: 1.45; }
`

export const ImageStage = styled.div`
  position: relative;
  width: 100%;
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 8px;
  cursor: ${props => (props.$canPan ? (props.$dragging ? 'grabbing' : 'grab') : 'default')};
  touch-action: none;
  user-select: none;
`

export const PanZoomLayer = styled.div`
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  transform-origin: center center;
  will-change: transform;
`

export const UploadedImage = styled.img`
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 8px;
  pointer-events: none;
`

export const ConstellationOverlay = styled.svg`
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: hidden;

  .major-star {
    filter: drop-shadow(0 0 5px currentColor) drop-shadow(0 0 12px currentColor);
    animation: majorStarPulse 2.2s ease-in-out infinite;
  }

  .active-star {
    animation: selectedStarFlash 0.6s ease-in-out 3;
  }

  @keyframes majorStarPulse {
    0%, 100% { opacity: 0.78; }
    50% { opacity: 1; }
  }

  @keyframes selectedStarFlash {
    0%, 100% { opacity: 0.85; transform: scale(1); }
    50% { opacity: 1; transform: scale(2.4); }
  }
`

export const OverlayLegend = styled.div`
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  flex-shrink: 0;

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
`

export const OverlayLegendItem = styled.div`
  padding: 0.5rem 0.85rem;
  border-radius: 999px;
  color: white;
  font-size: 0.78rem;
  font-weight: 700;
  background: ${props => props.$color};
  border: 1px solid ${props => props.$borderColor};
  box-shadow: 0 0 10px ${props => props.$glowColor}, 0 0 24px ${props => props.$glowColor};
  backdrop-filter: blur(8px);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`

export const ImagePlaceholder = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  background: rgba(30, 41, 59, 0.4);
  color: #a78bfa;
  font-size: 3rem;
  border-radius: 8px;
`

export const ControlButtons = styled.div`
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  flex-shrink: 0;
`

export const ControlButton = styled.button`
  width: 40px;
  height: 40px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(30, 41, 59, 0.8);
  color: #a78bfa;
  cursor: pointer;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;

  &:hover {
    background: rgba(167, 139, 250, 0.2);
    border-color: rgba(167, 139, 250, 0.4);
    color: white;
    transform: scale(1.05);
  }

  &:active {
    transform: scale(0.95);
  }
`

export const DetailSection = styled.div`
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 2rem;
  max-height: 400px;
  overflow-y: auto;

  &:hover {
    border-color: rgba(167, 139, 250, 0.4);
  }

  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 4px;

    &:hover {
      background: rgba(255, 255, 255, 0.3);
    }
  }
`

export const RankBadge = styled.span`
  display: inline-block;
  background: rgba(167, 139, 250, 0.15);
  border: 1px solid rgba(167, 139, 250, 0.4);
  color: #a78bfa;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
`

export const ConstellationTitle = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;

  h2 {
    font-size: 1.8rem;
    color: white;
    margin: 0;
  }

  p {
    font-size: 1rem;
    color: #a78bfa;
    margin: 0;
  }
`

export const ConstellationDescription = styled.p`
  font-size: 0.95rem;
  color: #cbd5e1;
  line-height: 1.6;
  margin: 1rem 0;
`

export const SectionLabel = styled.h3`
  font-size: 1rem;
  color: #a78bfa;
  margin: 1.5rem 0 0.75rem 0;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 0.5rem;
`

export const MainStarsContainer = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin: 1rem 0;
`

export const StarChip = styled.span`
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #e2e8f0;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.85rem;
  cursor: ${props => (props.$available ? 'pointer' : 'default')};
  transition: all 0.3s ease;

  &:hover {
    border-color: rgba(167, 139, 250, 0.4);
    background: rgba(167, 139, 250, 0.1);
    transform: ${props => (props.$available ? 'translateY(-2px)' : 'none')};
  }

  ${props => props.$active && `
    color: white;
    background: rgba(167, 139, 250, 0.3);
    border-color: #a78bfa;
    box-shadow: 0 0 10px rgba(196, 181, 253, 0.5);
  `}
`

export const StorySection = styled.div`
  margin: 1.5rem 0;

  p {
    font-size: 0.9rem;
    color: #cbd5e1;
    line-height: 1.8;
    margin: 0 0 1rem 0;

    &:last-child {
      margin-bottom: 0;
    }
  }
`

export const RightSection = styled.div`
  flex: 0 0 40%;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  background: transparent;
  border: none;
  padding: 0;

  @media (max-width: 1024px) {
    flex: none;
    width: 100%;
  }
`

export const ResultHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;

  h2 {
    font-size: 1.5rem;
    color: white;
    margin: 0;
  }
`

export const ActionButtons = styled.div`
  display: flex;
  gap: 1rem;
`

export const ActionButton = styled.button`
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  border: none;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;

  ${props =>
    props.$variant === 'primary'
      ? `
    background: #a78bfa;
    color: #fff;

    &:hover {
      background: #c084fc;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(167, 139, 250, 0.4);
    }
  `
      : `
    background: rgba(30, 41, 59, 0.8);
    color: #a78bfa;
    border: 1px solid rgba(167, 139, 250, 0.3);

    &:hover {
      background: rgba(167, 139, 250, 0.2);
      border-color: #a78bfa;
      transform: translateY(-2px);
    }
  `}

  &:active {
    transform: translateY(0);
  }
`

export const ResultListContainer = styled.div`
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 1rem;
  overflow-y: auto;
  flex: 1;

  &:hover {
    border-color: rgba(167, 139, 250, 0.4);
  }


  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 4px;

    &:hover {
      background: rgba(255, 255, 255, 0.3);
    }
  }
`

export const ResultItem = styled.div`
  background: ${props => (props.$isSelected ? 'rgba(167, 139, 250, 0.15)' : 'rgba(30, 41, 59, 0.4)')};
  border: 1px solid ${props => (props.$isSelected ? '#a78bfa' : 'rgba(255, 255, 255, 0.08)')};
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 1rem;

  &:hover {
    background: rgba(167, 139, 250, 0.08);
    border-color: rgba(167, 139, 250, 0.4);
  }

  &:last-child {
    margin-bottom: 0;
  }
`

export const RankNumber = styled.div`
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: ${props => (props.$isSelected ? '#a78bfa' : 'rgba(30, 41, 59, 0.8)')};
  border: 1px solid ${props => (props.$isSelected ? '#a78bfa' : 'rgba(255, 255, 255, 0.15)')};
  color: ${props => (props.$isSelected ? '#fff' : '#a78bfa')};
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 700;
  flex-shrink: 0;
`

export const ResultInfo = styled.div`
  flex: 1;
  min-width: 0;
`

export const ResultName = styled.div`
  font-size: 1.1rem;
  color: white;
  font-weight: 600;
  margin-bottom: 0.5rem;
`

export const ResultPercentage = styled.div`
  font-size: 1.5rem;
  color: #a78bfa;
  font-weight: 700;
`

export const PercentageBar = styled.div`
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  margin-top: 0.5rem;
  overflow: hidden;
`

export const PercentageFill = styled.div`
  height: 100%;
  background: linear-gradient(90deg, #a78bfa, #c084fc);
  width: ${props => props.$percentage}%;
  border-radius: 3px;
  transition: width 0.3s ease;
`

export const ShareModal = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
`

export const ShareModalContent = styled.div`
  background: rgba(15, 15, 46, 0.95);
  border: 1px solid rgba(167, 139, 250, 0.4);
  border-radius: 12px;
  padding: 2rem;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);

  h3 {
    font-size: 1.3rem;
    color: white;
    margin: 0 0 1.5rem 0;
    text-align: center;
  }
`

export const ShareOptions = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`

export const ShareOption = styled.button`
  padding: 1rem;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  color: #e2e8f0;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 1rem;

  &:hover {
    background: rgba(167, 139, 250, 0.15);
    border-color: #a78bfa;
    color: white;
    transform: translateX(4px);
  }
`

export const CloseButton = styled.button`
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(30, 41, 59, 0.8);
  color: #a78bfa;
  font-size: 1.5rem;
  cursor: pointer;
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;

  &:hover {
    background: rgba(167, 139, 250, 0.2);
    border-color: #a78bfa;
    color: white;
  }
`