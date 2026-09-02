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
} from './styles/ConstellationViewer.styles'

function ConstellationViewer({
  title = '오리온자리',
  location = '남동쪽 32°',
  condition = '관측 좋음',
  onCardClick,
}) {
  return (
    <CardWrapper onClick={onCardClick} style={{ cursor: onCardClick ? 'pointer' : 'default' }}>
      <CardHeader>
        <HeaderText>LIVE SKY · SEOUL 21:42</HeaderText>
        <HeaderIcon>
          <Compass size={16} color="#22d3ee" />
        </HeaderIcon>
      </CardHeader>

      <SVGContainer>
        <svg viewBox="0 0 300 200">
          <line
            x1="50"
            y1="140"
            x2="110"
            y2="90"
            stroke="#818cf8"
            strokeWidth="1.5"
            strokeDasharray="3 3"
          />
          <line x1="110" y1="90" x2="160" y2="110" stroke="#818cf8" strokeWidth="1.5" />
          <line x1="160" y1="110" x2="200" y2="55" stroke="#818cf8" strokeWidth="1.5" />
          <line x1="200" y1="55" x2="250" y2="40" stroke="#818cf8" strokeWidth="1.5" />
          <line x1="250" y1="40" x2="280" y2="90" stroke="#818cf8" strokeWidth="1.5" />
          <line
            x1="160"
            y1="110"
            x2="200"
            y2="150"
            stroke="#818cf8"
            strokeWidth="1.5"
            strokeDasharray="3 3"
          />

          {/* Star Nodes */}
          <circle cx="50" cy="140" r="3.5" fill="#fff" className="star-pulse" />
          <circle cx="110" cy="90" r="4.5" fill="#fff" />
          <circle cx="160" cy="110" r="5" fill="#c084fc" />
          <circle cx="200" cy="55" r="3.5" fill="#fff" />
          <circle cx="250" cy="40" r="4" fill="#fff" />
          <circle cx="280" cy="90" r="3.5" fill="#fff" />
          <circle cx="200" cy="150" r="3" fill="#fff" />
        </svg>
      </SVGContainer>

      <CardFooter>
        <LocationText>
          {title} · {location}
        </LocationText>
        <ConditionBadge>{condition}</ConditionBadge>
      </CardFooter>
    </CardWrapper>
  )
}

export default ConstellationViewer
