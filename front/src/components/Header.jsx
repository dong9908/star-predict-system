import { useNavigate } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import {
  HeaderWrapper,
  HeaderContainer,
  Logo,
  LogoText,
  Nav,
  NavButton,
  AuthButtonsGroup,
  AuthButton,
} from './styles/Header.styles'

function Header() {
  const navigate = useNavigate()

  const handleLogoClick = () => navigate('/')

  return (
    <HeaderWrapper>
      <HeaderContainer>
        <Logo onClick={handleLogoClick}>
          <Sparkles size={24} color="#a78bfa" />
          <LogoText>ASTRA</LogoText>
        </Logo>

        <Nav>
          <NavButton onClick={() => navigate('/')}>메인</NavButton>
          <NavButton onClick={() => navigate('/')}>별자리 찾기</NavButton>
          <NavButton onClick={() => navigate('/')}>별자리 위치</NavButton>
          <NavButton onClick={() => navigate('/')}>별자리 정보</NavButton>
          <NavButton onClick={() => navigate('/')}>도감</NavButton>
          <NavButton onClick={() => navigate('/')}>운세</NavButton>
          <NavButton onClick={() => navigate('/')}>결제</NavButton>
        </Nav>

        <AuthButtonsGroup>
          <AuthButton variant="outline" onClick={() => navigate('/login')}>
            로그인
          </AuthButton>
          <AuthButton variant="primary" onClick={() => navigate('/signup')}>
            회원가입
          </AuthButton>
        </AuthButtonsGroup>
      </HeaderContainer>
    </HeaderWrapper>
  )
}

export default Header
