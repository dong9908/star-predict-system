import styled from 'styled-components'

export const PageWrapper = styled.div`
  display: flex;
  gap: 2rem;
  padding: 2rem;
  background: linear-gradient(135deg, #0f0f2e 0%, #1a0f3d 100%);
  min-height: 100vh;
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
  background: rgba(20, 10, 50, 0.6);
  border: 2px solid #a78bfa;
  border-radius: 12px;
  padding: 2rem;
  height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;

  @media (max-width: 1024px) {
    height: 300px;
  }
`

export const UploadedImage = styled.img`
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 8px;
`

export const ImagePlaceholder = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  background: rgba(167, 139, 250, 0.1);
  color: #a78bfa;
  font-size: 3rem;
  border-radius: 8px;
`

export const ControlButtons = styled.div`
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  display: flex;
  gap: 0.5rem;
  z-index: 10;
`

export const ControlButton = styled.button`
  width: 40px;
  height: 40px;
  border-radius: 8px;
  border: 1px solid #a78bfa;
  background: rgba(167, 139, 250, 0.2);
  color: #a78bfa;
  cursor: pointer;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;

  &:hover {
    background: rgba(167, 139, 250, 0.4);
    transform: scale(1.05);
  }

  &:active {
    transform: scale(0.95);
  }
`

export const DetailSection = styled.div`
  background: rgba(20, 10, 50, 0.6);
  border: 2px solid #a78bfa;
  border-radius: 12px;
  padding: 2rem;
  max-height: 400px;
  overflow-y: auto;

  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(167, 139, 250, 0.1);
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(167, 139, 250, 0.4);
    border-radius: 4px;

    &:hover {
      background: rgba(167, 139, 250, 0.6);
    }
  }
`

export const RankBadge = styled.span`
  display: inline-block;
  background: rgba(167, 139, 250, 0.3);
  border: 1px solid #a78bfa;
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
    color: #e2e8f0;
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
  border-bottom: 1px solid rgba(167, 139, 250, 0.3);
  padding-bottom: 0.5rem;
`

export const MainStarsContainer = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin: 1rem 0;
`

export const StarChip = styled.span`
  background: rgba(167, 139, 250, 0.15);
  border: 1px solid #a78bfa;
  color: #e2e8f0;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    background: rgba(167, 139, 250, 0.3);
    transform: translateY(-2px);
  }
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
    color: #e2e8f0;
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
    background: rgba(167, 139, 250, 0.2);
    color: #a78bfa;
    border: 1px solid #a78bfa;

    &:hover {
      background: rgba(167, 139, 250, 0.4);
      transform: translateY(-2px);
    }
  `}

  &:active {
    transform: translateY(0);
  }
`

export const ResultListContainer = styled.div`
  background: rgba(20, 10, 50, 0.6);
  border: 2px solid #a78bfa;
  border-radius: 12px;
  padding: 1rem;
  max-height: 500px;
  overflow-y: auto;
  flex: 1;

  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(167, 139, 250, 0.1);
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(167, 139, 250, 0.4);
    border-radius: 4px;

    &:hover {
      background: rgba(167, 139, 250, 0.6);
    }
  }
`

export const ResultItem = styled.div`
  background: ${props => (props.$isSelected ? 'rgba(167, 139, 250, 0.2)' : 'rgba(167, 139, 250, 0.05)')};
  border: 2px solid ${props => (props.$isSelected ? '#a78bfa' : 'rgba(167, 139, 250, 0.2)')};
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 1rem;

  &:hover {
    background: rgba(167, 139, 250, 0.15);
    border-color: #c084fc;
    transform: translateX(4px);
  }

  &:last-child {
    margin-bottom: 0;
  }
`

export const RankNumber = styled.div`
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: ${props => (props.$isSelected ? '#a78bfa' : 'rgba(167, 139, 250, 0.2)')};
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
  color: #e2e8f0;
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
  background: rgba(167, 139, 250, 0.2);
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
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`

export const ShareModalContent = styled.div`
  background: rgba(20, 10, 50, 0.95);
  border: 2px solid #a78bfa;
  border-radius: 12px;
  padding: 2rem;
  max-width: 400px;
  width: 90%;

  h3 {
    font-size: 1.3rem;
    color: #e2e8f0;
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
  background: rgba(167, 139, 250, 0.1);
  border: 1px solid #a78bfa;
  border-radius: 8px;
  color: #e2e8f0;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 1rem;

  &:hover {
    background: rgba(167, 139, 250, 0.2);
    transform: translateX(4px);
  }
`

export const CloseButton = styled.button`
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid #a78bfa;
  background: rgba(167, 139, 250, 0.2);
  color: #a78bfa;
  font-size: 1.5rem;
  cursor: pointer;
  position: absolute;
  top: 1rem;
  right: 1rem;
  transition: all 0.3s ease;

  &:hover {
    background: rgba(167, 139, 250, 0.4);
  }
`
