import styled from 'styled-components'

export const PageContainer = styled.div`
  width: 100%;
  padding: 3rem 2rem;
  min-height: calc(100vh - 80px);
`

export const ContentWrapper = styled.div`
  max-width: 1400px;
  margin: 0 auto;
`

export const PageHeader = styled.div`
  margin-bottom: 3rem;
`

export const PageTitle = styled.h1`
  font-size: 2rem;
  color: white;
  margin-bottom: 0.5rem;

  @media (max-width: 768px) {
    font-size: 1.5rem;
  }
`

export const PageDescription = styled.p`
  color: #cbd5e1;
  font-size: 1rem;
`

export const MainContainer = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  align-items: flex-start;

  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
  }
`

export const FormSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`

export const FormGroup = styled.div`
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 1rem;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.3);

  &:hover {
    border-color: #a78bfa;
  }
`

export const FormGroupNumber = styled.span`
  display: inline-block;
  color: #a78bfa;
  font-weight: 600;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
`

export const FormGroupTitle = styled.h3`
  color: white;
  font-size: 1rem;
  margin-bottom: 1rem;
`

export const FormGroupContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
`

export const Input = styled.input`
  padding: 0.75rem 1rem;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 0.5rem;
  color: white;
  font-size: 0.875rem;

  &::placeholder {
    color: #64748b;
  }

  &:focus {
    outline: none;
    border-color: #a78bfa;
    box-shadow: 0 0 10px rgba(167, 139, 250, 0.2);
  }
`

export const LocationCheckBox = styled.label`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #cbd5e1;
  font-size: 0.875rem;
  cursor: pointer;

  input {
    cursor: pointer;
  }
`

export const LocationButton = styled.button`
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

export const CheckStatus = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #10b981;
  font-size: 0.875rem;
  margin-top: 0.5rem;
`

export const VisualizationSection = styled.div`
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 1rem;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  min-height: 500px;
  position: relative;

  &:hover {
    border-color: #a78bfa;
  }

  @media (max-width: 1024px) {
    min-height: 400px;
  }
`

export const StepLabel = styled.span`
  position: absolute;
  top: 1.5rem;
  right: 1.5rem;
  font-size: 0.75rem;
  color: #a78bfa;
  background: rgba(167, 139, 250, 0.1);
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  border: 1px solid rgba(167, 139, 250, 0.3);
`

export const Canvas = styled.canvas`
  width: 100%;
  height: 100%;
  display: block;
`

export const VisualizationPlaceholder = styled.div`
  text-align: center;
  color: #cbd5e1;

  p {
    margin: 0;
    font-size: 0.875rem;
  }
`
export const LocationNotice = styled.span`
  color: #64748b;
  font-size: 0.7rem;
  margin-top: 0.25rem;
`