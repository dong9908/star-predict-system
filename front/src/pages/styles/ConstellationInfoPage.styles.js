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

export const VisualizationPanel = styled.div`
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

export const VisualizationCanvas = styled.svg`
  width: 100%;
  height: 100%;
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

export const ObservationInfo = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin: 1rem 0;

  @media (max-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
  }
`

export const InfoCard = styled.div`
  background: rgba(167, 139, 250, 0.1);
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 8px;
  padding: 1rem;
  text-align: center;

  .label {
    font-size: 0.75rem;
    color: #a78bfa;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.5rem;
  }

  .value {
    font-size: 1.3rem;
    color: #e2e8f0;
    font-weight: 600;
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
  flex: 0 0 35%;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;

  @media (max-width: 1024px) {
    flex: none;
    width: 100%;
  }
`

export const SearchContainer = styled.div`
  position: relative;
`

export const SearchInput = styled.input`
  width: 100%;
  padding: 1rem;
  border: 2px solid #a78bfa;
  border-radius: 8px;
  background: rgba(20, 10, 50, 0.6);
  color: #e2e8f0;
  font-size: 1rem;
  transition: all 0.3s ease;

  &::placeholder {
    color: rgba(160, 174, 192, 0.6);
  }

  &:focus {
    outline: none;
    border-color: #c084fc;
    box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
  }
`

export const ConstellationListContainer = styled.div`
  background: rgba(20, 10, 50, 0.6);
  border: 2px solid #a78bfa;
  border-radius: 12px;
  padding: 1rem;
  max-height: 600px;
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

export const ConstellationCard = styled.div`
  background: ${props => (props.$isSelected ? 'rgba(167, 139, 250, 0.2)' : 'rgba(167, 139, 250, 0.05)')};
  border: 2px solid ${props => (props.$isSelected ? '#a78bfa' : 'rgba(167, 139, 250, 0.2)')};
  border-radius: 8px;
  padding: 1rem;
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

export const ConstellationIcon = styled.div`
  width: 50px;
  height: 50px;
  border-radius: 8px;
  background: rgba(167, 139, 250, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  flex-shrink: 0;
  color: #a78bfa;
`

export const ConstellationInfo = styled.div`
  flex: 1;
  min-width: 0;
`

export const ConstellationName = styled.div`
  font-size: 1rem;
  color: #e2e8f0;
  font-weight: 600;
  margin-bottom: 0.25rem;
`

export const ConstellationEnglish = styled.div`
  font-size: 0.85rem;
  color: #a78bfa;
`

export const EmptyState = styled.div`
  text-align: center;
  padding: 2rem 1rem;
  color: #a78bfa;
  font-size: 0.95rem;
`
