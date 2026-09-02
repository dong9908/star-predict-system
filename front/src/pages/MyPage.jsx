import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, Star } from 'lucide-react'
import {
  PageContainer,
  ProfileSection,
  ProfileIcon,
  ProfileInfo,
  UserName,
  ConstellationInfo,
  BadgeContainer,
  Badge,
  EditButton,
  TabMenu,
  Tab,
  ContentArea,
  SectionTitle,
  CardGrid,
  CharacteristicCard,
  CardIcon,
  CardContent,
  CardTitle,
  CardDescription,
  FooterText,
} from './styles/MyPage.styles'

const characteristics = [
  {
    id: 1,
    title: '별자리 알은',
    description: '별자리 여정을 시작한 탐험가',
    icon: '✦',
    borderColor: '#c084fc',
  },
  {
    id: 2,
    title: '별빛 관측자',
    description: '밤하늘을 구종한 바라본 관측가',
    icon: '✦',
    borderColor: '#60a5fa',
  },
  {
    id: 3,
    title: '별빛 추적자',
    description: '어린 별자리를 자아낸 탐험가',
    icon: '✦',
    borderColor: '#34d399',
  },
  {
    id: 4,
    title: '별자리 수집가',
    description: '다양한 별자리를 모은 수집가',
    icon: '✦',
    borderColor: '#fbbf24',
  },
  {
    id: 5,
    title: '우주 탐험가',
    description: '밤하늘 너머의 궁금 욕망',
    icon: '✦',
    borderColor: '#f87171',
  },
]

const badges = [
  { id: 1, label: '별자리 수집가', borderColor: '#fbbf24' },
]

const tabs = [
  { id: 'audience', label: '청중' },
  { id: 'background', label: '배경' },
  { id: 'profile', label: '프로필' },
]

function MyPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('audience')

  // 로컬 스토리지에서 로그인된 유저 정보 가져오기
  const userString = localStorage.getItem('user')
  const user = userString ? JSON.parse(userString) : null

  // 로그인하지 않은 경우 로그인 페이지로 리다이렉트
  if (!user) {
    return (
      <PageContainer>
        <div style={{ color: '#a78bfa', textAlign: 'center', padding: '3rem 1rem' }}>
          <p style={{ fontSize: '1.125rem', marginBottom: '1rem' }}>로그인이 필요합니다.</p>
          <button
            onClick={() => navigate('/login')}
            style={{
              padding: '0.75rem 1.5rem',
              borderRadius: '0.5rem',
              backgroundColor: '#9333ea',
              color: 'white',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '600',
            }}
          >
            로그인하기
          </button>
        </div>
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
          <ConstellationInfo>
            <Star size={16} color="#fbbf24" />
            획득한 별자리 6/88
          </ConstellationInfo>
          <BadgeContainer>
            {badges.map(badge => (
              <Badge key={badge.id} $borderColor={badge.borderColor}>
                {badge.label}
              </Badge>
            ))}
          </BadgeContainer>
        </ProfileInfo>

        <EditButton onClick={() => navigate('/edit-profile')}>회원 정보 수정</EditButton>
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
        {activeTab === 'audience' && (
          <>
            <SectionTitle>최극한 징조</SectionTitle>
            <CardGrid>
              {characteristics.map(char => (
                <CharacteristicCard key={char.id} $borderColor={char.borderColor}>
                  <CardIcon $borderColor={char.borderColor}>{char.icon}</CardIcon>
                  <CardContent>
                    <CardTitle>{char.title}</CardTitle>
                    <CardDescription>{char.description}</CardDescription>
                  </CardContent>
                </CharacteristicCard>
              ))}
            </CardGrid>
            <FooterText>
              최극한 징조를 선택하면 다른 징조로 정정할 수 있습니다.
            </FooterText>
          </>
        )}

        {activeTab === 'background' && (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#cbd5e1' }}>
            배경 탭 컨텐츠가 준비 중입니다.
          </div>
        )}

        {activeTab === 'profile' && (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#cbd5e1' }}>
            프로필 탭 컨텐츠가 준비 중입니다.
          </div>
        )}
      </ContentArea>
    </PageContainer>
  )
}

export default MyPage
