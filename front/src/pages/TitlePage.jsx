import { useEffect, useState } from 'react'
import { CheckCircle, Lock, Trophy } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { evaluateMyTitlesAPI, getMyTitlesAPI, selectMyTitleAPI } from '../api/title'
import {
  AcquiredDate,
  EmptyMessage,
  ErrorMessage,
  Header,
  LoadingMessage,
  NewTitleBanner,
  PageContainer,
  PageDescription,
  PageTitle,
  Progress,
  ProgressBar,
  ProgressFill,
  StatusIcon,
  TitleCard,
  TitleDescription,
  TitleGrid,
  TitleName,
  TitleTierBadge,
  SelectButton,
} from './styles/TitlePage.styles'

const TITLE_LEVELS = {
  1: { key: 'common', label: '일반' },
  2: { key: 'rare', label: '희귀' },
  3: { key: 'legendary', label: '전설' },
}

function TitlePage({ onDataLoaded }) {
  const navigate = useNavigate()
  const [titles, setTitles] = useState([])
  const [newTitles, setNewTitles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectingId, setSelectingId] = useState(null)

  useEffect(() => {
    const loadTitles = async () => {
      const accessToken = localStorage.getItem('accessToken')
      if (!accessToken) {
        navigate('/login', { replace: true })
        return
      }

      try {
        const evaluation = await evaluateMyTitlesAPI(accessToken)
        const result = await getMyTitlesAPI(accessToken)
        setNewTitles(evaluation.newTitles || [])
        setTitles(result.titles || [])
        onDataLoaded?.(result)
      } catch (requestError) {
        if (requestError.status === 401) {
          localStorage.removeItem('accessToken')
          localStorage.removeItem('user')
          navigate('/login', { replace: true })
          return
        }
        setError(requestError.message)
      } finally {
        setLoading(false)
      }
    }

    loadTitles()
  }, [navigate, onDataLoaded])

  const acquiredCount = titles.filter(title => title.acquired).length

  const handleSelectTitle = async titleId => {
    const accessToken = localStorage.getItem('accessToken')
    if (!accessToken || selectingId !== null) return

    try {
      setSelectingId(titleId)
      setError('')
      await selectMyTitleAPI(accessToken, titleId)
      const result = await getMyTitlesAPI(accessToken)
      setTitles(result.titles || [])
      onDataLoaded?.(result)
      window.dispatchEvent(new CustomEvent('astra:selected-title-changed', {
        detail: result.titles?.find(title => title.selected) || null,
      }))
    } catch (requestError) {
      if (requestError.status === 401) {
        localStorage.removeItem('accessToken')
        localStorage.removeItem('user')
        navigate('/login', { replace: true })
        return
      }
      setError(requestError.message)
    } finally {
      setSelectingId(null)
    }
  }

  return (
    <PageContainer>
      <Header>
        <Trophy size={38} aria-hidden="true" />
        <div>
          <PageTitle>나의 칭호</PageTitle>
          <PageDescription>별자리를 발견하고 특별한 칭호를 모아보세요.</PageDescription>
        </div>
      </Header>

      {!loading && !error && (
        <Progress>
          <span>{acquiredCount} / {titles.length} 획득</span>
          <ProgressBar>
            <ProgressFill $percent={titles.length ? (acquiredCount / titles.length) * 100 : 0} />
          </ProgressBar>
        </Progress>
      )}

      {newTitles.length > 0 && (
        <NewTitleBanner role="status">
          🏆 새로운 칭호 획득: {newTitles.map(title => title.name).join(', ')}
        </NewTitleBanner>
      )}

      {loading && <LoadingMessage>칭호 정보를 확인하고 있습니다...</LoadingMessage>}
      {error && <ErrorMessage role="alert">{error}</ErrorMessage>}
      {!loading && !error && titles.length === 0 && (
        <EmptyMessage>등록된 칭호가 없습니다.</EmptyMessage>
      )}

      <TitleGrid>
        {titles.map(title => {
          const tier = title.id === 121
            ? { key: 'unavailable', label: '특수 전설' }
            : TITLE_LEVELS[title.level] || TITLE_LEVELS[1]
          return (
          <TitleCard key={title.id} $acquired={title.acquired} $tier={tier.key}>
            <StatusIcon $acquired={title.acquired} $tier={tier.key}>
              {title.acquired
                ? <CheckCircle size={24} aria-label="획득 완료" />
                : <Lock size={22} aria-label="미획득" />}
            </StatusIcon>
            <div>
              <TitleName>
                {title.name}
                <TitleTierBadge $tier={tier.key}>{tier.label}</TitleTierBadge>
              </TitleName>
              <TitleDescription>{title.description || '획득 조건이 없습니다.'}</TitleDescription>
              {title.acquired && title.acquiredAt && (
                <AcquiredDate>
                  {new Date(title.acquiredAt).toLocaleDateString('ko-KR')} 획득
                </AcquiredDate>
              )}
              {title.acquired && (
                <SelectButton
                  type="button"
                  $selected={title.selected}
                  disabled={title.selected || selectingId !== null}
                  onClick={() => handleSelectTitle(title.id)}
                >
                  {title.selected
                    ? '대표 칭호로 사용 중'
                    : selectingId === title.id
                      ? '변경 중...'
                      : '대표 칭호로 설정'}
                </SelectButton>
              )}
            </div>
          </TitleCard>
          )
        })}
      </TitleGrid>
    </PageContainer>
  )
}

export default TitlePage
