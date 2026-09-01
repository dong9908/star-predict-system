import { useNavigate } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { logoutAPI } from '../api/auth'
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

  // 1. 로컬 스토리지에서 로그인된 유저 정보 가져오기
  const userString = localStorage.getItem('user')
  const user = userString ? JSON.parse(userString) : null

  // 2. 로그아웃 핸들러 (백엔드 쿠키 삭제 + 로컬 스토리지 삭제)
  const handleLogout = async () => {
    try {
      await logoutAPI() // 백엔드 쿠키(refreshToken) 만료 처리 요청
    } catch (error) {
      console.error('로그아웃 요청 중 오류 발생:', error)
    } finally {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('user')
      alert('로그아웃 되었습니다.')
      navigate('/')
      window.location.reload() // 화면 상태 갱신을 위해 새로고침
    }
  }

  return (
    <HeaderWrapper>
      <HeaderContainer>
        <Logo onClick={handleLogoClick}>
          <Sparkles size={24} color="#a78bfa" />
          <LogoText>ASTRA</LogoText>
        </Logo>

        <Nav>
          <NavButton onClick={() => navigate('/')}>메인</NavButton>
          <NavButton onClick={() => navigate('/constellation-find')}>별자리 찾기</NavButton>
          <NavButton onClick={() => navigate('/constellation-location')}>별자리 위치</NavButton>
          <NavButton onClick={() => navigate('/')}>별자리 정보</NavButton>
          <NavButton onClick={() => navigate('/constellation-catalog')}>도감</NavButton>
          <NavButton onClick={() => navigate('/fortune-reading')}>운세</NavButton>
          <NavButton onClick={() => navigate('/')}>결제</NavButton>
        </Nav>

        <AuthButtonsGroup>
          {user ? (
            // 로그인 상태일 때 표시할 UI
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <span style={{ fontSize: '0.9rem', color: '#e2e8f0' }}>
                <strong style={{ color: '#a78bfa' }}>{user.name}</strong>님
              </span>
              <AuthButton $variant="outline" onClick={handleLogout}>
                로그아웃
              </AuthButton>
            </div>
          ) : (
            // 비로그인 상태일 때 표시할 UI
            <>
              <AuthButton $variant="outline" onClick={() => navigate('/login')}>
                로그인
              </AuthButton>
              <AuthButton $variant="primary" onClick={() => navigate('/signup')}>
                회원가입
              </AuthButton>
            </>
          )}
        </AuthButtonsGroup>
      </HeaderContainer>
    </HeaderWrapper>
  )
}

export default Header