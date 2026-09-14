import { useEffect, useState } from 'react'
import { Camera, MapPin, Pause, Play, Sparkles } from 'lucide-react'
import skyStaticA from '../assets/main-motion/sky-static-a.png'
import skyStaticB from '../assets/main-motion/sky-static-b.png'
import {
  PreviewShell,
  BackgroundLayer,
  MovingSky,
  SkyShade,
  PreviewControls,
  ModeButton,
  PauseButton,
  PreviewContent,
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

function MainMotionPreviewPage() {
  const [mode, setMode] = useState('slideshow')
  const [activeImage, setActiveImage] = useState(0)
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    if (mode !== 'slideshow' || paused) return undefined
    const timer = window.setInterval(() => {
      setActiveImage((current) => (current + 1) % backgrounds.length)
    }, 10000)
    return () => window.clearInterval(timer)
  }, [mode, paused])

  return (
    <PreviewShell>
      {mode === 'slideshow' ? backgrounds.map((image, index) => (
        <BackgroundLayer
          key={image}
          $image={image}
          $active={index === activeImage}
          $paused={paused}
        />
      )) : (
        <MovingSky $paused={paused} />
      )}
      <SkyShade />

      <PreviewControls>
        <ModeButton $active={mode === 'slideshow'} onClick={() => setMode('slideshow')}>
          1안 · 10초 배경 전환
        </ModeButton>
        <ModeButton $active={mode === 'drift'} onClick={() => setMode('drift')}>
          2안 · 별 이동
        </ModeButton>
        <PauseButton onClick={() => setPaused((value) => !value)} aria-label={paused ? '재생' : '일시정지'}>
          {paused ? <Play size={16} /> : <Pause size={16} />}
        </PauseButton>
      </PreviewControls>

      <PreviewContent>
        <HeroGrid>
          <HeroCopy>
            <Badge><Sparkles size={14} /> 오늘 밤, 별과 더 가까워지는 방법</Badge>
            <Title>밤하늘을 올려다보는 순간,<br /><Accent>별자리</Accent>가 이야기가 됩니다</Title>
            <Description>사진 속 별을 발견하고, 지금 내 위치에서 만날 수 있는 밤하늘을 확인해 보세요.</Description>
            <ActionRow>
              <PrimaryAction><Camera size={19} /> 사진으로 별자리 찾기</PrimaryAction>
              <SecondaryAction><MapPin size={19} /> 내 위치에서 찾기</SecondaryAction>
            </ActionRow>
          </HeroCopy>

          <SkyCard>
            <SkyCardHeader><span>LIVE SKY · SEOUL 15:43</span><span>◎</span></SkyCardHeader>
            <SkyDiagram viewBox="0 0 420 190" aria-label="별자리 미리보기">
              <path d="M86 132 L105 76 L160 116 L220 87 L275 71 L310 91 L338 66 L357 82" />
              {[['86','132'],['105','76'],['160','116'],['220','87'],['275','71'],['310','91'],['338','66'],['357','82']].map(([cx, cy]) => (
                <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="4" />
              ))}
            </SkyDiagram>
            <SkyCardFooter><span>물고기자리 · 남서쪽 45° · <b>관측 보통</b></span><strong>정보보기 →</strong></SkyCardFooter>
          </SkyCard>
        </HeroGrid>

        <FeatureGrid>
          <FeatureCard>
            <FeatureNumber>01</FeatureNumber><FeatureIcon><Camera size={26} /></FeatureIcon>
            <div><h3>사진으로 별자리 찾기</h3><p>밤하늘 사진을 올리면 별자리 이름과 숨겨진 신화 이야기를 알려드려요.</p><a>지금 업로드하기 →</a></div>
          </FeatureCard>
          <FeatureCard>
            <FeatureNumber>02</FeatureNumber><FeatureIcon><MapPin size={26} /></FeatureIcon>
            <div><h3>내 위치에서 별자리 찾기</h3><p>현재 위치와 시간 기준으로 별이 있는 정확한 방향과 고도를 찾아드려요.</p><a>별자리 위치 찾기 →</a></div>
          </FeatureCard>
        </FeatureGrid>
      </PreviewContent>

      {mode === 'slideshow' && (
        <ProgressDots>
          {backgrounds.map((image, index) => (
            <ProgressDot key={image} $active={index === activeImage} onClick={() => setActiveImage(index)} />
          ))}
        </ProgressDots>
      )}
    </PreviewShell>
  )
}

export default MainMotionPreviewPage
