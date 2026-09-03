import styled from 'styled-components'

/* Hero Section */
export const HeroSection = styled.section`
  width: 100%;
  margin-bottom: 3rem;
  padding-top: 1.5rem;

  @media (max-width: 768px) {
    margin-bottom: 2rem;
    padding-top: 1rem;
  }
`

export const HeroGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 2rem;
  align-items: center;

  @media (max-width: 768px) {
    gap: 1.5rem;
  }
`

export const HeroContent = styled.div`
  grid-column: span 7;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;

  /* 1024px 이하: 상하 배치 */
  @media (max-width: 1024px) {
    grid-column: span 12;
  }

  /* 768px 이하: 모바일 최적화 */
  @media (max-width: 768px) {
    gap: 1rem;
  }
`

export const Badge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 0.75rem;
  border-radius: 9999px;
  background: rgba(76, 29, 149, 0.6);
  border: 1px solid rgba(147, 51, 234, 0.5);
  color: #d8b4fe;
  font-size: 0.75rem;
  font-weight: 600;
  width: fit-content;

  @media (max-width: 640px) {
    font-size: 0.65rem;
    padding: 0.5rem 0.6rem;
  }
`

export const Title = styled.h1`
  font-size: 1.25rem;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: white;
  margin: 0;

  /* 768px 이상: 태블릿 사이즈 */
  @media (min-width: 768px) {
    font-size: 2.25rem;
  }

  /* 1024px 이상: 데스크톱 사이즈 */
  @media (min-width: 1024px) {
    font-size: 3rem;
  }
`

export const ButtonGroup = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-top: 0.5rem;

  /* 768px 이하: 모바일 전체 너비, 버튼 스택 */
  @media (max-width: 768px) {
    flex-direction: column;
    gap: 0.75rem;
    width: 100%;
  }
`

export const PrimaryButton = styled.button`
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  background-color: #9333ea;
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: background-color 150ms ease-in-out;
  box-shadow: 0 10px 15px -3px rgba(147, 51, 234, 0.25);
  height: auto;
  white-space: nowrap;

  &:hover {
    background-color: #a855f7;
  }

  /* 768px 이하: 모바일 최적화 */
  @media (max-width: 768px) {
    width: 100%;
    padding: 1rem;
    height: 3.5rem;
    font-size: 1rem;
  }
`

export const ButtonIcon = styled.span`
  display: flex;
  align-items: center;
  justify-content: center;
`

export const SecondaryButton = styled.button`
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  background-color: #0f172a;
  border: 1px solid rgba(30, 41, 59, 0.8);
  color: #cbd5e1;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 150ms ease-in-out;
  height: auto;
  white-space: nowrap;

  &:hover {
    background-color: #1e293b;
  }

  /* 768px 이하: 모바일 최적화 */
  @media (max-width: 768px) {
    width: 100%;
    padding: 1rem;
    height: 3.5rem;
    font-size: 1rem;
  }
`

/* Sky Image Section */
export const ImageSection = styled.div`
  width: 100%;
  margin: 2rem 0;
  overflow: hidden;
  border-radius: 0.75rem;

  img {
    width: 100%;
    height: auto;
    display: block;
    object-fit: cover;
  }

  /* 768px 이하: 모바일 여백 축소 */
  @media (max-width: 768px) {
    margin: 1.5rem 0;
    border-radius: 0.5rem;
  }

  /* 640px 이하: 초소형 모바일 */
  @media (max-width: 640px) {
    margin: 1rem 0;
    border-radius: 0.375rem;
  }
`

/* Constellation Viewer Container */
export const ConstellationContainer = styled.div`
  grid-column: span 5;

  /* 1024px 이하: 전체 너비 */
  @media (max-width: 1024px) {
    grid-column: span 12;
  }
`

/* Feature Grid - 2칼럼 배치 */
export const FeatureGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  padding-top: 1rem;

  /* 768px 이하: 모바일 1칼럼 */
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  /* 640px 이하: 초소형 모바일 */
  @media (max-width: 640px) {
    gap: 0.75rem;
    padding-top: 0.5rem;
  }
`
