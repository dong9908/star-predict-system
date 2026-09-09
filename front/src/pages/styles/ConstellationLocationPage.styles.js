import styled from 'styled-components'

export const PageContainer = styled.div`
  width: 100%;
  padding: 3rem 2rem;
  min-height: calc(100vh - 80px);
  box-sizing: border-box;

  @media (max-width: 768px) {
    padding: 1.5rem 1rem;
  }
`

export const ContentWrapper = styled.div`
  max-width: 1400px;
  margin: 0 auto;
`

export const PageHeader = styled.div`
  margin-bottom: 2.5rem;
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
  align-items: start;

  @media (max-width: 1024px) {
    display: flex;
    flex-direction: column;
  }
`

export const FormSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
  box-sizing: border-box;

  @media (max-width: 1024px) {
    order: 1;
  }
`

export const FormGroup = styled.div`
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 1rem;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  box-sizing: border-box;
  width: 100%;

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
  position: relative;
  width: 100%;
  box-sizing: border-box;
`

export const Input = styled.input`
  width: 100%;
  box-sizing: border-box;
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
  width: 100%;
  box-sizing: border-box;
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
  box-sizing: border-box;
  width: 100%;
  position: relative;

  display: flex;
  flex-direction: column;
  gap: 1.5rem;

  &:hover {
    border-color: #a78bfa;
  }

  @media (max-width: 1024px) {
    order: 2;
  }
`

export const VisualizationHeader = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0;
`

export const LocationNotice = styled.span`
  color: #64748b;
  font-size: 0.7rem;
  margin-top: 0.25rem;
`

export const ConstellationSearchWrapper = styled.div`
  position: relative;
  width: 100%;
  box-sizing: border-box;
`

export const ConstellationDropdown = styled.div`
  position: absolute;
  z-index: 10;
  top: calc(100% + 4px);
  left: 0;
  width: 100%;
  max-height: 240px;
  overflow-y: auto;

  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 0.5rem;
  background: rgba(30, 41, 59, 0.98);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  box-sizing: border-box;
`

export const ConstellationOption = styled.button`
  display: block;
  width: 100%;
  padding: 0.75rem 1rem;
  text-align: left;
  color: white;
  font-size: 0.875rem;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background 200ms ease;

  &:hover {
    background: rgba(167, 139, 250, 0.1);
  }
`

export const ConstellationNoResult = styled.div`
  position: absolute;
  z-index: 10;
  top: calc(100% + 4px);
  left: 0;
  width: 100%;
  padding: 0.75rem 1rem;
  color: #94a3b8;
  font-size: 0.875rem;
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 0.5rem;
  background: rgba(30, 41, 59, 0.98);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  box-sizing: border-box;
`

export const ConstellationImageBox = styled.div`
  width: 100%;
  min-height: 300px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 0.75rem;
  background: rgba(255, 255, 255, 0.02);
  overflow: hidden;
`

export const ConstellationImage = styled.img`
  width: 100%;
  max-width: 400px;
  height: auto;
  display: block;
`

export const ResultContainer = styled.div`
  background: rgba(20, 10, 50, 0.6);
  border: 2px solid #a78bfa;
  border-radius: 12px;
  padding: 20px;
  margin: 0;
  color: #e2e8f0;
  box-sizing: border-box;
  width: 100%;
`

export const ResultRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid rgba(167, 139, 250, 0.2);

  &:last-child {
    border-bottom: none;
  }
`

export const ResultLabel = styled.span`
  font-size: 14px;
  font-weight: 600;
  color: #a78bfa;
  min-width: 100px;
`

export const ResultValue = styled.span`
  font-size: 16px;
  font-weight: 500;
  color: #e2e8f0;
  text-align: right;
  flex: 1;
`

export const ResultActionWrapper = styled.div`
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(167, 139, 250, 0.2);
`

export const InfoLinkButton = styled.button`
  width: 100%;
  box-sizing: border-box;
  padding: 0.75rem 1.5rem;
  background: rgba(167, 139, 250, 0.15);
  border: 1px solid #a78bfa;
  border-radius: 0.5rem;
  color: #d8b4fe;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 300ms ease;

  &:hover {
    background: rgba(167, 139, 250, 0.3);
    color: white;
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(167, 139, 250, 0.2);
  }

  &:active {
    transform: translateY(0);
  }
`

export const BottomButtonWrapper = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid rgba(167, 139, 250, 0.2);
  margin-top: auto;
  box-sizing: border-box;
  width: 100%;
`

export const FortuneButton = styled.button`
  width: 100%;
  box-sizing: border-box;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #a78bfa, #d8b4fe);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 300ms ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(167, 139, 250, 0.3);
  }

  &:active {
    transform: translateY(0);
  }
`