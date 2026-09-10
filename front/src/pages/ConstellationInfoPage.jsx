import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
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
  LoadingState,
  ConstellationImage,
  StarEnglish,
  ConstellationCardLoading,
} from './styles/ConstellationInfoPage.styles'

const DEFAULT_CONSTELLATION_ID = 1

function ConstellationVisualization({ constellation }) {
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)

  const dragStartRef = useRef({
    pointerX: 0,
    pointerY: 0,
    panX: 0,
    panY: 0,
  })

  // 축소
  const handleZoomOut = () => {
    setZoom((value) => {
      const next = Math.max(1, value - 0.25)

      if (next === 1) {
        setPan({ x: 0, y: 0 })
      }

      return next
    })
  }

  // 확대
  const handleZoomIn = () => {
    setZoom((value) => Math.min(4, value + 0.25))
  }

  // 초기화
  const handleResetView = () => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }

  // 드래그 시작
  const handlePointerDown = (event) => {
    if (zoom <= 1) return

    event.currentTarget.setPointerCapture(event.pointerId)

    dragStartRef.current = {
      pointerX: event.clientX,
      pointerY: event.clientY,
      panX: pan.x,
      panY: pan.y,
    }

    setIsDragging(true)
  }

  // 드래그 중
  const handlePointerMove = (event) => {
    if (!isDragging || zoom <= 1) return

    const start = dragStartRef.current
    const DRAG_SPEED = 7

    setPan({
      x: start.panX + (event.clientX - start.pointerX) * DRAG_SPEED ,
      y: start.panY + (event.clientY - start.pointerY) * DRAG_SPEED,
    })
  }

  // 드래그 종료
  const handlePointerUp = (event) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }

    setIsDragging(false)
  }

  return (
    <VisualizationPanel>

      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor:
            zoom > 1
              ? (isDragging ? 'grabbing' : 'grab')
              : 'default',
          touchAction: 'none',
          userSelect: 'none',
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onDoubleClick={handleResetView}
      >

        {constellation.image_url ? (
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: 'center center',
              transition: isDragging
                ? 'none'
                : 'transform 0.2s ease',
            }}
          >
            <ConstellationImage
              src={constellation.image_url}
              alt={`${constellation.name_ko} 별자리`}
            />
          </div>
        ) : (
          <div
            style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            별자리 이미지가 없습니다.
          </div>
        )}

      </div>

      <ControlButtons>
        <ControlButton
          title="축소"
          onClick={handleZoomOut}
        >
          -
        </ControlButton>

        <ControlButton
          title="확대"
          onClick={handleZoomIn}
        >
          +
        </ControlButton>

        <ControlButton
          title="초기화"
          onClick={handleResetView}
        >
          🔄
        </ControlButton>
      </ControlButtons>

    </VisualizationPanel>
  )
}


function ConstellationInfoPage() {
  const [constellations, setConstellations] = useState([])
  const [searchParams] = useSearchParams()
  const urlConstellationId =
    Number(searchParams.get('constellation_id')) ||
    DEFAULT_CONSTELLATION_ID
  const [selectedId, setSelectedId] = useState(urlConstellationId)
  const [selectedConstellation, setSelectedConstellation] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadingId, setLoadingId] = useState(null)
  const [error, setError] = useState('')

  // 도감에서 넘어온 경우인지 확인 (constellation_id 파라미터 유무)
  const hasCatalogParam = searchParams.has('constellation_id')
  
  // 이미지(시각화 패널)가 있는 영역을 최상단으로 잡기 위한 ref
  const visualizationRef = useRef(null)

  // 별자리 전체 목록 조회 및 URL ID 변경 감지
  useEffect(() => {
    const fetchCatalog = async () => {
      try {
        setLoading(true)

        // 목록 조회
        const catalogResponse = await fetch(
          '/api/constellation/catalog'
        )

        const catalogData = await catalogResponse.json()

        setConstellations(catalogData)


        // URL에 전달된 별자리 선택 (없으면 기본값)
        const detailResponse = await fetch(
          `/api/constellation/${urlConstellationId}`
        )

        const detailData = await detailResponse.json()

        setSelectedConstellation(detailData)
        setSelectedId(urlConstellationId)

        // 도감에서 넘어온 경우 모바일에서도 이미지/시각화 패널부터 맨 위에 보이도록 즉시 스크롤 포커스
        window.scrollTo(0, 0)
        if (hasCatalogParam && visualizationRef.current) {
          visualizationRef.current.scrollIntoView({ behavior: 'auto', block: 'center' })
        }

      } catch(error) {
        console.error(error)
        setError(error.message)

      } finally {
        setLoading(false)
      }
    }

    fetchCatalog()

  }, [urlConstellationId, hasCatalogParam])

  // 검색 결과
  const filteredConstellations = useMemo(() => {
    const keyword = searchTerm.toLowerCase().trim()

    if (!keyword) {
      return constellations
    }

    return constellations.filter(
      (constellation) =>
        constellation.name_ko.toLowerCase().includes(keyword) ||
        constellation.name_en.toLowerCase().includes(keyword)
    )
  }, [constellations, searchTerm])


  // 로딩
  if (loading) {
    return (
      <LoadingState>
        별자리 정보를 불러오는 중입니다...
      </LoadingState>
    )
  }


  // 에러
  if (error) {
    return (
      <PageWrapper>
        {error}
      </PageWrapper>
    )
  }


  // 데이터 없음
  if (!selectedConstellation) {
    return (
      <PageWrapper>
        별자리 정보를 로드할 수 없습니다.
      </PageWrapper>
    )
  }


  return (
    <PageWrapper>

      {/* =========================
          왼쪽 영역 ($isFromCatalog 전달)
      ========================= */}
      <LeftSection $isFromCatalog={hasCatalogParam}>

        {/* 별자리 이미지 및 시각화 패널 (ref 부착으로 도감 진입 시 맨 먼저 노출) */}
        <div ref={visualizationRef}>
          <ConstellationVisualization
            constellation={selectedConstellation}
          />
        </div>


        <DetailSection>

          {/* 별자리 이름 */}
          <ConstellationTitle>
            <h2>
              {selectedConstellation.name_ko}
            </h2>

            <p>
              {selectedConstellation.name_en}
            </p>
          </ConstellationTitle>


          {/* 별자리 설명 */}
          <ConstellationDescription>
            {selectedConstellation.description}
          </ConstellationDescription>


          {/* 주요 별 */}
          <SectionLabel>
            🌟 주요 별들
          </SectionLabel>

          <MainStarsContainer>
            {selectedConstellation.main_stars &&
            selectedConstellation.main_stars.length > 0 ? (
              selectedConstellation.main_stars.map(
                (star, idx) => (
                  <StarChip key={idx}>
                    {star.name}{' '}

                    <StarEnglish>
                      ({star.name_en})
                    </StarEnglish>

                    <span
                      style={{
                        fontSize: '0.75rem',
                        opacity: 0.7,
                      }}
                    >
                      {' '}
                      (밝기 {star.mag})
                    </span>
                  </StarChip>
                )
              )
            ) : (
              <span>
                주요 별 정보가 없습니다.
              </span>
            )}
          </MainStarsContainer>


          {/* 별자리 이야기 */}
          <SectionLabel>
            📖 별자리 이야기
          </SectionLabel>

          <StorySection>
            {selectedConstellation.mythology ? (
              selectedConstellation.mythology
                .split('\n')
                .map((paragraph, idx) => (
                  <p key={idx}>
                    {paragraph}
                  </p>
                ))
            ) : (
              <p>
                별자리 이야기가 없습니다.
              </p>
            )}
          </StorySection>

        </DetailSection>
      </LeftSection>


      {/* =========================
          오른쪽 영역
      ========================= */}
      <RightSection $isFromCatalog={hasCatalogParam}>

        {/* 검색 */}
        <SearchContainer>
          <SearchInput
            type="text"
            placeholder="별자리를 검색해보세요"
            value={searchTerm}
            onChange={(e) =>
              setSearchTerm(e.target.value)
            }
          />
        </SearchContainer>


        {/* 별자리 목록 */}
        <ConstellationListContainer>

          {filteredConstellations.length > 0 ? (
            filteredConstellations.map(
              (constellation) => (
                <ConstellationCard
                  key={constellation.constellation_id}
                  $isSelected={
                    selectedId ===
                    constellation.constellation_id
                  }
                  onClick={async () => {
                    const id = constellation.constellation_id

                    setSelectedId(id)
                    setLoadingId(id)

                    try {
                      const response = await fetch(
                        `/api/constellation/${id}`
                      )

                      const data = await response.json()

                      setSelectedConstellation(data)

                    } catch(error) {
                      console.error(error)

                    } finally {
                      setLoadingId(null)
                    }
                  }}
                >
                  <ConstellationIcon>
                    <img
                      src={constellation.image_url}
                      alt={`${constellation.name_ko} 별자리`}
                    />
                  </ConstellationIcon>

                  <ConstellationInfo>
                    <ConstellationName>
                      {constellation.name_ko}
                    </ConstellationName>

                    <ConstellationEnglish>
                      {constellation.name_en}
                    </ConstellationEnglish>
                  </ConstellationInfo>
                  {loadingId === constellation.constellation_id && (
                    <ConstellationCardLoading>
                      별자리를 불러오고 있습니다.
                    </ConstellationCardLoading>
                  )}
                </ConstellationCard>
              )
            )
          ) : (
            <EmptyState>
              검색 결과가 없습니다
            </EmptyState>
          )}

        </ConstellationListContainer>

      </RightSection>

    </PageWrapper>
  )
}

export default ConstellationInfoPage