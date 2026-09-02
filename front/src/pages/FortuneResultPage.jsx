import { useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import {
  PageContainer,
  ContentWrapper,
  PageHeader,
  PageTitle,
  PageSubtitle,
  UserInfoSection,
  UserInfo,
  ConstellationIcon,
  UserDetails,
  UserName,
  UserMeta,
  FortuneScore,
  ScoreLabel,
  ScoreValue,
  DateSection,
  DateText,
  SummarySection,
  SectionTitle,
  SummaryContent,
  CategoriesGrid,
  CategoryCard,
  CardHeader,
  CardIcon,
  CardTitle,
  StarRating,
  Star,
  CardContent,
  AdviceSection,
  AdviceContent,
  FooterInfo,
  FooterText,
  BackButton,
} from './styles/FortuneResultPage.styles'

const fortuneCategories = [
  {
    id: 'love',
    title: '사랑운',
    icon: '💘',
    score: 4,
    borderColor: '#ec4899',
    content: '사랑과 관련하여 좋은 기운이 감돕니다. 주변 사람들과의 관계가 더욱 돈독해질 시간입니다. 새로운 만남이 있다면 용기 있게 발을 내디뎌 보세요.',
  },
  {
    id: 'wealth',
    title: '재물운',
    icon: '💰',
    score: 3,
    borderColor: '#f59e0b',
    content: '재정 운이 평온하게 흐르는 하루입니다. 무분별한 지출을 피하고 계획적인 소비를 하면 좋은 결과를 얻을 수 있습니다. 투자는 신중히 결정하세요.',
  },
  {
    id: 'health',
    title: '건강운',
    icon: '🏥',
    score: 5,
    borderColor: '#10b981',
    content: '신체와 정신이 모두 좋은 상태입니다. 꾸준한 운동과 충분한 휴식으로 이 좋은 운을 유지하세요. 스트레스 관리도 중요한 날입니다.',
  },
  {
    id: 'career',
    title: '직업운',
    icon: '💼',
    score: 4,
    borderColor: '#3b82f6',
    content: '업무에서의 집중력이 높아지는 시간입니다. 미루던 일들을 처리하기 좋은 날이 될 것입니다. 동료들과의 소통도 원활할 것으로 보입니다.',
  },
  {
    id: 'relationship',
    title: '인간관계운',
    icon: '👥',
    score: 5,
    borderColor: '#a855f7',
    content: '인간관계에서 긍정적인 변화가 일어나는 날입니다. 소중한 사람들과의 시간을 소중히 여기세요. 좋은 사람을 만날 가능성도 높습니다.',
  },
]

function FortuneResultPage() {
  const navigate = useNavigate()

  const userString = localStorage.getItem('user')
  const user = userString ? JSON.parse(userString) : null

  if (!user) {
    return (
      <PageContainer>
        <ContentWrapper>
          <PageHeader>
            <PageTitle>로그인이 필요합니다</PageTitle>
            <PageSubtitle>운세 결과를 보려면 로그인해주세요</PageSubtitle>
          </PageHeader>
          <div style={{ textAlign: 'center', marginTop: '3rem' }}>
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
        </ContentWrapper>
      </PageContainer>
    )
  }

  const today = new Date()
  const dateStr = `${today.getFullYear()}년 ${today.getMonth() + 1}월 ${today.getDate()}일 ${{
    0: '일요일',
    1: '월요일',
    2: '화요일',
    3: '수요일',
    4: '목요일',
    5: '금요일',
    6: '토요일',
  }[today.getDay()]}`

  const renderStars = (score) => {
    return Array.from({ length: 5 }).map((_, index) => (
      <Star key={index} $filled={index < score}>
        ★
      </Star>
    ))
  }

  return (
    <PageContainer>
      <ContentWrapper>
        <BackButton onClick={() => navigate('/fortune-reading')}>
          <ChevronLeft size={20} />
          돌아가기
        </BackButton>

        <PageHeader>
          <PageTitle>✦ 오늘의 운세 상세 결과</PageTitle>
          <PageSubtitle>전문 점술가와 함께하는 오늘의 메시지</PageSubtitle>
        </PageHeader>

        {/* 사용자 정보 섹션 */}
        <UserInfoSection>
          <UserInfo>
            <ConstellationIcon>♑</ConstellationIcon>
            <UserDetails>
              <UserName>{user.name}</UserName>
              <UserMeta>{user.birthDate} · {user.gender}</UserMeta>
            </UserDetails>
          </UserInfo>
          <FortuneScore>
            <ScoreLabel>행운지수</ScoreLabel>
            <ScoreValue>88</ScoreValue>
          </FortuneScore>
        </UserInfoSection>

        {/* 날짜 정보 */}
        <DateSection>
          <DateText>{dateStr}</DateText>
        </DateSection>

        {/* 종합 운세 */}
        <SummarySection>
          <SectionTitle>✦ 오늘의 종합 운세</SectionTitle>
          <SummaryContent>
            <p>
              오늘은 펀소보다 직감이 돋보나는 하루입니다. 오른쪽 직감을 믿고 행동했을 때는 도움이 지갈 길 있습니다.
              가끔 숨소 놓을 정도로 직장이 거칠 것 수도 있어요.
            </p>
            <p>
              가족과 가지민 느는 슬픔을 한잔 자중을 가거울 수 있습니다. 시들 너무 과심하지 마세요.
            </p>
            <p>
              아래에서 오늘의 운세를 카테고리별로 확인해 보세요. 각 영역에서의 운의 흐름을 이해하면 오늘의 하루를 더욱 의미 있게 보낼 수 있습니다.
            </p>
          </SummaryContent>
        </SummarySection>

        {/* 카테고리별 운세 */}
        <CategoriesGrid>
          {fortuneCategories.map(category => (
            <CategoryCard key={category.id} $borderColor={category.borderColor}>
              <CardHeader>
                <CardIcon>{category.icon}</CardIcon>
                <CardTitle>{category.title}</CardTitle>
              </CardHeader>
              <StarRating>{renderStars(category.score)}</StarRating>
              <CardContent>{category.content}</CardContent>
            </CategoryCard>
          ))}
        </CategoriesGrid>

        {/* 조언 섹션 */}
        <AdviceSection>
          <SectionTitle>✦ 오늘의 조언</SectionTitle>
          <AdviceContent>
            <p>
              오늘은 변화의 바람이 불어오는 시간입니다. 새로운 결정을 내려야 한다면 이 시기를 활용해 보세요.
              직감과 이성의 균형을 맞추면 최고의 결과를 얻을 수 있습니다.
            </p>
            <p>
              💡 오늘을 더 행운으로 만드는 팁: 아침의 차분한 시간을 통해 자신의 감정을 정리하고,
              중요한 결정은 오후 3시 이후에 내리는 것을 추천합니다.
            </p>
          </AdviceContent>
        </AdviceSection>

        {/* 하단 정보 */}
        <FooterInfo>
          <FooterText>✦ 오늘의 운세는 자정에 갱신됩니다</FooterText>
          <FooterText>이 운세는 재미와 참고를 위한 것이며, 실제 결과와 다를 수 있습니다.</FooterText>
        </FooterInfo>
      </ContentWrapper>
    </PageContainer>
  )
}

export default FortuneResultPage
