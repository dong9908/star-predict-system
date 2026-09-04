import styled from 'styled-components'

export const PageContainer = styled.div`
  width: 100%;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  padding: 2rem 1rem;
  min-height: 100vh;
`

export const ContentWrapper = styled.div`
  max-width: 1000px;
  margin: 0 auto;
`

export const PageHeader = styled.div`
  text-align: center;
  margin-bottom: 3rem;
`

export const PageTitle = styled.h1`
  font-size: 2.25rem;
  font-weight: 700;
  color: white;
  margin: 0 0 0.5rem 0;

  @media (max-width: 768px) {
    font-size: 1.75rem;
  }
`

export const PageSubtitle = styled.p`
  font-size: 0.875rem;
  color: #cbd5e1;
  margin: 0;
`

export const UserInfoSection = styled.div`
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2rem;
  padding: 1.5rem;
  border-radius: 0.75rem;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(147, 51, 234, 0.3);
  margin-bottom: 2rem;
  align-items: center;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`

export const UserInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
`

export const ConstellationIcon = styled.div`
  width: 60px;
  height: 60px;
  min-width: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #9333ea, #a855f7);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  box-shadow: 0 4px 15px rgba(147, 51, 234, 0.3);
`

export const UserDetails = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`

export const UserName = styled.h2`
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
  margin: 0;
`

export const UserMeta = styled.p`
  font-size: 0.875rem;
  color: #cbd5e1;
  margin: 0;
`

export const FortuneScore = styled.div`
  text-align: center;
  padding: 1rem;
  background: rgba(147, 51, 234, 0.2);
  border-radius: 0.5rem;
  border: 1px solid rgba(147, 51, 234, 0.4);
`

export const ScoreLabel = styled.p`
  font-size: 0.75rem;
  color: #a78bfa;
  margin: 0 0 0.5rem 0;
  font-weight: 600;
`

export const ScoreValue = styled.p`
  font-size: 1.75rem;
  font-weight: 700;
  color: #fbbf24;
  margin: 0;
`

export const DateSection = styled.div`
  text-align: center;
  padding: 1rem 1.5rem;
  background: rgba(76, 29, 149, 0.2);
  border-radius: 0.75rem;
  border: 1px solid rgba(147, 51, 234, 0.2);
  margin-bottom: 2rem;
`

export const DateText = styled.p`
  font-size: 0.875rem;
  color: #d8b4fe;
  margin: 0;
  font-weight: 600;
`

export const SummarySection = styled.div`
  padding: 1.5rem;
  border-radius: 0.75rem;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(147, 51, 234, 0.3);
  margin-bottom: 2rem;
`

export const SectionTitle = styled.h2`
  font-size: 1.125rem;
  font-weight: 700;
  color: white;
  margin: 0 0 1rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`

export const SummaryContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;

  p {
    font-size: 0.875rem;
    color: #cbd5e1;
    line-height: 1.6;
    margin: 0;
  }
`

export const CategoriesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  margin-bottom: 2rem;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`

export const CategoryCard = styled.div`
  padding: 1.5rem;
  border-radius: 0.75rem;
  background: rgba(15, 23, 42, 0.8);
  border-left: 3px solid ${props => props.$borderColor || '#a78bfa'};
  border: 1px solid rgba(147, 51, 234, 0.2);
  border-left: 3px solid ${props => props.$borderColor || '#a78bfa'};
  transition: all 150ms ease-in-out;
  cursor: pointer;

  &:hover {
    background: rgba(30, 41, 59, 0.9);
    transform: translateY(-4px);
    box-shadow: 0 8px 24px ${props => `${props.$borderColor}40` || 'rgba(147, 51, 234, 0.2)'};
  }
`

export const CardHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
`

export const CardIcon = styled.span`
  font-size: 1.5rem;
`

export const CardTitle = styled.h3`
  font-size: 1rem;
  font-weight: 700;
  color: white;
  margin: 0;
`

export const StarRating = styled.div`
  display: flex;
  gap: 0.25rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
`

export const Star = styled.span`
  color: ${props => (props.$filled ? '#fbbf24' : '#475569')};
  font-weight: bold;
`

export const CardContent = styled.p`
  font-size: 0.875rem;
  color: #cbd5e1;
  line-height: 1.6;
  margin: 0;
`

export const AdviceSection = styled.div`
  padding: 2rem;
  border-radius: 0.75rem;
  background: linear-gradient(135deg, rgba(147, 51, 234, 0.1), rgba(99, 102, 241, 0.1));
  border: 1px solid rgba(147, 51, 234, 0.3);
  margin-bottom: 2rem;
`

export const AdviceContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;

  p {
    font-size: 0.875rem;
    color: #cbd5e1;
    line-height: 1.6;
    margin: 0;
  }
`

export const FooterInfo = styled.div`
  text-align: center;
  padding: 1.5rem;
  border-top: 1px solid rgba(147, 51, 234, 0.2);
  margin-top: 2rem;
`

export const FooterText = styled.p`
  font-size: 0.75rem;
  color: #64748b;
  margin: 0.5rem 0;

  &:first-child {
    color: #a78bfa;
    font-weight: 600;
    margin-top: 0;
  }
`

export const BackButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  background-color: transparent;
  color: #a78bfa;
  border: 1px solid rgba(147, 51, 234, 0.5);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 150ms ease-in-out;
  margin-bottom: 1.5rem;

  &:hover {
    background-color: rgba(147, 51, 234, 0.1);
    border-color: rgba(147, 51, 234, 0.8);
    color: #d8b4fe;
  }
`

export const ConversationWorkspace = styled.div`
  display: grid;
  grid-template-columns: minmax(190px, 2fr) minmax(0, 8fr);
  gap: 1rem;
  align-items: stretch;
  margin-bottom: 2rem;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`

export const ChatSection = styled.section`
  padding: 1.5rem;
  border-radius: 0.75rem;
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(147, 51, 234, 0.3);
  min-width: 0;
`

export const HistoryPanel = styled.section`
  padding: 1.25rem 1.5rem;
  border-radius: 0.75rem;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.2);
  min-width: 0;
`

export const HistoryHeader = styled.div`
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.75rem;

  ${SectionTitle} {
    margin-bottom: 0;
  }
`

export const ConversationList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 480px;
  overflow-y: auto;
  margin-top: 1rem;
  padding-right: 0.25rem;
  color: #94a3b8;
  font-size: 0.875rem;
`

export const ConversationItem = styled.div`
  display: flex;
  flex: 0 0 auto;
  align-items: stretch;
  border-radius: 0.5rem;
  overflow: hidden;
`

export const ConversationButton = styled.button`
  flex: 1 1 auto;
  min-width: 0;
  max-width: none;
  padding: 0.65rem 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-radius: 0.5rem 0 0 0.5rem;
  border: 1px solid ${props => (props.$active ? '#a855f7' : 'rgba(148, 163, 184, 0.3)')};
  background: ${props => (props.$active ? 'rgba(147, 51, 234, 0.25)' : 'rgba(30, 41, 59, 0.7)')};
  color: #e2e8f0;
  cursor: pointer;

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
`

export const DeleteConversationButton = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-left: 0;
  border-radius: 0 0.5rem 0.5rem 0;
  background: rgba(127, 29, 29, 0.2);
  color: #fca5a5;
  cursor: pointer;

  &:hover:not(:disabled) {
    background: rgba(185, 28, 28, 0.35);
    color: #fecaca;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`

export const NewConversationButton = styled.button`
  flex: 0 0 auto;
  padding: 0.55rem 0.8rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(167, 139, 250, 0.5);
  background: transparent;
  color: #c4b5fd;
  cursor: pointer;

  &:hover {
    background: rgba(147, 51, 234, 0.15);
  }
`

export const ChatMessages = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  max-height: 480px;
  overflow-y: auto;
  padding: 0.5rem 0;
  margin-bottom: 1rem;
`

export const ChatMessage = styled.div`
  align-self: ${props => (props.$role === 'user' ? 'flex-end' : 'flex-start')};
  width: fit-content;
  max-width: 82%;
  padding: 0.875rem 1rem;
  border-radius: ${props => (props.$role === 'user' ? '1rem 1rem 0.25rem 1rem' : '1rem 1rem 1rem 0.25rem')};
  background: ${props => (props.$role === 'user' ? '#7e22ce' : 'rgba(15, 23, 42, 0.9)')};
  border: 1px solid rgba(167, 139, 250, 0.25);
  color: #e2e8f0;

  p {
    margin: 0;
    line-height: 1.6;
    white-space: pre-wrap;
  }
`

export const MessageRole = styled.span`
  display: block;
  margin-bottom: 0.35rem;
  color: #c4b5fd;
  font-size: 0.75rem;
  font-weight: 700;
`

export const SuggestedQuestions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
`

export const SuggestedQuestionButton = styled.button`
  padding: 0.55rem 0.8rem;
  border-radius: 999px;
  border: 1px solid rgba(167, 139, 250, 0.45);
  background: rgba(147, 51, 234, 0.12);
  color: #ddd6fe;
  cursor: pointer;

  &:hover:not(:disabled) {
    background: rgba(147, 51, 234, 0.25);
  }

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
`

export const ChatForm = styled.form`
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.75rem;

  @media (max-width: 560px) {
    grid-template-columns: 1fr;
  }
`

export const ChatInput = styled.input`
  min-width: 0;
  padding: 0.85rem 1rem;
  border-radius: 0.625rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.9);
  color: white;
  outline: none;

  &:focus {
    border-color: #a855f7;
    box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.15);
  }

  &::placeholder {
    color: #64748b;
  }
`

export const SendButton = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.8rem 1.1rem;
  border: 0;
  border-radius: 0.625rem;
  background: linear-gradient(135deg, #9333ea, #7c3aed);
  color: white;
  font-weight: 700;
  cursor: pointer;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`

export const ChatError = styled.p`
  margin: 0.75rem 0 0;
  color: #fca5a5;
  font-size: 0.875rem;
`

export const RefundArea = styled.div`
  display: flex;
  justify-content: flex-end;
  margin-top: 1.25rem;
`

export const RefundButton = styled.button`
  padding: 0.35rem 0.55rem;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 0.4rem;
  background: transparent;
  color: rgba(148, 163, 184, 0.42);
  font-size: 0.72rem;
  cursor: pointer;

  &:hover:not(:disabled),
  &:focus-visible {
    border-color: rgba(248, 113, 113, 0.55);
    color: #fca5a5;
  }

  &:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }
`
