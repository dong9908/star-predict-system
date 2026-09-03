import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ChevronLeft, Send, Trash2 } from 'lucide-react'
import {
  createFortuneChatAPI,
  deleteFortuneConversationAPI,
  getFortuneConversationMessagesAPI,
  getFortuneConversationsAPI,
} from '../api/fortune'
import {
  PageContainer, ContentWrapper, PageHeader, PageTitle, PageSubtitle,
  UserInfoSection, UserInfo, ConstellationIcon, UserDetails, UserName,
  UserMeta, FortuneScore, ScoreLabel, ScoreValue, DateSection, DateText,
  SummarySection, SectionTitle, SummaryContent, CategoriesGrid, CategoryCard,
  CardHeader, CardIcon, CardTitle, StarRating, Star, CardContent,
  AdviceSection, AdviceContent, FooterInfo, FooterText, BackButton,
  ChatSection, ChatMessages, ChatMessage, MessageRole, SuggestedQuestions,
  SuggestedQuestionButton, ChatForm, ChatInput, SendButton, ChatError,
  ConversationWorkspace,
  HistoryPanel, HistoryHeader, ConversationList, ConversationButton,
  ConversationItem, DeleteConversationButton, NewConversationButton,
} from './styles/FortuneResultPage.styles'

const CATEGORY_META = {
  love: { title: '사랑운', icon: '💘', color: '#ec4899' },
  wealth: { title: '재물운', icon: '💰', color: '#f59e0b' },
  health: { title: '건강운', icon: '🏥', color: '#10b981' },
  career: { title: '직업운', icon: '💼', color: '#3b82f6' },
  relationship: { title: '인간관계운', icon: '👥', color: '#a855f7' },
  general: { title: '종합운', icon: '✨', color: '#a855f7' },
}

const readStoredResult = () => {
  const stored = sessionStorage.getItem('fortuneResult')
  if (!stored) return null
  try {
    return JSON.parse(stored)
  } catch {
    sessionStorage.removeItem('fortuneResult')
    return null
  }
}

const formatToday = () => new Intl.DateTimeFormat('ko-KR', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
}).format(new Date())

function FortuneResultPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const resultState = useMemo(() => location.state || readStoredResult(), [location.state])
  const fortune = resultState?.fortune
  const user = resultState?.user
  const [messages, setMessages] = useState(() => fortune ? [{ role: 'assistant', content: fortune.greeting }] : [])
  const [suggestedQuestions, setSuggestedQuestions] = useState(fortune?.suggestedQuestions || [])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [conversationId, setConversationId] = useState(() => {
    const storedId = Number(sessionStorage.getItem('fortuneConversationId'))
    return storedId > 0 ? storedId : null
  })
  const [conversations, setConversations] = useState([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [deletingConversationId, setDeletingConversationId] = useState(null)

  const handleAuthenticationError = requestError => {
    if (requestError.status !== 401) return false
    localStorage.removeItem('accessToken')
    localStorage.removeItem('user')
    sessionStorage.removeItem('fortuneConversationId')
    navigate('/login')
    return true
  }

  const loadConversations = async () => {
    const accessToken = localStorage.getItem('accessToken')
    if (!accessToken) return
    try {
      setConversations(await getFortuneConversationsAPI(accessToken))
    } catch (requestError) {
      if (!handleAuthenticationError(requestError)) {
        setError(requestError.message)
      }
    }
  }

  const loadConversation = async selectedConversationId => {
    const accessToken = localStorage.getItem('accessToken')
    if (!accessToken || loadingHistory) return

    setLoadingHistory(true)
    setError('')
    try {
      const detail = await getFortuneConversationMessagesAPI(
        accessToken,
        selectedConversationId,
      )
      setConversationId(detail.conversationId)
      sessionStorage.setItem(
        'fortuneConversationId',
        String(detail.conversationId),
      )
      setMessages(detail.messages.map(({ role, content }) => ({ role, content })))
      setSuggestedQuestions([])
    } catch (requestError) {
      if (!handleAuthenticationError(requestError)) {
        setError(requestError.message)
      }
    } finally {
      setLoadingHistory(false)
    }
  }

  const startNewConversation = () => {
    setConversationId(null)
    sessionStorage.removeItem('fortuneConversationId')
    setMessages([{ role: 'assistant', content: fortune.greeting }])
    setSuggestedQuestions(fortune.suggestedQuestions || [])
    setError('')
  }

  const deleteConversation = async selectedConversationId => {
    if (!window.confirm('이 대화방과 모든 메시지를 삭제할까요?')) return

    const accessToken = localStorage.getItem('accessToken')
    if (!accessToken) {
      navigate('/login')
      return
    }

    setDeletingConversationId(selectedConversationId)
    setError('')
    try {
      await deleteFortuneConversationAPI(accessToken, selectedConversationId)
      setConversations(current => current.filter(
        conversation => conversation.conversationId !== selectedConversationId,
      ))
      if (conversationId === selectedConversationId) startNewConversation()
    } catch (requestError) {
      if (!handleAuthenticationError(requestError)) {
        setError(requestError.message || '대화방을 삭제하지 못했습니다.')
      }
    } finally {
      setDeletingConversationId(null)
    }
  }

  useEffect(() => {
    if (!fortune) return
    loadConversations()
    if (conversationId) loadConversation(conversationId)
    // 최초 진입 시에만 저장된 대화와 목록을 불러온다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!fortune) {
    return (
      <PageContainer><ContentWrapper>
        <PageHeader>
          <PageTitle>운세 결과가 없습니다</PageTitle>
          <PageSubtitle>오늘의 운세를 먼저 생성해주세요.</PageSubtitle>
        </PageHeader>
        <div style={{ textAlign: 'center' }}>
          <BackButton type="button" onClick={() => navigate('/fortune-reading')}>운세 보러 가기</BackButton>
        </div>
      </ContentWrapper></PageContainer>
    )
  }

  const sendMessage = async message => {
    const trimmedMessage = message.trim()
    if (!trimmedMessage || sending) return

    const accessToken = localStorage.getItem('accessToken')
    if (!accessToken) {
      navigate('/login')
      return
    }

    const requestHistory = messages.slice(-10).map(({ role, content }) => ({ role, content }))
    setMessages(current => [...current, { role: 'user', content: trimmedMessage }])
    setInput('')
    setError('')
    setSending(true)

    try {
      const response = await createFortuneChatAPI(accessToken, {
        conversationId,
        message: trimmedMessage,
        category: 'general',
        history: requestHistory,
      })
      setConversationId(response.conversationId)
      sessionStorage.setItem('fortuneConversationId', String(response.conversationId))
      setMessages(current => [...current, { role: 'assistant', content: response.answer }])
      setSuggestedQuestions(response.suggestedQuestions)
      loadConversations()
    } catch (requestError) {
      if (handleAuthenticationError(requestError)) return
      setError(requestError.message || '답변을 가져오지 못했습니다. 다시 시도해주세요.')
    } finally {
      setSending(false)
    }
  }

  const handleSubmit = event => {
    event.preventDefault()
    sendMessage(input)
  }

  const renderStars = score => Array.from({ length: 5 }, (_, index) => (
    <Star key={index} $filled={index < score}>★</Star>
  ))

  return (
    <PageContainer><ContentWrapper>
      <BackButton type="button" onClick={() => navigate('/fortune-reading')}>
        <ChevronLeft size={20} /> 돌아가기
      </BackButton>

      <PageHeader>
        <PageTitle>✦ 오늘의 운세 상세 결과</PageTitle>
        <PageSubtitle>AI 운세 상담가가 전하는 오늘의 메시지</PageSubtitle>
      </PageHeader>

      <UserInfoSection>
        <UserInfo>
          <ConstellationIcon>✨</ConstellationIcon>
          <UserDetails>
            <UserName>{user?.name || '회원'}님</UserName>
            <UserMeta>{user?.birth_date || '등록된 생년월일 기준 분석'}</UserMeta>
          </UserDetails>
        </UserInfo>
        <FortuneScore><ScoreLabel>행운지수</ScoreLabel><ScoreValue>{fortune.fortuneScore}</ScoreValue></FortuneScore>
      </UserInfoSection>

      <DateSection><DateText>{formatToday()}</DateText></DateSection>

      <SummarySection>
        <SectionTitle>✦ 오늘의 종합 운세</SectionTitle>
        <SummaryContent>
          <p>{fortune.greeting}</p>
          <p>{fortune.summary}</p>
          <p>오늘의 키워드: {fortune.keywords.join(' · ')}</p>
        </SummaryContent>
      </SummarySection>

      <CategoriesGrid>
        {fortune.categorySummaries.map(category => {
          const meta = CATEGORY_META[category.category] || CATEGORY_META.general
          return (
            <CategoryCard key={category.category} $borderColor={meta.color}>
              <CardHeader><CardIcon>{meta.icon}</CardIcon><CardTitle>{category.label || meta.title}</CardTitle></CardHeader>
              <StarRating>{renderStars(category.score)}</StarRating>
              <CardContent>{category.summary}</CardContent>
            </CategoryCard>
          )
        })}
      </CategoriesGrid>

      <AdviceSection>
        <SectionTitle>✦ 운세 안내</SectionTitle>
        <AdviceContent><p>{fortune.disclaimer}</p></AdviceContent>
      </AdviceSection>

      <ConversationWorkspace>
        <HistoryPanel>
          <HistoryHeader>
            <SectionTitle>✦ 지난 운세 대화</SectionTitle>
            <NewConversationButton type="button" onClick={startNewConversation}>
              새 대화
            </NewConversationButton>
          </HistoryHeader>
          <ConversationList>
            {conversations.length === 0 && <span>저장된 대화가 없습니다.</span>}
            {conversations.map(conversation => (
              <ConversationItem key={conversation.conversationId}>
                <ConversationButton
                  type="button"
                  $active={conversation.conversationId === conversationId}
                  onClick={() => loadConversation(conversation.conversationId)}
                  disabled={loadingHistory || sending}
                >
                  {conversation.title}
                </ConversationButton>
                <DeleteConversationButton
                  type="button"
                  onClick={() => deleteConversation(conversation.conversationId)}
                  disabled={deletingConversationId === conversation.conversationId}
                  aria-label={`${conversation.title} 삭제`}
                  title="대화방 삭제"
                >
                  <Trash2 size={16} />
                </DeleteConversationButton>
              </ConversationItem>
            ))}
          </ConversationList>
        </HistoryPanel>

        <ChatSection>
          <SectionTitle>✦ 운세 AI에게 더 물어보기</SectionTitle>
          <ChatMessages aria-live="polite">
            {messages.map((message, index) => (
              <ChatMessage key={`${message.role}-${index}`} $role={message.role}>
                <MessageRole>{message.role === 'user' ? '나' : 'ASTRA AI'}</MessageRole>
                <p>{message.content}</p>
              </ChatMessage>
            ))}
            {sending && <ChatMessage $role="assistant"><MessageRole>ASTRA AI</MessageRole><p>별의 흐름을 살펴보는 중입니다...</p></ChatMessage>}
          </ChatMessages>

          <SuggestedQuestions>
            {suggestedQuestions.map(question => (
              <SuggestedQuestionButton type="button" key={question} onClick={() => sendMessage(question)} disabled={sending}>
                {question}
              </SuggestedQuestionButton>
            ))}
          </SuggestedQuestions>

          <ChatForm onSubmit={handleSubmit}>
            <ChatInput
              value={input}
              onChange={event => setInput(event.target.value)}
              placeholder="사랑운, 재물운 등 궁금한 내용을 물어보세요."
              maxLength={500}
              disabled={sending}
              aria-label="운세 질문"
            />
            <SendButton type="submit" disabled={sending || !input.trim()}><Send size={18} /> 전송</SendButton>
          </ChatForm>
          {error && <ChatError role="alert">{error}</ChatError>}
        </ChatSection>
      </ConversationWorkspace>

      <FooterInfo>
        <FooterText>오늘의 운세는 매일 자정에 새로운 날짜를 기준으로 생성됩니다.</FooterText>
        <FooterText>운세는 참고용이며 중요한 결정은 충분한 검토 후 내려주세요.</FooterText>
      </FooterInfo>
    </ContentWrapper></PageContainer>
  )
}

export default FortuneResultPage
