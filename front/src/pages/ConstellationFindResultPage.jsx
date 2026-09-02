import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { analysisResults } from '../data/analysisResults'
import {
  PageWrapper,
  LeftSection,
  ImageVisualizationPanel,
  UploadedImage,
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
  StorySection,
  RightSection,
  ResultHeader,
  ActionButtons,
  ActionButton,
  ResultListContainer,
  ResultItem,
  RankNumber,
  ResultInfo,
  ResultName,
  ResultPercentage,
  PercentageBar,
  PercentageFill,
  ShareModal,
  ShareModalContent,
  ShareOptions,
  ShareOption,
  CloseButton,
} from './styles/ConstellationFindResultPage.styles'

function ConstellationFindResultPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const imageFile = location.state?.image

  const [selectedRank, setSelectedRank] = useState(1)
  const [showShareModal, setShowShareModal] = useState(false)
  const [imageUrl, setImageUrl] = useState(() => {
    if (imageFile) {
      return URL.createObjectURL(imageFile)
    }
    return null
  })

  const selectedResult = analysisResults.find((r) => r.rank === selectedRank)

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

  if (!selectedResult) {
    return <PageWrapper>분석 결과를 불러올 수 없습니다.</PageWrapper>
  }

  return (
    <PageWrapper>
      <LeftSection>
        <ImageVisualizationPanel>
          {imageUrl ? (
            <UploadedImage src={imageUrl} alt="업로드된 별자리 사진" />
          ) : (
            <ImagePlaceholder>📸</ImagePlaceholder>
          )}
          <ControlButtons>
            <ControlButton title="축소">-</ControlButton>
            <ControlButton title="확대">+</ControlButton>
            <ControlButton title="초기화">🔄</ControlButton>
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
            {selectedResult.mainStars.map((star, idx) => (
              <StarChip key={idx}>
                {star.ko} <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>({star.en})</span>
              </StarChip>
            ))}
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
          {analysisResults.map((result) => (
            <ResultItem
              key={result.rank}
              $isSelected={selectedRank === result.rank}
              onClick={() => setSelectedRank(result.rank)}
            >
              <RankNumber $isSelected={selectedRank === result.rank}>{result.rank}</RankNumber>
              <ResultInfo>
                <ResultName>{result.name}</ResultName>
                <PercentageBar>
                  <PercentageFill $percentage={result.percentage} />
                </PercentageBar>
              </ResultInfo>
              <ResultPercentage>{result.percentage}%</ResultPercentage>
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
  )
}

export default ConstellationFindResultPage
