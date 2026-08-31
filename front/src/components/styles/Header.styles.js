import styled from 'styled-components'

export const HeaderWrapper = styled.header`
  border-bottom: 1px solid rgba(30, 41, 59, 0.8);
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 50;
`

export const HeaderContainer = styled.div`
  max-width: 80rem;
  margin: 0 auto;
  padding: 0 1.5rem;
  height: 4rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
`

export const Logo = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  transition: opacity 150ms ease-in-out;

  &:hover {
    opacity: 0.8;
  }
`

export const LogoText = styled.span`
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.125rem;
  color: white;
`

export const Nav = styled.nav`
  display: flex;
  align-items: center;
  gap: 2rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #cbd5e1;
`

export const NavButton = styled.button`
  background: none;
  border: none;
  color: #cbd5e1;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: color 150ms ease-in-out;

  &:hover {
    color: white;
  }
`

export const AuthButtonsGroup = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
`

export const AuthButton = styled.button`
  padding: ${props => (props.variant === 'primary' ? '0.375rem 1rem' : '0.375rem 1rem')};
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 150ms ease-in-out;

  ${props => {
    if (props.variant === 'primary') {
      return `
        background-color: #9333ea;
        color: white;
        border: none;
        box-shadow: 0 10px 15px -3px rgba(147, 51, 234, 0.2);

        &:hover {
          background-color: #a855f7;
        }
      `
    } else {
      return `
        background: none;
        border: 1px solid #475569;
        color: #cbd5e1;

        &:hover {
          border-color: #64748b;
          color: white;
        }
      `
    }
  }}
`
