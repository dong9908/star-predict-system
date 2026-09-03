import styled from 'styled-components'

export const FormContainer = styled.div`
  width: 100%;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 1rem;

  @media (max-width: 768px) {
    align-items: flex-start;
    padding: 1rem;
    padding-top: 6rem;
    padding-bottom: 2rem;
  }
`

export const FormWrapper = styled.div`
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid #1e293b;
  padding: 2rem;
  border-radius: 1.5rem;
  backdrop-filter: blur(12px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.25);
  width: 100%;
  max-width: 28rem;

  @media (max-width: 768px) {
    padding: 1.5rem;
    border-radius: 1rem;
    max-width: 100%;
  }
`

export const Title = styled.h2`
  font-size: 1.5rem;
  font-weight: 700;
  text-align: center;
  color: white;
  margin: 0 0 1.5rem;

  @media (max-width: 768px) {
    font-size: 1.25rem;
    margin-bottom: 1.25rem;
  }
`

export const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 0.875rem;

  @media (max-width: 768px) {
    gap: 1.25rem;
  }
`

export const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
`

export const Label = styled.label`
  font-size: 0.75rem;
  font-weight: 500;
  color: #cbd5e1;
  margin-bottom: 0.25rem;

  @media (max-width: 768px) {
    font-size: 0.875rem;
    margin-bottom: 0.5rem;
  }
`

export const Input = styled.input`
  width: 100%;
  padding: 0.5rem 0.875rem;
  border-radius: 0.5rem;
  background-color: #030712;
  border: 1px solid #1e293b;
  font-size: 0.875rem;
  color: white;
  transition: border-color 150ms ease-in-out;
  height: auto;

  &::placeholder {
    color: #64748b;
  }

  &:focus {
    outline: none;
    border-color: #9333ea;
  }

  @media (max-width: 768px) {
    padding: 1rem;
    height: 3.5rem;
    font-size: 1rem;
  }
`

export const EmailGroup = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;

  @media (max-width: 768px) {
    gap: 0.75rem;
  }
`

export const EmailSeparator = styled.span`
  color: #64748b;
  font-size: 0.875rem;

  @media (max-width: 768px) {
    font-size: 1rem;
  }
`

export const CheckboxGroup = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-top: 0.25rem;
`

export const CheckboxInput = styled.input`
  width: 1rem;
  height: 1rem;
  cursor: pointer;
  accent-color: #9333ea;
`

export const CheckboxLabel = styled.label`
  font-size: 0.75rem;
  color: #94a3b8;
  cursor: pointer;
`

export const SubmitButton = styled.button`
  width: 100%;
  padding: 0.625rem;
  border-radius: 0.5rem;
  background-color: #9333ea;
  color: white;
  font-weight: 600;
  font-size: 0.875rem;
  border: none;
  cursor: pointer;
  transition: background-color 150ms ease-in-out;
  box-shadow: 0 10px 15px -3px rgba(147, 51, 234, 0.2);
  margin-top: 0.5rem;
  height: auto;

  &:hover {
    background-color: #a855f7;
  }

  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  @media (max-width: 768px) {
    padding: 1rem;
    height: 3.5rem;
    font-size: 1rem;
    margin-top: 1.5rem;
    margin-bottom: 1rem;
  }
`

export const SignupLink = styled.button`
  background: none;
  border: none;
  color: #a855f7;
  cursor: pointer;
  font-size: 0.75rem;
  transition: text-decoration 150ms ease-in-out;

  &:hover {
    text-decoration: underline;
  }

  @media (max-width: 768px) {
    font-size: 0.875rem;
  }
`
