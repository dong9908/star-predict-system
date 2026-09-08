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
  ConstellationContainer,
  ImageSection,
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
          </HeroContent>

          <ConstellationContainer>
            <ConstellationViewer/>
          </ConstellationContainer>
        </HeroGrid>
      </HeroSection>


      {/* Feature Cards Grid - 2 Columns */}
      <FeatureGrid>
        {features.map((feature) => (
          <FeatureCard
            key={feature.number}
            number={feature.number}
            title={feature.title}
            description={feature.description}
            linkText={feature.linkText}
            onLinkClick={() => {
              if (feature.number === '01') {
                navigate('/constellation-find')
              } else if (feature.number === '02') {
                navigate('/constellation-location')
              }
            }}
          />
        ))}
      </FeatureGrid>
    </div>
  )
}

export default MainPage
