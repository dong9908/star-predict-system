import styled, { css, keyframes } from 'styled-components'
import skyTrails from '../../assets/main-motion/sky-trails.png'

const driftWest = keyframes`
  from { transform: translate3d(5%, 0, 0) scale(1.14); }
  to { transform: translate3d(-5%, 0, 0) scale(1.14); }
`

const slowTurn = keyframes`
  from { transform: rotate(0deg) scale(1.08); }
  to { transform: rotate(-7deg) scale(1.08); }
`

const twinkle = keyframes`
  0%, 100% { opacity: 0.48; }
  50% { opacity: 0.78; }
`

export const PreviewShell = styled.section`
  position: fixed;
  inset: 0;
  overflow-x: hidden;
  overflow-y: auto;
  background: #020617;
  color: #f8fafc;
  box-sizing: border-box;

  /* ★ 기기 툴바 전환 시 뷰포트 폭 변경에 즉각 반응하도록 설정 */
  @media (max-width: 850px) {
    width: 100vw;
    height: 100vh;
    box-sizing: border-box;
    overflow-x: hidden;
  }
`

export const BackgroundLayer = styled.div`
  position: absolute;
  inset: -3%;
  background-image: url(${props => props.$image});
  background-position: center;
  background-size: cover;
  filter: saturate(1.32) contrast(1.08) brightness(1.08);
  opacity: ${props => (props.$active ? 1 : 0)};
  transform: scale(${props => (props.$active ? 1.04 : 1.1)});
  transition: opacity 1800ms ease, transform 10s linear;
  animation-play-state: ${props => (props.$paused ? 'paused' : 'running')};
`

export const MovingSky = styled.div`
  position: absolute;
  inset: -8%;
  background:
    radial-gradient(circle at 50% 12%, rgba(129, 140, 248, 0.2), transparent 25%),
    url(${skyTrails}) center / cover no-repeat;
  filter: saturate(1.32) contrast(1.08) brightness(1.08);
  animation: ${driftWest} 28s linear infinite alternate;
  animation-play-state: ${props => (props.$paused ? 'paused' : 'running')};

  &::after {
    content: '';
    position: absolute;
    inset: -12%;
    background-image:
      radial-gradient(circle at 10% 20%, #fff 0 1px, transparent 2px),
      radial-gradient(circle at 35% 65%, #c4b5fd 0 1px, transparent 2px),
      radial-gradient(circle at 72% 28%, #fff 0 1.2px, transparent 2.2px),
      radial-gradient(circle at 88% 74%, #93c5fd 0 1px, transparent 2px);
    background-size: 82px 67px, 113px 97px, 149px 109px, 191px 137px;
    transform-origin: 50% 16%;
    animation: ${slowTurn} 38s linear infinite alternate, ${twinkle} 4s ease-in-out infinite;
    animation-play-state: ${props => (props.$paused ? 'paused' : 'running')};
  }
`

export const SkyShade = styled.div`
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 29% 43%, rgba(2, 6, 23, 0.5) 0%, rgba(2, 6, 23, 0.2) 29%, transparent 52%),
    linear-gradient(90deg, rgba(2, 6, 23, 0.2), rgba(2, 6, 23, 0.04) 58%, rgba(2, 6, 23, 0.12)),
    linear-gradient(0deg, rgba(2, 6, 23, 0.5), transparent 42%, rgba(2, 6, 23, 0.08));
`

export const PreviewControls = styled.div`
  position: absolute;
  z-index: 5;
  top: 4.8rem;
  left: 50%;
  display: flex;
  gap: 0.45rem;
  padding: 0.4rem;
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 999px;
  background: rgba(2, 6, 23, 0.78);
  backdrop-filter: blur(14px);
  transform: translateX(-50%);

  @media (max-width: 850px) {
    width: max-content;
    max-width: calc(100% - 1rem);
  }
`

export const ModeButton = styled.button`
  padding: 0.6rem 0.9rem;
  border: 0;
  border-radius: 999px;
  background: ${props => (props.$active ? 'linear-gradient(135deg, #7c3aed, #a855f7)' : 'transparent')};
  color: ${props => (props.$active ? '#fff' : '#cbd5e1')};
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;

  @media (max-width: 850px) {
    padding: 0.55rem 0.65rem;
    font-size: 0.66rem;
  }
`

export const PauseButton = styled.button`
  display: grid;
  width: 2.2rem;
  border: 0;
  border-radius: 50%;
  background: rgba(148, 163, 184, 0.16);
  color: white;
  cursor: pointer;
  place-items: center;
`

export const PreviewContent = styled.div`
  position: relative;
  z-index: 2;
  width: min(1120px, calc(100% - 3rem));
  margin: 0 auto;
  padding-top: clamp(5.2rem, 10vh, 8rem);
  box-sizing: border-box;

  /* ★ 기기 크기가 고정된 모바일 뷰어 환경을 위한 완전 방어 설정 */
  @media (max-width: 850px) {
    width: 100% !important;
    max-width: 100% !important;
    padding-top: 6.8rem;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    box-sizing: border-box !important;
    overflow-x: hidden !important;
  }
`

export const HeroGrid = styled.div`
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: clamp(2rem, 5vw, 5rem);
  align-items: center;
  box-sizing: border-box;
  width: 100%;

  @media (max-width: 850px) {
    grid-template-columns: 1fr !important;
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
  }
`

export const HeroCopy = styled.div`
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;

  @media (max-width: 850px) {
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
  }
`

export const Badge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 0.95rem; /* 패딩 살짝 확대 */
  border: 1px solid rgba(192, 132, 252, 0.5);
  border-radius: 999px;
  background: rgba(88, 28, 135, 0.64);
  color: #e9d5ff;
  font-size: 0.88rem; /* ★ 부제목(뱃지) 글자 크기를 약 1.2배 키움 */
  font-weight: 600;
`

export const Title = styled.h1`
  margin: 1.25rem 0 0;
  font-size: clamp(1.5rem, 2.5vw, 2.3rem); /* ★ 데스크톱 제목 크기를 살짝 줄임 */
  line-height: 1.2;
  letter-spacing: -0.03em;
  text-shadow: 0 3px 30px rgba(2, 6, 23, 0.85);
  word-break: keep-all;
  overflow-wrap: break-word;

  @media (max-width: 850px) {
    font-size: 1.5rem;
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
  }
`

export const Accent = styled.span`color: #c4b5fd;`

export const Description = styled.p`
  max-width: 34rem;
  margin: 1rem 0 0;
  color: #cbd5e1;
  font-size: 0.92rem;
  text-shadow: 0 2px 12px #020617;
`

export const ActionRow = styled.div`
  display: flex;
  gap: 0.8rem;
  margin-top: 1.6rem;
  width: 100%;
  box-sizing: border-box;

  /* ★ 모바일(850px 이하)에서만 세로 정렬 및 100폭 적용, 데스크톱에서는 가로 나란히 정렬 유지 */
  @media (max-width: 850px) {
    flex-direction: column;
    width: 100%;
  }
`

const actionBase = css`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  padding: 0.9rem 1.25rem;
  border-radius: 999px;
  color: white;
  font-weight: 700;
  cursor: pointer;
  box-sizing: border-box;
  width: auto;       /* 데스크톱에서는 내용물 크기에 맞게 */
  min-width: 12.5rem;

  /* ★ 모바일(850px 이하)에서만 버튼 폭 100% 강제 */
  @media (max-width: 850px) {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
  }
`

export const PrimaryAction = styled.button`
  ${actionBase};
  border: 0;
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  box-shadow: 0 12px 35px rgba(124, 58, 237, 0.42);

  @media (max-width: 850px) {
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
  }
`

export const SecondaryAction = styled.button`
  ${actionBase};
  border: 1px solid rgba(196, 181, 253, 0.7);
  background: rgba(2, 6, 23, 0.58);

  @media (max-width: 850px) {
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
  }
`

export const SkyCard = styled.div`
  padding: 1.2rem;
  border: 1px solid rgba(167, 139, 250, 0.52);
  border-radius: 1.25rem;
  background: rgba(8, 15, 36, 0.7);
  box-shadow: 0 18px 65px rgba(76, 29, 149, 0.32), inset 0 0 45px rgba(99, 102, 241, 0.08);
  backdrop-filter: blur(14px);

  @media (max-width: 850px) {
    display: none;
  }
`

export const SkyCardHeader = styled.div`
  display: flex;
  justify-content: space-between;
  color: #67e8f9;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.08em;
`

export const SkyDiagram = styled.svg`
  width: 100%;
  height: 175px;
  margin-top: 0.5rem;
  filter: drop-shadow(0 0 7px rgba(167, 139, 250, 0.85));
  path { fill: none; stroke: #a5b4fc; stroke-width: 2; }
  circle { fill: white; }
`

export const SkyCardFooter = styled.div`
  display: flex;
  justify-content: space-between;
  padding-top: 0.8rem;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
  color: #94a3b8;
  font-size: 0.72rem;
  b { color: #facc15; }
  strong { color: #c084fc; cursor: pointer; }
`

export const FeatureGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.2rem;
  margin-top: clamp(2.5rem, 6vh, 4.5rem);

  @media (max-width: 850px) {
    display: none;
  }
`

export const FeatureCard = styled.article`
  position: relative;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1rem;
  align-items: center;
  padding: 1.35rem;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 1rem;
  background: rgba(15, 23, 42, 0.66);
  box-shadow: 0 16px 45px rgba(2, 6, 23, 0.3);
  backdrop-filter: blur(14px);
  transition: transform 180ms ease, border-color 180ms ease, background 180ms ease;
  ${props => props.$active && `
    transform: translateY(-3px);
    border-color: rgba(167, 139, 250, 0.52);
    background: rgba(23, 31, 54, 0.76);
  `}
  h3 { margin: 0; font-size: 1rem; }
  p { margin: 0.4rem 0; color: #a7b2c5; font-size: 0.75rem; }
  a { color: #c084fc; font-size: 0.76rem; font-weight: 700; }
`

export const FeatureIcon = styled.div`
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 0.9rem;
  background: rgba(139, 92, 246, 0.18);
  color: #c4b5fd;
  overflow: hidden; 

  img {
    width: 100%;
    height: 100%;
    object-fit: cover; 
    transform: translateX(-1px);
  }
`

export const FeatureNumber = styled.span`
  position: absolute;
  top: 0.65rem;
  left: 0.75rem;
  color: #c084fc;
  font-size: 0.65rem;
  font-weight: 800;
`

export const ProgressDots = styled.div`
  position: absolute;
  z-index: 5;
  bottom: 1.2rem;
  left: 50%;
  display: flex;
  gap: 0.55rem;
  transform: translateX(-50%);
`

export const ProgressDot = styled.button`
  width: ${props => (props.$active ? '1.6rem' : '0.5rem')};
  height: 0.5rem;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: ${props => (props.$active ? '#a78bfa' : 'rgba(255,255,255,0.42)')};
  transition: width 250ms ease, background 250ms ease;
  cursor: pointer;
`

export const MobileConstellationCard = styled.div`
  display: none;

  @media (max-width: 850px) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 1.5rem;
    padding: 1.8rem 1.6rem; /* ★ 상하 패딩을 더 넓혀서 위아래로 묵직하게 키움 */
    border: 1px solid rgba(167, 139, 250, 0.45);
    border-radius: 1.25rem;
    background: rgba(15, 23, 42, 0.8);
    backdrop-filter: blur(12px);
    box-sizing: border-box;
    width: 100%;
    cursor: pointer;
    box-shadow: 0 14px 40px rgba(76, 29, 149, 0.35);
  }
`

export const MobileCardInfo = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.35rem;

  span {
    color: #c084fc;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.05em;
  }

  h4 {
    margin: 0;
    color: #f8fafc;
    font-size: 1.2rem;
    font-weight: 700;
  }

  p {
    margin: 0;
    color: #94a3b8;
    font-size: 0.82rem;
  }
`

export const MobileCardDiagram = styled.svg`
  width: 105px;  /* ★ 오른쪽 별자리 사진(SVG)의 가로 크기를 대폭 확대 */
  height: 75px; /* ★ 세로 크기도 함께 키워서 시인성 극대화 */
  filter: drop-shadow(0 0 8px rgba(167, 139, 250, 0.9));
  
  path { fill: none; stroke: #a5b4fc; stroke-width: 2; } /* 선 두께도 살짝 두껍게 */
  circle { fill: white; }
`