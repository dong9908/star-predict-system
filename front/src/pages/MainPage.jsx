import { useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import ConstellationViewer from '../components/ConstellationViewer'
import FeatureCard from '../components/FeatureCard'
import {
  HeroSection,
  HeroGrid,
  HeroContent,
  Badge,
  Title,
  ButtonGroup,
  PrimaryButton,
  SecondaryButton,
  ButtonIcon,
  FeatureGrid,
} from './styles/MainPage.styles'

function MainPage() {
  const navigate = useNavigate()

  const features = [
    {
      number: '01',
      title: '사진으로 별자리 찾기',
      description: '밤하늘 사진을 올리면 별자리 이름과 숨겨진 신화 이야기를 알려드려요.',
      linkText: '지금 업로드하기',
    },
    {
      number: '02',
      title: '내 위치에서 별자리 찾기',
      description: '현재 위치와 시간 기준으로 별이 있는 정확한 방향과 고도를 확인해요.',
      linkText: '하늘 지도 열기',
    },
    {
      number: '03',
      title: '별자리 정보',
      description: '88개 별자리의 역사, 밝은 별 정보, 설화 및 신화 도감을 한눈에 조회하세요.',
      linkText: '별자리 정보 보기',
    },
  ]

  return (
    <div style={{ width: '100%', spacing: '3rem' }}>
      {/* Hero Section */}
      <HeroSection>
        <HeroGrid>
          <HeroContent>
            <Badge>
              ✦ 오늘 밤, 별과 더 가까워지는 방법
            </Badge>
            <Title>
              밤하늘을 올려다보는 순간,<br />별자리가 이야기가 됩니다
            </Title>
            <ButtonGroup>
              <PrimaryButton onClick={() => navigate('/')}>
                사진으로 별자리 찾기
                <ButtonIcon>
                  <ArrowRight size={16} />
                </ButtonIcon>
              </PrimaryButton>
              <SecondaryButton onClick={() => navigate('/')}>
                내 위치에서 찾아보기
              </SecondaryButton>
            </ButtonGroup>
          </HeroContent>

          <div style={{ gridColumn: 'span 5' }}>
            <ConstellationViewer />
          </div>
        </HeroGrid>
      </HeroSection>

      {/* Feature Cards Grid */}
      <FeatureGrid>
        {features.map((feature) => (
          <FeatureCard
            key={feature.number}
            number={feature.number}
            title={feature.title}
            description={feature.description}
            linkText={feature.linkText}
          />
        ))}
      </FeatureGrid>
    </div>
  )
}

export default MainPage
