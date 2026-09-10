import styled from 'styled-components'

export const PageWrapper = styled.div`
  display: flex;
  gap: 2rem;
  padding: 2rem;
  background: #090916; /* 다른 페이지들과 일치하는 깔끔한 어두운 단색 배경으로 변경 */
  height: 100vh;
  width: 100%;
  max-width: 1800px;
  margin: 0 auto;
  box-sizing: border-box;
  align-items: stretch;

  @media (max-width: 1024px) {
    flex-direction: column;
    gap: 1.5rem;
    height: auto;
    min-height: 100vh;
    align-items: flex-start;
  }

  @media (max-width: 768px) {
    padding: 1rem;
    gap: 1rem;
  }
`

export const LeftSection = styled.div`
  flex: 1 1 0;
  min-width: 0;
  width: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: 100%;

  @media (max-width: 1024px) {
    flex: none;
    width: 100%;
    height: auto;
    order: 2;
  }
`

export const ConstellationListContainer = styled.div`
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 1rem;
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
  min-height: 0;

  /* 모바일 화면에서 카드가 4개 정도만 보이도록 높이 제한 */
  @media (max-width: 1024px) {
    max-height: 420px; /* 카드 크기에 맞춰 대략 4개 정도가 들어오는 높이 */
    flex: none;
  }

  &:hover {
    border-color: #a78bfa;
  }

  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(167, 139, 250, 0.3);
    border-radius: 4px;

    &:hover {
      background: rgba(167, 139, 250, 0.5);
    }
  }
`

export const VisualizationPanel = styled.div`
  width: 100%;
  min-width: 0;
  box-sizing: border-box;

  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 1rem;
  padding: 2rem;
  height: 400px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;

  &:hover {
    border-color: #a78bfa;
  }

  @media (max-width: 1024px) {
    height: 300px;
    flex-shrink: 1;
  }
`

export const ConstellationImage = styled.img`
  display: block;
  width: 100%;
  height: 100%;
  max-width: 100%;
  min-width: 0;
  object-fit: contain;
`

export const VisualizationCanvas = styled.svg`
  width: 100%;
  height: 100%;
`

export const ControlButtons = styled.div`
  position: absolute;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);

  display: flex;
  gap: 0.5rem;
  z-index: 10;
`

export const ControlButton = styled.button`
  width: 40px;
  height: 40px;
  border-radius: 8px;
  border: 1px solid rgba(167, 139, 250, 0.3);
  background: rgba(30, 41, 59, 0.8);
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
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 1rem;
  padding: 2rem;
  overflow-y: auto;
  flex: 1;
  min-height: 0;

  &:hover {
    border-color: #a78bfa;
  }

  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(167, 139, 250, 0.3);
    border-radius: 4px;

    &:hover {
      background: rgba(167, 139, 250, 0.5);
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
  position: relative;

  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(167, 139, 250, 0.3);
  color: #e2e8f0;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    border-color: #a78bfa;
    background: rgba(167, 139, 250, 0.1);
    transform: translateY(-2px);
  }

  &::after {
    content: '밝기는 숫자가 작을수록 밝습니다.';
    position: absolute;
    left: 50%;
    bottom: calc(100% + 8px);
    transform: translateX(-50%);

    background: rgba(30, 41, 59, 0.98);
    border: 1px solid rgba(167, 139, 250, 0.3);
    color: #e2e8f0;
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: normal;
    white-space: nowrap;

    opacity: 0;
    visibility: hidden;
    pointer-events: none;

    transition: opacity 0.2s ease;
    z-index: 100;
  }

  &:hover::after {
    opacity: 1;
    visibility: visible;
  }
`

export const StarEnglish = styled.span`
  font-size: 0.75rem;
  color: #94a3b8;
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
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 8px;
  padding: 1rem;
  text-align: center;

  .label {
    font-size: 0.75rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.5rem;
  }

  .value {
    font-size: 1.3rem;
    color: white;
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

/* 오른쪽 영역 바깥쪽 배경을 투명하게 만들어 전체 배경 그라데이션과 완전히 일치시킴 */
export const RightSection = styled.div`
  flex: 0 0 35%;
  min-width: 0;
  width: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: 100%;
  background: transparent;
  border: none;
  padding: 0;

  @media (max-width: 1024px) {
    flex: none;
    width: 100%;
    height: auto;
    order: 1;
  }
`

export const SearchContainer = styled.div`
  position: relative;
  /* 검색창 바깥의 엉뚱한 배경색 제거 */
  background: transparent;
  border: none;
  padding: 0;
`

export const SearchInput = styled.input`
  width: 100%;
  padding: 1rem;
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.3);
  color: white;
  font-size: 1rem;
  transition: all 0.3s ease;

  &::placeholder {
    color: #64748b;
  }

  &:focus {
    outline: none;
    border-color: #a78bfa;
    box-shadow: 0 0 10px rgba(167, 139, 250, 0.2);
  }
`



export const ConstellationCard = styled.div`
  position: relative;
  background: ${props => (props.$isSelected ? 'rgba(167, 139, 250, 0.15)' : 'rgba(30, 41, 59, 0.6)')};
  border: 1px solid ${props => (props.$isSelected ? '#a78bfa' : 'rgba(167, 139, 250, 0.2)')};
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 1rem;

  &:hover {
    background: rgba(167, 139, 250, 0.1);
    border-color: #a78bfa;
  }

  &:last-child {
    margin-bottom: 0;
  }
`

export const ConstellationIcon = styled.div`
  width: 70px;
  height: 70px;
  border-radius: 10px;
  overflow: hidden;
  flex-shrink: 0;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.02);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
`

export const ConstellationInfo = styled.div`
  flex: 1;
  min-width: 0;
`

export const ConstellationName = styled.div`
  font-size: 1rem;
  color: white;
  font-weight: 600;
  margin-bottom: 0.25rem;
`

export const ConstellationEnglish = styled.div`
  font-size: 0.85rem;
  color: #94a3b8;
`

export const EmptyState = styled.div`
  text-align: center;
  padding: 2rem 1rem;
  color: #94a3b8;
  font-size: 0.95rem;
`

export const LoadingState = styled.div`
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a78bfa;
  font-size: 1rem;
`

export const ConstellationCardLoading = styled.div`
  position: absolute;
  inset: 0;

  background: rgba(0, 0, 0, 0.6);

  display: flex;
  align-items: center;
  justify-content: center;

  color: white;
  font-size: 0.95rem;
  font-weight: 600;

  border-radius: 8px;

  z-index: 10;
`