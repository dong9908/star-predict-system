import styled from 'styled-components'

export const PageContainer = styled.div`
  width: 100%;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  padding: 2rem 1rem;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
`

export const FormWrapper = styled.div`
  width: 100%;
  max-width: 600px;
`

export const PageHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
`

export const BackButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  background-color: transparent;
  color: #a78bfa;
  border: 1px solid rgba(147, 51, 234, 0.5);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 150ms ease-in-out;

  &:hover {
    background-color: rgba(147, 51, 234, 0.1);
    border-color: rgba(147, 51, 234, 0.8);
    color: #d8b4fe;
  }
`

export const PageTitle = styled.h1`
  font-size: 1.75rem;
  font-weight: 700;
  color: white;
  margin: 0;
`

export const FormCard = styled.div`
  padding: 2rem;
  border-radius: 0.75rem;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(147, 51, 234, 0.3);
`

export const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.5rem;

  &:last-of-type {
    margin-bottom: 0;
  }
`

export const Label = styled.label`
  font-size: 0.875rem;
  font-weight: 600;
  color: #cbd5e1;
  text-transform: capitalize;
`

export const InputWrapper = styled.div`
  display: ${props => (props.$flex ? 'flex' : 'block')};
  gap: ${props => (props.$gap ? props.$gap : '0')};
  align-items: ${props => (props.$flex ? 'center' : 'stretch')};
`

export const Input = styled.input`
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(147, 51, 234, 0.3);
  color: white;
  font-size: 0.875rem;
  font-family: inherit;
  transition: all 150ms ease-in-out;
  flex: ${props => (props.$flex ? props.$flex : '1')};

  &:focus {
    outline: none;
    border-color: rgba(147, 51, 234, 0.8);
    box-shadow: 0 0 0 3px rgba(147, 51, 234, 0.1);
  }

  &::placeholder {
    color: #64748b;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`

export const AtSymbol = styled.span`
  color: #a78bfa;
  font-weight: 600;
  padding: 0 0.5rem;
`

export const ErrorMessage = styled.p`
  font-size: 0.75rem;
  color: #f87171;
  margin: 0;
  margin-top: 0.25rem;
`

export const SuccessMessage = styled.p`
  font-size: 0.875rem;
  color: #10b981;
  margin: 0;
  margin-top: 0.25rem;
`

export const GeneralError = styled.div`
  padding: 1rem;
  border-radius: 0.5rem;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.3);
  color: #fca5a5;
  font-size: 0.875rem;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
`

export const SubmitButton = styled.button`
  width: 100%;
  padding: 1rem;
  border-radius: 0.5rem;
  background-color: #9333ea;
  color: white;
  font-size: 1rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 150ms ease-in-out;
  margin-top: 2rem;

  &:hover:not(:disabled) {
    background-color: #a855f7;
    box-shadow: 0 10px 15px -3px rgba(147, 51, 234, 0.25);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`

export const LoadingSpinner = styled.span`
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
`

export const PasswordRequirements = styled.div`
  font-size: 0.75rem;
  color: #cbd5e1;
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: rgba(147, 51, 234, 0.1);
  border-radius: 0.25rem;
  border-left: 2px solid rgba(147, 51, 234, 0.5);

  p {
    margin: 0.25rem 0;

    &:first-child {
      margin-top: 0;
    }
  }
`

export const FormDivider = styled.div`
  height: 1px;
  background: rgba(147, 51, 234, 0.2);
  margin: 1.5rem 0;
`

export const InfoText = styled.p`
  font-size: 0.75rem;
  color: #64748b;
  margin: 0;
  margin-top: 2rem;
  text-align: center;
`
