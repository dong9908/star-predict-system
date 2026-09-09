import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { registerConstellation } from '../api/constellation'
import {
  PageWrapper,
  ResultPageShell,
  EmptyResultCard,
  EmptyPreview,
  EmptyTipGrid,
  EmptyTipItem,
  LeftSection,
  ImageVisualizationPanel,
  ImageStage,
  PanZoomLayer,
  UploadedImage,
  ConstellationOverlay,
  OverlayLegend,
  OverlayLegendItem,
  ImagePlaceholder,
  ControlButtons,
  ControlButton,
  DetailSection,
  RankBadge,
  ConstellationTitle,
  ConstellationDescription,
  SectionLabel,
  MainStarsContainer,
  StarChip,
  StarEnglish,
  StorySection,
  RightSection,
  ResultHeader,
  ActionButtons,
  ActionButton,
  ResultListContainer,
  ResultItem,
  RankNumber,
  ResultInfo,
  ResultNameRow,
  ResultName,
  ResultPercentage,
  CatalogRegisterButton,
  PercentageBar,
  PercentageFill,
  ShareModal,
  ShareModalContent,
  ShareOptions,
  ShareOption,
  CloseButton,
} from './styles/ConstellationFindResultPage.styles'
import {
  ProcessIndicator,
  ProcessStep,
  StepCircle,
  StepLabel,
} from './styles/ConstellationFindPage.styles'

const ResultProcessIndicator = () => (
  <ProcessIndicator>
    <ProcessStep><StepCircle $completed>✓</StepCircle><StepLabel>사진 업로드</StepLabel></ProcessStep>
    <ProcessStep><StepCircle $completed>✓</StepCircle><StepLabel>별자리 분석</StepLabel></ProcessStep>
    <ProcessStep><StepCircle $active>03</StepCircle><StepLabel>결과 확인</StepLabel></ProcessStep>
  </ProcessIndicator>
)

function ConstellationFindResultPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const imageFile = location.state?.image
  const analysis = location.state?.analysis

  const [selectedRank, setSelectedRank] = useState(1)
  const [showShareModal, setShowShareModal] = useState(false)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [activeStar, setActiveStar] = useState(null)
  const [flashToken, setFlashToken] = useState(0)
  const [registeredIds, setRegisteredIds] = useState(() => new Set())
  const [registeringId, setRegisteringId] = useState(null)
  const dragStartRef = useRef({ pointerX: 0, pointerY: 0, panX: 0, panY: 0 })
  const flashTimerRef = useRef(null)
  const [imageUrl] = useState(() => {
    if (imageFile) {
      return URL.createObjectURL(imageFile)
    }
    return null
  })

  useEffect(() => () => {
    if (imageUrl) URL.revokeObjectURL(imageUrl)
    if (flashTimerRef.current) window.clearTimeout(flashTimerRef.current)
  }, [imageUrl])

  const liveResults = useMemo(() => {
    const verifiedStructures = (analysis?.graphOverlays || []).filter((overlay) => overlay.verified)
    const sourceResults = verifiedStructures.length
      ? verifiedStructures.map((overlay, index) => ({
          rank: index + 1,
          name: overlay.name,
          englishName: overlay.englishName || overlay.candidate,
          percentage: overlay.score,
          detectedObjects: [],
          resultSource: 'WCS 구조 검증',
          description: overlay.description,
          mainStars: overlay.mainStars,
          story: overlay.story,
          detailsSource: overlay.detailsSource,
          constellationId: overlay.constellationId,
          registrationEligible: overlay.registrationEligible,
        }))
      : (analysis?.results || [])
    return sourceResults.map((result) => {
      const detectedObjects = result.detectedObjects || []
      return {
        ...result,
        description: result.description || (result.resultSource
          ? `${result.resultSource}을 통해 확인된 별자리입니다.`
          : `${detectedObjects.join(', ')} 검출 결과`),
        mainStars: result.mainStars?.length
          ? result.mainStars
          : detectedObjects.map((name) => ({ ko: name, en: name })),
        story: result.story || '업로드한 사진의 별 좌표와 공식 별자리 연결선을 비교한 결과입니다.',
      }
    })
  }, [analysis])

  const selectedResult = liveResults.find((result) => result.rank === selectedRank)
  const overlays = analysis?.graphOverlays?.length
    ? analysis.graphOverlays
    : analysis?.graphOverlay?.points?.length ? [analysis.graphOverlay] : []
  const overlayColors = [
    { line: '#c4b5fd', bg: 'rgba(109, 40, 217, 0.88)', border: '#ddd6fe', glow: 'rgba(167, 139, 250, 0.65)' },
    { line: '#60a5fa', bg: 'rgba(30, 64, 175, 0.88)', border: '#93c5fd', glow: 'rgba(59, 130, 246, 0.62)' },
    { line: '#4ade80', bg: 'rgba(21, 128, 61, 0.88)', border: '#86efac', glow: 'rgba(34, 197, 94, 0.60)' },
    { line: '#fb7185', bg: 'rgba(190, 24, 93, 0.88)', border: '#fda4af', glow: 'rgba(244, 63, 94, 0.60)' },
  ]

  const handleShare = (platform) => {
    const text = `${selectedResult.name}(${selectedResult.englishName})를 발견했어요! 일치도: ${selectedResult.percentage}% 🌟`
    const url = window.location.href

    const shareUrls = {
      twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
      kakaotalk: 'kakaoMessage',
      copy: 'copy',
    }

    if (platform === 'copy') {
      navigator.clipboard.writeText(text)
      alert('복사되었습니다!')
      setShowShareModal(false)
    } else if (platform === 'kakaotalk') {
      alert('카카오톡 공유는 준비 중입니다.')
    } else {
      window.open(shareUrls[platform], '_blank', 'width=600,height=400')
    }
  }

  const handleReanalyze = () => {
    navigate('/constellation-find')
  }

  const handleCatalogRegistration = async (event, result) => {
    event.stopPropagation()
    const accessToken = localStorage.getItem('accessToken')
    const user = localStorage.getItem('user')
    if (!accessToken || !user) {
      alert('로그인 해주세요.')
      return
    }
    if (!result.registrationEligible || !result.constellationId || registeringId) return
    try {
      setRegisteringId(result.constellationId)
      const response = await registerConstellation(result.constellationId, accessToken)
      setRegisteredIds((previous) => new Set(previous).add(result.constellationId))
      alert(response.message)
    } catch (error) {
      alert(error.message || '도감 등록에 실패했습니다.')
    } finally {
      setRegisteringId(null)
    }
  }

  const handleZoomOut = () => {
    setZoom((value) => {
      const next = Math.max(1, value - 0.25)
      if (next === 1) setPan({ x: 0, y: 0 })
      return next
    })
  }

  const handleZoomIn = () => setZoom((value) => Math.min(4, value + 0.25))

  const handleResetView = () => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }

  const selectedOverlay = overlays[selectedRank - 1]
  const availableStarIds = new Set((selectedOverlay?.points || []).map((point) => point.id))

  const handleStarClick = (star) => {
    if (!star.hip || !selectedOverlay || !availableStarIds.has(star.hip)) return
    if (flashTimerRef.current) window.clearTimeout(flashTimerRef.current)
    setActiveStar({ hip: star.hip, iau: selectedOverlay.iau })
    setFlashToken((value) => value + 1)
    flashTimerRef.current = window.setTimeout(() => setActiveStar(null), 1800)
  }

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

  const handlePointerMove = (event) => {
    if (!isDragging || zoom <= 1) return
    const start = dragStartRef.current
    setPan({
      x: start.panX + event.clientX - start.pointerX,
      y: start.panY + event.clientY - start.pointerY,
    })
  }

  const handlePointerUp = (event) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
    setIsDragging(false)
  }

  if (!imageFile || !analysis) {
    return <PageWrapper>업로드 화면에서 사진을 선택한 후 분석해주세요.</PageWrapper>
  }

  if (!selectedResult) {
    return (
      <ResultPageShell>
        <ResultProcessIndicator />
        <EmptyResultCard>
          <h2>사진에서 별자리를 확인하지 못했어요</h2>
          <p>별이 충분히 보이지 않거나 사진이 흐린 경우 인식이 어려울 수 있습니다.</p>
          {imageUrl && <EmptyPreview src={imageUrl} alt="별자리를 인식하지 못한 사진" />}
          <EmptyTipGrid>
            <EmptyTipItem><span>🌙</span><strong>어두운 장소에서 촬영</strong><small>광공해가 적고 별이 잘 보이는 장소가 좋아요.</small></EmptyTipItem>
            <EmptyTipItem><span>📷</span><strong>카메라를 흔들리지 않기</strong><small>삼각대나 고정된 곳에서 안정적으로 촬영해 주세요.</small></EmptyTipItem>
            <EmptyTipItem><span>✨</span><strong>별이 선명한 사진</strong><small>초점을 별에 맞추고 밝은 별이 여러 개 보이게 촬영해 주세요.</small></EmptyTipItem>
          </EmptyTipGrid>
          <ActionButton $variant="primary" onClick={handleReanalyze}>다른 사진 분석하기</ActionButton>
        </EmptyResultCard>
      </ResultPageShell>
    )
  }

  return (
    <ResultPageShell>
      <ResultProcessIndicator />
      <PageWrapper>
      <LeftSection>
        <ImageVisualizationPanel>
          {overlays.length > 0 && (
            <OverlayLegend>
              {overlays.map((overlay, index) => {
                const color = overlayColors[index % overlayColors.length]
                return (
                  <OverlayLegendItem key={`${overlay.iau}-${index}`} $color={color.bg}
                    $borderColor={color.border} $glowColor={color.glow}>
                    구조 후보 {index + 1}순위 : {overlay.name || overlay.candidate} · {overlay.score}% · {overlay.verified ? '검증됨' : '미확정'}
                  </OverlayLegendItem>
                )
              })}
            </OverlayLegend>
          )}
          <ImageStage
            $canPan={zoom > 1}
            $dragging={isDragging}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
            onDoubleClick={handleResetView}
            title={zoom > 1 ? '드래그해서 확대된 사진을 이동하세요.' : '확대하면 사진을 드래그할 수 있습니다.'}
          >
          {imageUrl ? (
            <PanZoomLayer style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}>
              <UploadedImage src={imageUrl} alt="업로드된 별자리 사진" />
              {overlays.length > 0 && (
                <>
                  <ConstellationOverlay
                    viewBox={`0 0 ${analysis.image.width} ${analysis.image.height}`}
                    preserveAspectRatio="xMidYMid meet"
                    aria-label="인식된 별자리 연결선"
                  >
                    {overlays.map((overlay, overlayIndex) => {
                      const color = overlayColors[overlayIndex % overlayColors.length]
                      const points = Object.fromEntries(overlay.points.map((point) => [point.id, point]))
                      const majorStars = overlay.mainStars || []
                      const majorIds = new Set(majorStars.map((star) => star.hip).filter(Boolean))
                      return (
                        <g key={`${overlay.iau}-${overlayIndex}`}>
                          {overlay.edges.map((edge, edgeIndex) => {
                            const from = points[edge.from]
                            const to = points[edge.to]
                            if (!from || !to) return null
                            return <line key={edgeIndex} x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                              stroke={color.line} strokeWidth="5"
                              strokeDasharray={overlay.verified ? undefined : '14 10'} opacity="0.92" />
                          })}
                          {overlay.points.map((point) => (
                            <g
                              key={`${point.id}-${activeStar?.hip === point.id && activeStar?.iau === overlay.iau ? flashToken : 0}`}
                              className={`${majorIds.has(point.id) ? 'major-star' : ''} ${activeStar?.hip === point.id && activeStar?.iau === overlay.iau ? 'active-star' : ''}`}
                              style={{ color: color.line, transformOrigin: `${point.x}px ${point.y}px` }}
                            >
                              {majorIds.has(point.id) && (
                                <>
                                  <circle cx={point.x} cy={point.y} r="17" fill={color.line} opacity="0.16" />
                                  <line x1={point.x - 15} y1={point.y} x2={point.x + 15} y2={point.y} stroke={color.line} strokeWidth="2" />
                                  <line x1={point.x} y1={point.y - 15} x2={point.x} y2={point.y + 15} stroke={color.line} strokeWidth="2" />
                                </>
                              )}
                              <circle cx={point.x} cy={point.y} r={majorIds.has(point.id) ? 12 : 9} fill="rgba(255,255,255,0.24)" />
                              <circle cx={point.x} cy={point.y} r={majorIds.has(point.id) ? 6.5 : 4.5} fill={majorIds.has(point.id) ? '#ffffff' : color.line} stroke={color.line} strokeWidth="2" />
                            </g>
                          ))}
                        </g>
                      )
                    })}
                  </ConstellationOverlay>
                </>
              )}
            </PanZoomLayer>
          ) : (
            <ImagePlaceholder>📸</ImagePlaceholder>
          )}
          </ImageStage>
          <ControlButtons>
            <ControlButton title="축소" onClick={handleZoomOut}>-</ControlButton>
            <ControlButton title="확대" onClick={handleZoomIn}>+</ControlButton>
            <ControlButton title="초기화" onClick={handleResetView}>🔄</ControlButton>
          </ControlButtons>
        </ImageVisualizationPanel>

        <DetailSection>
          <RankBadge>{selectedResult.rank}위 (일치도 {selectedResult.percentage}%)</RankBadge>

          <ConstellationTitle>
            <h2>{selectedResult.name}</h2>
            <p>{selectedResult.englishName}</p>
          </ConstellationTitle>

          <ConstellationDescription>{selectedResult.description}</ConstellationDescription>

          <SectionLabel>🌟 주요 별들</SectionLabel>
          <MainStarsContainer>
            {selectedResult.mainStars.map((star, idx) => {
              const available = Boolean(star.hip && availableStarIds.has(star.hip))
              const active = activeStar?.hip === star.hip && activeStar?.iau === selectedOverlay?.iau
              return (
              <StarChip key={idx} $available={available} $active={active} onClick={() => handleStarClick(star)}>
                {star.ko}{' '}
                <StarEnglish>({star.en})</StarEnglish>
                {star.magnitude != null && (
                  <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                    {' '}(밝기 {star.magnitude})
                  </span>
                )}
              </StarChip>
              )
            })}
          </MainStarsContainer>

          <SectionLabel>📖 별자리 이야기</SectionLabel>
          <StorySection>
            {selectedResult.story.split('\n').map((paragraph, idx) => (
              <p key={idx}>{paragraph}</p>
            ))}
          </StorySection>
        </DetailSection>
      </LeftSection>

      <RightSection>
        <ResultHeader>
          <h2>분석 결과</h2>
          <ActionButtons>
            <ActionButton $variant="outline" onClick={() => setShowShareModal(true)}>
              공유하기
            </ActionButton>
            <ActionButton $variant="primary" onClick={handleReanalyze}>
              새로 분석하기
            </ActionButton>
          </ActionButtons>
        </ResultHeader>

        <ResultListContainer>
          {liveResults.map((result) => (
            <ResultItem
              key={result.rank}
              $isSelected={selectedRank === result.rank}
              onClick={() => setSelectedRank(result.rank)}
            >
              <RankNumber $isSelected={selectedRank === result.rank}>{result.rank}</RankNumber>
              <ResultInfo>
                <ResultNameRow>
                  <ResultName>{result.name}</ResultName>
                  <ResultPercentage>{result.percentage}%</ResultPercentage>
                </ResultNameRow>
                <PercentageBar>
                  <PercentageFill $percentage={result.percentage} />
                </PercentageBar>
              </ResultInfo>
              <CatalogRegisterButton
                type="button"
                $registered={registeredIds.has(result.constellationId)}
                disabled={!result.registrationEligible || registeringId === result.constellationId || registeredIds.has(result.constellationId)}
                onClick={(event) => handleCatalogRegistration(event, result)}
                title={result.registrationEligible ? '발견한 별자리를 도감에 등록합니다.' : '이 결과는 도감 등록 조건을 충족하지 않습니다.'}
              >
                {registeredIds.has(result.constellationId)
                  ? '등록 완료'
                  : registeringId === result.constellationId ? '등록 중...' : '도감 등록'}
              </CatalogRegisterButton>
            </ResultItem>
          ))}
        </ResultListContainer>
      </RightSection>

      {showShareModal && (
        <ShareModal onClick={() => setShowShareModal(false)}>
          <ShareModalContent onClick={(e) => e.stopPropagation()}>
            <CloseButton onClick={() => setShowShareModal(false)}>×</CloseButton>
            <h3>분석 결과 공유하기</h3>
            <ShareOptions>
              <ShareOption onClick={() => handleShare('twitter')}>
                𝕏 Twitter에서 공유
              </ShareOption>
              <ShareOption onClick={() => handleShare('facebook')}>
                f Facebook에서 공유
              </ShareOption>
              <ShareOption onClick={() => handleShare('kakaotalk')}>
                💬 카카오톡으로 공유
              </ShareOption>
              <ShareOption onClick={() => handleShare('copy')}>
                🔗 링크 복사
              </ShareOption>
            </ShareOptions>
          </ShareModalContent>
        </ShareModal>
      )}
      </PageWrapper>
    </ResultPageShell>
  )
}

export default ConstellationFindResultPage
