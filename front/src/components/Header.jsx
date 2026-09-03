import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, Menu, X } from 'lucide-react'
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
  HamburgerButton,
  MobileMenuOverlay,
  MobileMenu,
  MobileMenuClose,
  MobileMenuList,
  MobileMenuItem,
  MobileAuthButtons,
  MobileMenuUserInfo,
} from './styles/Header.styles'

function Header() {
  const navigate = useNavigate()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogoClick = () => {
    navigate('/')
    setMobileMenuOpen(false)
  }

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
      sessionStorage.removeItem('fortuneResult')
      sessionStorage.removeItem('fortuneConversationId')
      alert('로그아웃 되었습니다.')
      setMobileMenuOpen(false)
      navigate('/')
      window.location.reload() // 화면 상태 갱신을 위해 새로고침
    }
  }

  const handleMobileNavigation = (path) => {
    navigate(path)
    setMobileMenuOpen(false)
  }

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768) {
        setMobileMenuOpen(false)
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

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
          <NavButton onClick={() => navigate('/constellation-info')}>별자리 정보</NavButton>
          <NavButton onClick={() => navigate('/constellation-catalog')}>도감</NavButton>
          <NavButton onClick={() => navigate('/fortune-reading')}>운세</NavButton>
          <NavButton onClick={() => navigate('/mypage')}>마이 페이지</NavButton>
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

        <HamburgerButton onClick={() => setMobileMenuOpen(true)}>
          <Menu size={24} />
        </HamburgerButton>
      </HeaderContainer>

      <MobileMenuOverlay isOpen={mobileMenuOpen} onClick={() => setMobileMenuOpen(false)} />

      <MobileMenu isOpen={mobileMenuOpen}>
        <MobileMenuClose onClick={() => setMobileMenuOpen(false)}>
          <X size={24} />
        </MobileMenuClose>

        {user && (
          <MobileMenuUserInfo>
            <span>
              <strong style={{ color: '#a78bfa' }}>{user.name}</strong>님
            </span>
          </MobileMenuUserInfo>
        )}

        <MobileMenuList>
          <MobileMenuItem onClick={() => handleMobileNavigation('/')}>메인</MobileMenuItem>
          <MobileMenuItem onClick={() => handleMobileNavigation('/constellation-find')}>
            별자리 찾기
          </MobileMenuItem>
          <MobileMenuItem onClick={() => handleMobileNavigation('/constellation-location')}>
            별자리 위치 찾기
          </MobileMenuItem>
          <MobileMenuItem onClick={() => handleMobileNavigation('/constellation-info')}>
            별자리 정보
          </MobileMenuItem>
          <MobileMenuItem onClick={() => handleMobileNavigation('/constellation-catalog')}>
            도감
          </MobileMenuItem>
          <MobileMenuItem onClick={() => handleMobileNavigation('/fortune-reading')}>
            운세
          </MobileMenuItem>
          <MobileMenuItem onClick={() => handleMobileNavigation('/mypage')}>
            마이 페이지
          </MobileMenuItem>
        </MobileMenuList>

        <MobileAuthButtons>
          {user ? (
            <AuthButton $variant="primary" onClick={handleLogout} style={{ width: '100%' }}>
              로그아웃
            </AuthButton>
          ) : (
            <>
              <AuthButton
                $variant="outline"
                onClick={() => handleMobileNavigation('/login')}
                style={{ width: '100%' }}
              >
                로그인
              </AuthButton>
              <AuthButton
                $variant="primary"
                onClick={() => handleMobileNavigation('/signup')}
                style={{ width: '100%' }}
              >
                회원가입
              </AuthButton>
            </>
          )}
        </MobileAuthButtons>
      </MobileMenu>
    </HeaderWrapper>
  )
}

export default Header
