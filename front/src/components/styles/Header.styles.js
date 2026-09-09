import styled from 'styled-components'

const titleTextColors = {
  1: '#7dd3fc',
  2: '#d8b4fe',
  3: '#fcd34d',
  unavailable: '#fb7185',
}

const titleTextGlows = {
  1: 'rgba(56, 189, 248, 0.68)',
  2: 'rgba(168, 85, 247, 0.7)',
  3: 'rgba(245, 158, 11, 0.72)',
  unavailable: 'rgba(244, 63, 94, 0.72)',
}

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

  @media (max-width: 768px) {
    padding: 0 1rem;
  }
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

  @media (max-width: 768px) {
    font-size: 1.1rem;
  }
`

export const Nav = styled.nav`
  display: flex;
  align-items: center;
  gap: 2rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #cbd5e1;

  @media (max-width: 768px) {
    display: none;
  }
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

  @media (max-width: 768px) {
    display: none;
  }
`

export const UserIdentity = styled.div`
  display: flex;
  flex-direction: column;
  align-items: ${props => props.$mobile ? 'flex-start' : 'flex-end'};
  gap: 0.15rem;
  min-width: 0;
`

export const UserNameText = styled.span`
  color: #a78bfa;
  font-size: 0.9rem;
  font-weight: 700;
  line-height: 1.2;
`

export const UserTitleText = styled.span`
  max-width: 150px;
  overflow: hidden;
  color: ${props => props.$unavailable
    ? titleTextColors.unavailable
    : titleTextColors[props.$level] || titleTextColors[1]};
  font-size: 0.68rem;
  font-weight: 600;
  line-height: 1.2;
  text-shadow: ${props => `0 0 2px ${props.$unavailable
    ? titleTextGlows.unavailable
    : titleTextGlows[props.$level] || titleTextGlows[1]}`};
  text-overflow: ellipsis;
  white-space: nowrap;
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

export const HamburgerButton = styled.button`
  display: none;
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  transition: color 150ms ease-in-out;

  &:hover {
    color: #a855f7;
  }

  @media (max-width: 768px) {
    display: block;
  }
`

export const MobileMenuOverlay = styled.div`
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
  opacity: 0;
  transition: opacity 300ms ease-in-out;

  @media (max-width: 768px) {
    display: ${props => (props.isOpen ? 'block' : 'none')};
    opacity: ${props => (props.isOpen ? 1 : 0)};
  }
`

export const MobileMenu = styled.div`
  display: none;
  position: fixed;
  top: 0;
  right: 0;
  width: 80%;
  max-width: 300px;
  height: 100vh;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(12px);
  transform: translateX(${props => (props.isOpen ? '0' : '100%')});
  transition: transform 300ms ease-in-out;
  z-index: 1000;
  padding: 1.5rem;
  overflow-y: auto;

  @media (max-width: 768px) {
    display: block;
  }
`

export const MobileMenuClose = styled.button`
  display: none;
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  align-self: flex-end;
  margin-bottom: 1rem;

  @media (max-width: 768px) {
    display: block;
  }
`

export const MobileMenuList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`

export const MobileMenuItem = styled.button`
  background: none;
  border: none;
  color: ${props => (props.$active ? '#a78bfa' : '#cbd5e1')};
  font-size: 1rem;
  font-weight: ${props => (props.$active ? 600 : 500)};
  cursor: pointer;
  padding: 1rem 0;
  text-align: left;
  transition: all 150ms ease-in-out;
  border-bottom: 1px solid rgba(30, 41, 59, 0.5);
  border-left: 3px solid ${props => (props.$active ? '#a78bfa' : 'transparent')};
  padding-left: ${props => (props.$active ? 'calc(1rem - 3px)' : '1rem')};

  &:hover {
    color: white;
  }
`

export const MobileAuthButtons = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
  border-top: 1px solid rgba(30, 41, 59, 0.5);
  padding-top: 1rem;
`

export const MobileMenuUserInfo = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 0;
  border-bottom: 1px solid rgba(30, 41, 59, 0.5);
  margin-bottom: 1rem;
  color: #cbd5e1;
  font-size: 0.9rem;
`
