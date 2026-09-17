import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Camera, MapPin, Sparkles } from 'lucide-react'
import skyStaticA from '../assets/main-motion/sky-static-a.png'
import skyStaticB from '../assets/main-motion/sky-static-b.png'
import featureBook from '../assets/main-motion/feature-book.png'
import featureCrystalBall from '../assets/main-motion/feature-crystal-ball.png'
import featureCamera from '../assets/main-motion/feature-camera.png'
import featureMap from '../assets/main-motion/feature-map.png'
import CONSTELLATIONS_DATA from '../data/constellationViewerData'
import {
  PreviewShell as MainShell,
  BackgroundLayer,
  SkyShade,
  PreviewContent as MainContent,
  HeroGrid,
  HeroCopy,
  Badge,
  Title,
  Accent,
  Description,
  ActionRow,
  PrimaryAction,
  SecondaryAction,
  SkyCard,
  SkyCardHeader,
  SkyDiagram,
  SkyCardFooter,
  FeatureGrid,
  FeatureCard,
  FeatureIcon,
  FeatureNumber,
  ProgressDots,
  ProgressDot,
} from './styles/MainMotionPreviewPage.styles'

const backgrounds = [
  skyStaticA,
  skyStaticB,
]

const getCurrentTime = () => {
  const now = new Date()
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
}

const getRandomConstellation = () => (
  CONSTELLATIONS_DATA[Math.floor(Math.random() * CONSTELLATIONS_DATA.length)]
)

const getConditionColor = (condition) => {
  if (condition === '관측 좋음') return '#34d399'
  if (condition === '관측 나쁨') return '#ff6565'
  return '#facc15'
}

function MainPage() {
  const navigate = useNavigate()
  const [activeImage, setActiveImage] = useState(0)
  const [activeFeature, setActiveFeature] = useState(0)
  const [currentTime, setCurrentTime] = useState(getCurrentTime)
  const [currentConstellation] = useState(getRandomConstellation)

  useEffect(() => {
    const backgroundTimer = window.setInterval(() => {
      setActiveImage((current) => (current + 1) % backgrounds.length)
    }, 10000)

    const featureTimer = window.setInterval(() => {
      setActiveFeature((current) => (current + 1) % 4)
    }, 3000)

    const clockTimer = window.setInterval(() => {
      setCurrentTime(getCurrentTime())
    }, 1000)

    return () => {
      window.clearInterval(backgroundTimer)
      window.clearInterval(featureTimer)
      window.clearInterval(clockTimer)
    }
  }, [])

  return (
    <MainShell>
      {backgrounds.map((image, index) => (
        <BackgroundLayer key={image} $image={image} $active={index === activeImage} />
      ))}
      <SkyShade />

      <MainContent>
        <HeroGrid>
          <HeroCopy>
            <Badge><Sparkles size={14} /> 오늘 밤, 별과 더 가까워지는 방법</Badge>
            <Title>
              밤하늘을 올려다보는 순간,<br />
              <Accent>별자리</Accent>가 이야기가 됩니다
            </Title>
            <Description>
              사진 속 별을 발견하고, 지금 내 위치에서 만날 수 있는 밤하늘을 확인해 보세요.
            </Description>
            <ActionRow>
              <PrimaryAction onClick={() => navigate('/constellation-find')}>
                <Camera size={19} /> 사진으로 별자리 찾기
              </PrimaryAction>
              <SecondaryAction onClick={() => navigate('/constellation-location')}>
                <MapPin size={19} /> 내 위치에서 찾기
              </SecondaryAction>
            </ActionRow>
          </HeroCopy>

          <SkyCard>
            <SkyCardHeader><span>LIVE SKY · SEOUL {currentTime}</span><span>◎</span></SkyCardHeader>
            <SkyDiagram viewBox="0 0 300 200" aria-label={`${currentConstellation.title} 미리보기`}>
              {currentConstellation.lines.map((line, index) => (
                <line
                  key={`line-${index}`}
                  x1={line.x1}
                  y1={line.y1}
                  x2={line.x2}
                  y2={line.y2}
                  stroke="#a5b4fc"
                  strokeWidth="1.5"
                  strokeDasharray={line.dashed ? '3 3' : 'none'}
                />
              ))}
              {currentConstellation.stars.map((star, index) => (
                <circle
                  key={`star-${index}`}
                  cx={star.cx}
                  cy={star.cy}
                  r={star.r}
                  fill={star.color || '#fff'}
                />
              ))}
            </SkyDiagram>
            <SkyCardFooter>
              <span>
                {currentConstellation.title} · {currentConstellation.location} ·{' '}
                <b style={{ color: getConditionColor(currentConstellation.condition) }}>
                  {currentConstellation.condition}
                </b>
              </span>
              <strong onClick={() => navigate(`/constellation-info?constellation_id=${currentConstellation.id}`)}>
                정보보기 →
              </strong>
            </SkyCardFooter>
          </SkyCard>
        </HeroGrid>

        <FeatureGrid>
          <FeatureCard $active={activeFeature === 0}>
            <FeatureNumber>01</FeatureNumber>
            <FeatureIcon>
              <img src={featureCamera} alt="" />
            </FeatureIcon>
            <div>
              <h3>사진으로 별자리 찾기</h3>
              <p>밤하늘 사진을 올려서 별자리를 찾고 도감에 등록할 수 있어요.</p>
            </div>
          </FeatureCard>

          <FeatureCard $active={activeFeature === 1}>
            <FeatureNumber>02</FeatureNumber>
            <FeatureIcon>
              <img src={featureMap} alt="" />
            </FeatureIcon>
            <div>
              <h3>내 위치에서 별자리 찾기</h3>
              <p>현재 위치와 시간 기준으로 별이 있는 정확한 방향과 고도를 찾아드려요.</p>
            </div>
          </FeatureCard>

          <FeatureCard $active={activeFeature === 2}>
            <FeatureNumber>03</FeatureNumber>
            <FeatureIcon>
              <img src={featureBook} alt="" />
            </FeatureIcon>
            <div>
              <h3>나만의 프로필 꾸미기</h3>
              <p>특정 조건을 만족하고 다양한 프로필을 꾸며보세요.</p>
            </div>
          </FeatureCard>

          <FeatureCard $active={activeFeature === 3}>
            <FeatureNumber>04</FeatureNumber>
            <FeatureIcon>
              <img src={featureCrystalBall} alt="" />
            </FeatureIcon>
            <div>
              <h3>오늘의 운세 (pro)</h3>
              <p>내 생일을 바탕으로 오늘의 운세를 확인하고 다양하게 질문할 수 있어요.</p>
            </div>
          </FeatureCard>
        </FeatureGrid>
      </MainContent>

      <ProgressDots aria-label="배경 이미지 선택">
        {backgrounds.map((image, index) => (
          <ProgressDot
            key={image}
            $active={index === activeImage}
            onClick={() => setActiveImage(index)}
            aria-label={`${index + 1}번째 배경 보기`}
          />
        ))}
      </ProgressDots>
    </MainShell>
  )
}

export default MainPage
