import { useState } from 'react'
import { Gift } from 'lucide-react'
import {
  PageContainer,
  ContentWrapper,
  PageTitle,
  PageSubtitle,
  UserInfoBox,
  UserInfoContent,
  ConstellationInfo,
  ConstellationIcon,
  ConstellationDetails,
  ConstellationName,
  ConstellationMetaInfo,
  DetailInfo,
  DetailLabel,
  ActionButton,
  FortuneBox,
  FortuneTitle,
  FortuneDate,
  FortuneContent,
  PremiumBox,
  PremiumContent,
  PremiumIcon,
  PremiumInfo,
  PremiumTitle,
  PremiumDescription,
  PriceSection,
  Price,
  BuyButton,
} from './styles/FortuneReadingPage.styles'

function FortuneReadingPage() {
  const [user] = useState({
    constellation: '염소자리',
    icon: '♑',
    birthDate: '2000.04.12',
    gender: '남성',
  })

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

  return (
    <PageContainer>
      <ContentWrapper>
        <PageTitle>✦ 오늘의 운세 확인</PageTitle>
        <PageSubtitle>
          내 정보를 확인하고 오늘의 운세를 읽어보세요
        </PageSubtitle>

        {/* User Info */}
        <UserInfoBox>
          <UserInfoContent>
            <ConstellationInfo>
              <ConstellationIcon>{user.icon}</ConstellationIcon>
              <ConstellationDetails>
                <ConstellationName>{user.constellation}</ConstellationName>
                <ConstellationMetaInfo>{user.birthDate} · {user.gender}</ConstellationMetaInfo>
              </ConstellationDetails>
            </ConstellationInfo>
            <DetailInfo>
              <DetailLabel>🌟</DetailLabel>
              <span>별자리 정보 수정 가능</span>
            </DetailInfo>
          </UserInfoContent>
          <ActionButton>
            ✓ 별자리 기본 문석
          </ActionButton>
        </UserInfoBox>

        {/* Fortune Content */}
        <FortuneBox>
          <FortuneTitle>
            ✦ 오늘의 종합 운세
          </FortuneTitle>
          <FortuneDate>{dateStr}</FortuneDate>
          <FortuneContent>
            <p>
              오늘은 펀소보다 직감이 돋보나는 하루입니다. 오른쪽 직감을 믿고 행동했을 때는 도움이 지갈 길 있습니다. 가끔 숨소 놓을 정도로 직장이 거칠 것 수도 있어요.
            </p>
            <p>
              가족과 가지민 ↓ 느는 슬픔을 한잔 자중을 가거울 수 있습니다. 시들 너문 과심하지 마세요.
            </p>
            <p>
              아래에서 오늘의 운세 상세 내용을 확인해 보세요.
            </p>
          </FortuneContent>
        </FortuneBox>

        {/* Premium Fortune */}
        <PremiumBox>
          <PremiumContent>
            <PremiumIcon>
              <Gift size={24} color="white" />
            </PremiumIcon>
            <PremiumInfo>
              <PremiumTitle>운세 상세 내용이 궁금하신가요?</PremiumTitle>
              <PremiumDescription>
                전문 점술가와 함께하는 오늘의 메시지를 받아보세요.
              </PremiumDescription>
            </PremiumInfo>
          </PremiumContent>
          <PriceSection>
            <Price>₩1,900</Price>
            <BuyButton>
              💳 ₩1,900 결제하고 운세 전체 보기
            </BuyButton>
          </PriceSection>
        </PremiumBox>
      </ContentWrapper>
    </PageContainer>
  )
}

export default FortuneReadingPage
