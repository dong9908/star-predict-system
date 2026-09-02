import styled from 'styled-components'

export const PageContainer = styled.div`
  width: 100%;
  padding: 3rem 2rem;
  min-height: calc(100vh - 80px);
`

export const ContentWrapper = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`

export const ProcessIndicator = styled.div`
  display: flex;
  justify-content: center;
  gap: 2rem;
  margin-bottom: 3rem;
  align-items: center;

  @media (max-width: 768px) {
    gap: 1rem;
  }
`

export const ProcessStep = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  position: relative;

  &::after {
    content: '';
    position: absolute;
    width: 3rem;
    height: 2px;
    background: linear-gradient(90deg, #a78bfa, transparent);
    top: 1.5rem;
    right: -2.5rem;

    @media (max-width: 768px) {
      width: 1.5rem;
      right: -1.8rem;
    }
  }

  &:last-child::after {
    display: none;
  }
`

export const StepCircle = styled.div`
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  border: 2px solid #a78bfa;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: #a78bfa;
  background: rgba(167, 139, 250, 0.1);

  ${props => props.$active && `
    background: #a78bfa;
    color: white;
    box-shadow: 0 0 20px rgba(167, 139, 250, 0.5);
  `}
`

export const StepLabel = styled.span`
  font-size: 0.875rem;
  color: #cbd5e1;
  text-align: center;
`

export const MainTitle = styled.h1`
  font-size: 2rem;
  color: white;
  text-align: center;
  margin-bottom: 1rem;

  @media (max-width: 768px) {
    font-size: 1.5rem;
  }
`

export const MainDescription = styled.p`
  font-size: 1rem;
  color: #cbd5e1;
  text-align: center;
  margin-bottom: 3rem;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
`

export const UploadArea = styled.div`
  border: 2px dashed #a78bfa;
  border-radius: 1rem;
  padding: 3rem;
  background: rgba(167, 139, 250, 0.05);
  text-align: center;
  cursor: pointer;
  transition: all 300ms ease;
  margin-bottom: 3rem;

  &:hover {
    background: rgba(167, 139, 250, 0.1);
    border-color: #d8b4fe;
  }

  ${props => props.$dragActive && `
    background: rgba(167, 139, 250, 0.15);
    border-color: #d8b4fe;
    transform: scale(1.02);
  `}

  @media (max-width: 768px) {
    padding: 2rem 1rem;
  }
`

export const UploadIcon = styled.div`
  font-size: 3rem;
  margin-bottom: 1rem;
`

export const UploadLabel = styled.label`
  display: block;
  cursor: pointer;
`

export const UploadText = styled.p`
  color: white;
  font-size: 1.125rem;
  margin-bottom: 0.5rem;
`

export const UploadSubText = styled.p`
  color: #a78bfa;
  font-size: 0.875rem;
  margin-bottom: 1rem;
`

export const FileInput = styled.input`
  display: none;
`

export const SelectButton = styled.button`
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #a78bfa, #d8b4fe);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 300ms ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(167, 139, 250, 0.3);
  }
`

export const FeaturesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  margin-top: 3rem;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`

export const FeatureBox = styled.div`
  padding: 2rem;
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 1rem;
  background: rgba(167, 139, 250, 0.05);
  text-align: center;
  transition: all 300ms ease;

  &:hover {
    border-color: #a78bfa;
    background: rgba(167, 139, 250, 0.1);
    transform: translateY(-4px);
  }
`

export const FeatureIcon = styled.div`
  font-size: 2rem;
  margin-bottom: 1rem;
`

export const FeatureTitle = styled.h3`
  color: white;
  font-size: 1rem;
  margin-bottom: 0.5rem;
`

export const FeatureDescription = styled.p`
  color: #cbd5e1;
  font-size: 0.875rem;
`
