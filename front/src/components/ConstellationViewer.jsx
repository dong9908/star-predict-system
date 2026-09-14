import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Compass } from 'lucide-react'
import {
  CardWrapper,
  CardHeader,
  HeaderText,
  HeaderIcon,
  SVGContainer,
  CardFooter,
  LocationText,
  ConditionBadge,
  InfoButton,
} from './styles/ConstellationViewer.styles'
import CONSTELLATIONS_DATA from '../data/constellationViewerData'

function ConstellationViewer({ onCardClick }) {
  const navigate = useNavigate()
  const [currentTime, setCurrentTime] = useState('')
  const [currentConstellation, setCurrentConstellation] = useState(null)

  useEffect(() => {
    const updateCurrentTime = () => {
      const now = new Date()
      const hours = String(now.getHours()).padStart(2, '0')
      const minutes = String(now.getMinutes()).padStart(2, '0')
      setCurrentTime(`${hours}:${minutes}`)
    }

    updateCurrentTime()
    const timer = setInterval(updateCurrentTime, 1000)

    const randomIndex = Math.floor(Math.random() * CONSTELLATIONS_DATA.length)
    setCurrentConstellation(CONSTELLATIONS_DATA[randomIndex])

    return () => clearInterval(timer)
  }, [])

  if (!currentConstellation) return null

  return (
    <CardWrapper onClick={onCardClick} style={{ cursor: onCardClick ? 'pointer' : 'default' }}>
      <CardHeader>
        <HeaderText>LIVE SKY · SEOUL {currentTime}</HeaderText>
        <HeaderIcon>
          <Compass size={16} color="#22d3ee" />
        </HeaderIcon>
      </CardHeader>

      <SVGContainer>
        <svg viewBox="0 0 300 200">
          {currentConstellation.lines.map((line, idx) => (
            <line
              key={`line-${idx}`}
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke="#818cf8"
              strokeWidth="1.5"
              strokeDasharray={line.dashed ? '3 3' : 'none'}
            />
          ))}

          {currentConstellation.stars.map((star, idx) => (
            <circle
              key={`star-${idx}`}
              cx={star.cx}
              cy={star.cy}
              r={star.r}
              fill={star.color || '#fff'}
              className={star.pulse ? 'star-pulse' : ''}
            />
          ))}
        </svg>
      </SVGContainer>

      <CardFooter>
        <LocationText>
          {currentConstellation.title} · {currentConstellation.location} ·{' '}
          <ConditionBadge condition={currentConstellation.condition}>
            {currentConstellation.condition}
          </ConditionBadge>
        </LocationText>

        <InfoButton
          onClick={(e) => {
            e.stopPropagation()
            navigate(
              `/constellation-info?constellation_id=${currentConstellation.id}`
            )
          }}
        >
          정보보기 →
        </InfoButton>
      </CardFooter>
    </CardWrapper>
  )
}

export default ConstellationViewer