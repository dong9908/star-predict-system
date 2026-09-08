import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { recognizeConstellation } from '../api/constellation'
import {
  ProcessIndicator,
  ProcessStep,
  StepCircle,
  StepLabel,
} from './styles/ConstellationFindPage.styles'
import {
  AnalyzePage,
  AnalyzeCard,
  OrbitLoader,
  LoaderCore,
  LoaderStar,
  AnalyzeTitle,
  AnalyzeDescription,
  Preview,
  StatusList,
  StatusItem,
  StatusMark,
  ErrorMessage,
  ErrorActions,
  ErrorButton,
} from './styles/ConstellationAnalyzingPage.styles'

const STATUS_MESSAGES = [
  '업로드한 사진을 확인하고 있습니다',
  'AI가 주요 별과 천체 후보를 찾고 있습니다',
  '별들의 위치와 연결 구조를 비교하고 있습니다',
  '천구 좌표를 이용한 검증을 시도하고 있습니다',
  '분석 결과를 정리하고 있습니다',
]

function ConstellationAnalyzingPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const imageFile = location.state?.image
  const startedRef = useRef(false)
  const [stage, setStage] = useState(0)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [previewUrl, setPreviewUrl] = useState('')

  useEffect(() => {
    if (!imageFile) {
      setPreviewUrl('')
      return undefined
    }
    const url = URL.createObjectURL(imageFile)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [imageFile])

  useEffect(() => {
    if (!imageFile || error) return undefined
    const timer = window.setInterval(() => {
      setStage((value) => Math.min(value + 1, STATUS_MESSAGES.length - 1))
    }, 1800)
    return () => window.clearInterval(timer)
  }, [imageFile, error, attempt])

  useEffect(() => {
    if (!imageFile || startedRef.current) return
    startedRef.current = true

    recognizeConstellation(imageFile)
      .then((analysis) => {
        navigate('/constellation-find-result', {
          state: { image: imageFile, analysis },
          replace: true,
        })
      })
      .catch((requestError) => setError(requestError.message || '별자리 분석에 실패했습니다.'))
  }, [attempt, imageFile, navigate])

  const retry = () => {
    startedRef.current = false
    setStage(0)
    setError('')
    setAttempt((value) => value + 1)
  }

  if (!imageFile) {
    return (
      <AnalyzePage>
        <AnalyzeCard>
          <AnalyzeTitle>분석할 사진이 없습니다</AnalyzeTitle>
          <AnalyzeDescription>사진을 다시 선택해 주세요.</AnalyzeDescription>
          <ErrorButton $primary onClick={() => navigate('/constellation-find')}>사진 선택 화면으로</ErrorButton>
        </AnalyzeCard>
      </AnalyzePage>
    )
  }

  return (
    <AnalyzePage>
      <ProcessIndicator>
        <ProcessStep><StepCircle $completed>✓</StepCircle><StepLabel>사진 업로드</StepLabel></ProcessStep>
        <ProcessStep><StepCircle $active>02</StepCircle><StepLabel>별자리 분석</StepLabel></ProcessStep>
        <ProcessStep><StepCircle>03</StepCircle><StepLabel>결과 확인</StepLabel></ProcessStep>
      </ProcessIndicator>

      <AnalyzeCard>
        {error ? (
          <>
            <AnalyzeTitle>별자리 분석을 완료하지 못했습니다</AnalyzeTitle>
            <ErrorMessage>{error}</ErrorMessage>
            <AnalyzeDescription>서버 연결과 사진 상태를 확인한 후 다시 시도해 주세요.</AnalyzeDescription>
            <ErrorActions>
              <ErrorButton onClick={() => navigate('/constellation-find')}>다른 사진 선택</ErrorButton>
              <ErrorButton $primary onClick={retry}>다시 분석하기</ErrorButton>
            </ErrorActions>
          </>
        ) : (
          <>
            <OrbitLoader aria-label="별자리 분석 중">
              <LoaderCore>✦</LoaderCore>
              <LoaderStar $position="one">✦</LoaderStar>
              <LoaderStar $position="two">•</LoaderStar>
              <LoaderStar $position="three">✧</LoaderStar>
            </OrbitLoader>
            <AnalyzeTitle>밤하늘을 분석하고 있어요</AnalyzeTitle>
            <AnalyzeDescription>사진 속 별과 별자리를 찾고 있습니다.</AnalyzeDescription>
            {previewUrl && <Preview src={previewUrl} alt="분석 중인 밤하늘" />}
            <StatusList>
              {STATUS_MESSAGES.map((message, index) => (
                <StatusItem key={message} $active={index === stage} $completed={index < stage}>
                  <StatusMark>{index < stage ? '✓' : index === stage ? '✦' : '○'}</StatusMark>
                  {message}
                </StatusItem>
              ))}
            </StatusList>
            <AnalyzeDescription>사진에 따라 잠시 시간이 걸릴 수 있습니다.</AnalyzeDescription>
          </>
        )}
      </AnalyzeCard>
    </AnalyzePage>
  )
}

export default ConstellationAnalyzingPage
