import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Gift } from 'lucide-react'
import { getMyInfoAPI } from '../api/auth'
import { createInitialFortuneAPI } from '../api/fortune'
import { getPaymentAccessAPI, readyPaymentAPI } from '../api/payment'
import {
  PageContainer, ContentWrapper, PageTitle, PageSubtitle, UserInfoBox,
  UserInfoContent, ConstellationInfo, ConstellationIcon, ConstellationDetails,
  ConstellationName, ConstellationMetaInfo, DetailInfo, DetailLabel,
  ActionButton, FortuneBox, FortuneTitle, FortuneDate, FortuneContent,
  PremiumBox, PremiumContent, PremiumIcon, PremiumInfo, PremiumTitle,
  PremiumDescription, PriceSection, Price, BuyButton,
} from './styles/FortuneReadingPage.styles'

const formatDate = value => value ? String(value).replaceAll('-', '.') : '생년월일 정보 없음'

const formatToday = () => new Intl.DateTimeFormat('ko-KR', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
}).format(new Date())

function FortuneReadingPage() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [checkingAccess, setCheckingAccess] = useState(false)
  const accessCheckStarted = useRef(false)

  useEffect(() => {
    if (accessCheckStarted.current) return undefined
    accessCheckStarted.current = true

    const loadUser = async () => {
      const storedUser = localStorage.getItem('user')
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser))
        } catch {
          localStorage.removeItem('user')
        }
      }

      const accessToken = localStorage.getItem('accessToken')
      if (!accessToken) {
        navigate('/login', { replace: true })
        return
      }

      setCheckingAccess(true)
      try {
        const myInfo = await getMyInfoAPI(accessToken)
        setUser(current => ({ ...current, ...myInfo }))

        const access = await getPaymentAccessAPI(accessToken)
        if (!access.hasFortuneAccess) return

        const initialFortune = await createInitialFortuneAPI(accessToken)
        const resultState = { fortune: initialFortune, user: myInfo }
        sessionStorage.removeItem('fortuneConversationId')
        sessionStorage.setItem('fortuneResult', JSON.stringify(resultState))
        navigate('/fortune-result', { replace: true, state: resultState })
      } catch (error) {
        if (error.status === 401) {
          localStorage.removeItem('accessToken')
          localStorage.removeItem('user')
          navigate('/login', { replace: true })
        }
      } finally {
        setCheckingAccess(false)
      }
    }

    loadUser()
    return undefined
  }, [navigate])

  const handleBuyClick = async () => {
    const accessToken = localStorage.getItem('accessToken')
    if (!accessToken) {
      navigate('/login')
      return
    }

    setCheckingAccess(true)
    try {
      const myInfo = await getMyInfoAPI(accessToken)
      const access = await getPaymentAccessAPI(accessToken)

      if (access.hasFortuneAccess) {
        const initialFortune = await createInitialFortuneAPI(accessToken)
        const resultState = { fortune: initialFortune, user: myInfo }
        sessionStorage.removeItem('fortuneConversationId')
        sessionStorage.setItem('fortuneResult', JSON.stringify(resultState))
        navigate('/fortune-result', { state: resultState })
        return
      }

      const payment = await readyPaymentAPI(accessToken)
      sessionStorage.setItem('pendingPaymentOrderId', payment.partnerOrderId)

      const isMobile = window.matchMedia('(max-width: 768px)').matches
        || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
      const redirectUrl = isMobile
        ? payment.mobileRedirectUrl || payment.appRedirectUrl || payment.redirectUrl
        : payment.pcRedirectUrl || payment.redirectUrl

      if (!redirectUrl) throw new Error('카카오페이 이동 주소를 받지 못했습니다.')
      window.location.assign(redirectUrl)
    } catch (error) {
      if (error.status === 401 || error.message.includes('인증')) {
        localStorage.removeItem('accessToken')
        localStorage.removeItem('user')
        navigate('/login')
        return
      }
      alert(error.message || '운세를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.')
    } finally {
      setCheckingAccess(false)
    }
  }

  return (
    <PageContainer>
      <ContentWrapper>
        <PageTitle>✦ 오늘의 운세 확인</PageTitle>
        <PageSubtitle>내 정보를 바탕으로 생성되는 오늘의 맞춤 운세를 확인해보세요.</PageSubtitle>

        <UserInfoBox>
          <UserInfoContent>
            <ConstellationInfo>
              <ConstellationIcon>✨</ConstellationIcon>
              <ConstellationDetails>
                <ConstellationName>{user?.name ? `${user.name}님의 운세` : '나의 오늘 운세'}</ConstellationName>
                <ConstellationMetaInfo>{formatDate(user?.birth_date || user?.birthDate)}</ConstellationMetaInfo>
              </ConstellationDetails>
            </ConstellationInfo>
            <DetailInfo>
              <DetailLabel>✦</DetailLabel>
              <span>생년월일을 기준으로 별자리와 오늘의 기운을 분석합니다.</span>
            </DetailInfo>
          </UserInfoContent>
          <ActionButton type="button" onClick={() => navigate('/mypage')}>내 정보 확인</ActionButton>
        </UserInfoBox>

        <FortuneBox>
          <FortuneTitle>✦ 오늘의 종합 운세</FortuneTitle>
          <FortuneDate>{formatToday()}</FortuneDate>
          <FortuneContent>
            <p>오늘의 흐름과 기회를 AI 운세 상담가가 알기 쉽게 풀어드립니다.</p>
            <p>사랑, 재물, 건강, 직업, 인간관계의 다섯 가지 영역을 한 번에 확인할 수 있습니다.</p>
            <p>상세 결과를 확인한 뒤 궁금한 내용을 운세 챗봇에게 이어서 질문해보세요.</p>
          </FortuneContent>
        </FortuneBox>

        <PremiumBox>
          <PremiumContent>
            <PremiumIcon><Gift size={24} color="white" /></PremiumIcon>
            <PremiumInfo>
              <PremiumTitle>AI가 생성하는 오늘의 상세 운세</PremiumTitle>
              <PremiumDescription>카카오페이 결제 후 오늘의 상세 운세와 AI 상담을 이용할 수 있습니다.</PremiumDescription>
            </PremiumInfo>
          </PremiumContent>
          <PriceSection>
            <Price>₩1,900</Price>
            <BuyButton type="button" onClick={handleBuyClick} disabled={checkingAccess}>
              {checkingAccess ? '결제 상태 확인 중...' : '카카오페이로 운세 전체 보기'}
            </BuyButton>
          </PriceSection>
        </PremiumBox>
      </ContentWrapper>
    </PageContainer>
  )
}

export default FortuneReadingPage
