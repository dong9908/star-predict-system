import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { User, Star } from 'lucide-react'
import TitlePage from './TitlePage'
import {
  PageContainer,
  ProfileSection,
  ProfileIcon,
  ProfileInfo,
  UserName,
  ConstellationInfo,
  SelectedTitle,
  EditButton,
  TabMenu,
  Tab,
  ContentArea,
  LoginRequiredContainer,
  LoginRequiredText,
  LoginButton,
  EmptyTabMessage,
} from './styles/MyPage.styles'

const tabs = [
  { id: 'titles', label: '칭호' },
  { id: 'background', label: '배경' },
  { id: 'profile', label: '프로필' },
]

function MyPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [activeTab, setActiveTab] = useState('titles')
  const [titleSummary, setTitleSummary] = useState({
    discoveredCount: 0,
    totalConstellations: 0,
    titles: [],
  })

  // 로컬 스토리지에서 로그인된 유저 정보 가져오기
  const userString = localStorage.getItem('user')
  const user = userString ? JSON.parse(userString) : null
  const selectedTitle = titleSummary.titles.find(title => title.selected)
  const selectedTitleLevel = selectedTitle?.level || 1
  const isUnavailableTitle = selectedTitle?.id === 121

  // 로그인하지 않은 경우 로그인 페이지로 리다이렉트
  if (!user) {
    return (
      <PageContainer>
        <LoginRequiredContainer>
          <LoginRequiredText>로그인이 필요합니다.</LoginRequiredText>

          <LoginButton
            onClick={() => {
              navigate('/login', {
                state: {
                  from: location.pathname + location.search,
                },
              })
            }}
          >
            로그인하기
          </LoginButton>
        </LoginRequiredContainer>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      {/* 프로필 섹션 */}
      <ProfileSection>
        <ProfileIcon>
          <User size={48} color="#a78bfa" />
        </ProfileIcon>

        <ProfileInfo>
          <UserName>{user.name}</UserName>
          <SelectedTitle
            $selected={Boolean(selectedTitle)}
            $level={selectedTitleLevel}
            $unavailable={isUnavailableTitle}
          >
            {selectedTitle ? `✦ ${selectedTitle.name}` : '대표 칭호를 선택해주세요'}
          </SelectedTitle>
          <ConstellationInfo>
            <Star size={16} color="#fbbf24" />
            발견한 별자리 {titleSummary.discoveredCount}/{titleSummary.totalConstellations}
          </ConstellationInfo>
        </ProfileInfo>

        <EditButton onClick={() => navigate('/edit-profile')}>
          회원 정보 수정
        </EditButton>
      </ProfileSection>

      {/* 탭 메뉴 */}
      <TabMenu>
        {tabs.map(tab => (
          <Tab
            key={tab.id}
            $active={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </Tab>
        ))}
      </TabMenu>

      {/* 콘텐츠 영역 */}
      <ContentArea>
        {activeTab === 'titles' && <TitlePage onDataLoaded={setTitleSummary} />}

        {activeTab === 'background' && (
          <EmptyTabMessage>
            배경 탭 컨텐츠가 준비 중입니다.
          </EmptyTabMessage>
        )}

        {activeTab === 'profile' && (
          <EmptyTabMessage>
            프로필 탭 컨텐츠가 준비 중입니다.
          </EmptyTabMessage>
        )}
      </ContentArea>
    </PageContainer>
  )
}

export default MyPage
