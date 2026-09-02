import { useState, useMemo } from 'react'
import { constellations } from '../data/constellations'
import {
  PageWrapper,
  LeftSection,
  VisualizationPanel,
  DetailSection,
  ConstellationTitle,
  ConstellationDescription,
  SectionLabel,
  MainStarsContainer,
  StarChip,
  ObservationInfo,
  InfoCard,
  StorySection,
  RightSection,
  SearchContainer,
  SearchInput,
  ConstellationListContainer,
  ConstellationCard,
  ConstellationIcon,
  ConstellationInfo,
  ConstellationName,
  ConstellationEnglish,
  EmptyState,
  ControlButtons,
  ControlButton,
} from './styles/ConstellationInfoPage.styles'

function ConstellationVisualization({ constellation }) {
  const padding = 40
  const width = 300
  const height = 300
  const viewBox = `0 0 ${width} ${height}`

  const generateStarPositions = (name) => {
    const positions = {
      '오리온자리': [
        { x: 150, y: 80, size: 6 },
        { x: 120, y: 120, size: 8 },
        { x: 180, y: 140, size: 8 },
        { x: 100, y: 160, size: 5 },
        { x: 200, y: 160, size: 5 },
        { x: 150, y: 200, size: 7 },
      ],
      '큰개자리': [
        { x: 150, y: 100, size: 10 },
        { x: 120, y: 140, size: 6 },
        { x: 180, y: 160, size: 5 },
        { x: 100, y: 200, size: 5 },
        { x: 200, y: 220, size: 4 },
      ],
      '쌍둥이자리': [
        { x: 120, y: 80, size: 7 },
        { x: 180, y: 80, size: 7 },
        { x: 115, y: 150, size: 6 },
        { x: 185, y: 150, size: 6 },
        { x: 120, y: 220, size: 5 },
        { x: 180, y: 220, size: 5 },
      ],
      '황소자리': [
        { x: 150, y: 80, size: 8 },
        { x: 130, y: 120, size: 6 },
        { x: 170, y: 120, size: 5 },
        { x: 100, y: 160, size: 4 },
        { x: 200, y: 160, size: 4 },
        { x: 150, y: 200, size: 5 },
      ],
      '작은개자리': [
        { x: 150, y: 100, size: 8 },
        { x: 130, y: 150, size: 5 },
        { x: 170, y: 200, size: 4 },
      ],
      '마차부자리': [
        { x: 150, y: 90, size: 9 },
        { x: 110, y: 130, size: 6 },
        { x: 190, y: 130, size: 5 },
        { x: 120, y: 190, size: 5 },
        { x: 180, y: 210, size: 4 },
      ],
      '페르세우스자리': [
        { x: 150, y: 100, size: 7 },
        { x: 100, y: 140, size: 6 },
        { x: 200, y: 140, size: 5 },
        { x: 130, y: 180, size: 5 },
        { x: 170, y: 200, size: 4 },
      ],
      '카시오페이아자리': [
        { x: 80, y: 100, size: 6 },
        { x: 120, y: 120, size: 7 },
        { x: 150, y: 100, size: 6 },
        { x: 180, y: 120, size: 5 },
        { x: 220, y: 100, size: 5 },
      ],
      '기린자리': [
        { x: 150, y: 80, size: 5 },
        { x: 110, y: 130, size: 6 },
        { x: 190, y: 150, size: 5 },
        { x: 120, y: 200, size: 4 },
        { x: 180, y: 210, size: 4 },
      ],
      '용자리': [
        { x: 100, y: 80, size: 5 },
        { x: 150, y: 100, size: 6 },
        { x: 200, y: 80, size: 5 },
        { x: 140, y: 150, size: 5 },
        { x: 180, y: 180, size: 6 },
        { x: 120, y: 220, size: 4 },
      ],
      '백조자리': [
        { x: 150, y: 80, size: 8 },
        { x: 100, y: 140, size: 6 },
        { x: 150, y: 150, size: 5 },
        { x: 200, y: 140, size: 6 },
        { x: 150, y: 220, size: 7 },
      ],
      '독수리자리': [
        { x: 150, y: 90, size: 8 },
        { x: 120, y: 150, size: 5 },
        { x: 180, y: 150, size: 5 },
        { x: 100, y: 200, size: 4 },
        { x: 200, y: 200, size: 4 },
      ],
    }

    return positions[name] || positions['오리온자리']
  }

  const stars = generateStarPositions(constellation.name)

  return (
    <VisualizationPanel>
      <svg viewBox={viewBox} width={width} height={height}>
        {/* 별 사이의 선 */}
        {stars.length > 1 && (
          <g stroke="rgba(167, 139, 250, 0.3)" strokeWidth="1">
            {stars.map((star, idx) =>
              idx < stars.length - 1 ? (
                <line
                  key={`line-${idx}`}
                  x1={star.x}
                  y1={star.y}
                  x2={stars[idx + 1].x}
                  y2={stars[idx + 1].y}
                />
              ) : null,
            )}
          </g>
        )}

        {/* 별 */}
        {stars.map((star, idx) => (
          <circle
            key={`star-${idx}`}
            cx={star.x}
            cy={star.y}
            r={star.size}
            fill="#a78bfa"
            opacity="0.9"
            filter="drop-shadow(0 0 3px #a78bfa)"
          />
        ))}
      </svg>
      <ControlButtons>
        <ControlButton>-</ControlButton>
        <ControlButton>+</ControlButton>
        <ControlButton>🔄</ControlButton>
      </ControlButtons>
    </VisualizationPanel>
  )
}

function ConstellationInfoPage() {
  const [selectedId, setSelectedId] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')

  const selectedConstellation = constellations.find((c) => c.id === selectedId)

  const filteredConstellations = useMemo(() => {
    return constellations.filter((c) =>
      c.name.includes(searchTerm) || c.englishName.toLowerCase().includes(searchTerm.toLowerCase()),
    )
  }, [searchTerm])

  const getDirectionIcon = (direction) => {
    const icons = {
      '북쪽': '⬆️',
      '남쪽': '⬇️',
      '동쪽': '➡️',
      '서쪽': '⬅️',
      '북동쪽': '↗️',
      '남동쪽': '↘️',
      '남서쪽': '↙️',
      '북서쪽': '↖️',
    }
    return icons[direction] || '📍'
  }

  const getCurrentTime = () => {
    const now = new Date()
    return now.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
  }

  if (!selectedConstellation) {
    return <PageWrapper>별자리 정보를 로드할 수 없습니다.</PageWrapper>
  }

  return (
    <PageWrapper>
      <LeftSection>
        <ConstellationVisualization constellation={selectedConstellation} />

        <DetailSection>
          <ConstellationTitle>
            <h2>{selectedConstellation.name}</h2>
            <p>{selectedConstellation.englishName}</p>
          </ConstellationTitle>

          <ConstellationDescription>{selectedConstellation.description}</ConstellationDescription>

          <SectionLabel>🌟 주요 별들</SectionLabel>
          <MainStarsContainer>
            {selectedConstellation.mainStars.map((star, idx) => (
              <StarChip key={idx}>
                {star.ko} <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>({star.en})</span>
              </StarChip>
            ))}
          </MainStarsContainer>

          <SectionLabel>📊 관측 정보</SectionLabel>
          <ObservationInfo>
            <InfoCard>
              <div className="label">현재 시간</div>
              <div className="value">{getCurrentTime()}</div>
            </InfoCard>
            <InfoCard>
              <div className="label">고도</div>
              <div className="value">{selectedConstellation.altitude}°</div>
            </InfoCard>
            <InfoCard>
              <div className="label">방향</div>
              <div className="value">{getDirectionIcon(selectedConstellation.direction)}</div>
              <div style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '0.25rem' }}>
                {selectedConstellation.direction}
              </div>
            </InfoCard>
          </ObservationInfo>

          <SectionLabel>📖 별자리 이야기</SectionLabel>
          <StorySection>
            {selectedConstellation.story.split('\n').map((paragraph, idx) => (
              <p key={idx}>{paragraph}</p>
            ))}
          </StorySection>
        </DetailSection>
      </LeftSection>

      <RightSection>
        <SearchContainer>
          <SearchInput
            type="text"
            placeholder="별자리를 검색해보세요"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </SearchContainer>

        <ConstellationListContainer>
          {filteredConstellations.length > 0 ? (
            filteredConstellations.map((constellation) => (
              <ConstellationCard
                key={constellation.id}
                $isSelected={selectedId === constellation.id}
                onClick={() => setSelectedId(constellation.id)}
              >
                <ConstellationIcon>✦</ConstellationIcon>
                <ConstellationInfo>
                  <ConstellationName>{constellation.name}</ConstellationName>
                  <ConstellationEnglish>{constellation.englishName}</ConstellationEnglish>
                </ConstellationInfo>
              </ConstellationCard>
            ))
          ) : (
            <EmptyState>검색 결과가 없습니다</EmptyState>
          )}
        </ConstellationListContainer>
      </RightSection>
    </PageWrapper>
  )
}

export default ConstellationInfoPage
