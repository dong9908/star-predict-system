import styled, { keyframes } from 'styled-components'

const orbit = keyframes`
  to { transform: rotate(360deg); }
`

const pulse = keyframes`
  0%, 100% { transform: scale(0.92); opacity: 0.72; }
  50% { transform: scale(1.08); opacity: 1; }
`

export const AnalyzePage = styled.div`
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
  padding: 2.5rem 1.25rem 4rem;
`

export const AnalyzeCard = styled.section`
  padding: 2rem;
  border: 1px solid rgba(167, 139, 250, 0.42);
  border-radius: 1.25rem;
  background: linear-gradient(145deg, rgba(20, 10, 50, 0.88), rgba(15, 23, 42, 0.82));
  box-shadow: 0 24px 70px rgba(15, 5, 40, 0.42);
  text-align: center;
`

export const OrbitLoader = styled.div`
  position: relative;
  width: 112px;
  height: 112px;
  margin: 0 auto 1.5rem;
  border: 2px solid rgba(167, 139, 250, 0.28);
  border-top-color: #c4b5fd;
  border-radius: 50%;
  animation: ${orbit} 3.2s linear infinite;
  box-shadow: inset 0 0 25px rgba(139, 92, 246, 0.2), 0 0 28px rgba(139, 92, 246, 0.25);
`

export const LoaderCore = styled.div`
  position: absolute;
  inset: 25px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: white;
  font-size: 2rem;
  background: linear-gradient(135deg, #7c3aed, #a78bfa);
  animation: ${pulse} 1.6s ease-in-out infinite;
`

export const LoaderStar = styled.span`
  position: absolute;
  color: #ddd6fe;
  text-shadow: 0 0 10px #a78bfa;
  ${props => props.$position === 'one' && 'top: 4px; left: 19px;'}
  ${props => props.$position === 'two' && 'right: -3px; top: 52px;'}
  ${props => props.$position === 'three' && 'bottom: 5px; left: 20px;'}
`

export const AnalyzeTitle = styled.h1`
  margin: 0 0 0.75rem;
  color: #fff;
  font-size: clamp(1.45rem, 4vw, 2rem);
`

export const AnalyzeDescription = styled.p`
  margin: 0.5rem 0 1.25rem;
  color: #cbd5e1;
  line-height: 1.65;
`

export const Preview = styled.img`
  display: block;
  width: 100%;
  height: 190px;
  margin: 1.25rem 0;
  object-fit: contain;
  border-radius: 0.85rem;
  background: rgba(2, 6, 23, 0.65);
  opacity: 0.72;
`

export const StatusList = styled.div`
  max-width: 470px;
  margin: 1.5rem auto;
  display: grid;
  gap: 0.8rem;
  text-align: left;
`

export const StatusItem = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: ${props => props.$active ? '#f5f3ff' : props.$completed ? '#a7f3d0' : '#64748b'};
  font-weight: ${props => props.$active ? 700 : 500};
  transition: color 300ms ease;
`

export const StatusMark = styled.span`
  width: 1.5rem;
  color: #a78bfa;
  text-align: center;
`

export const ErrorMessage = styled.p`
  margin: 1rem auto;
  padding: 0.9rem 1rem;
  border-radius: 0.75rem;
  color: #fecaca;
  background: rgba(127, 29, 29, 0.25);
`

export const ErrorActions = styled.div`
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
`

export const ErrorButton = styled.button`
  padding: 0.75rem 1.25rem;
  border: 1px solid #a78bfa;
  border-radius: 0.6rem;
  color: white;
  background: ${props => props.$primary ? '#8b5cf6' : 'transparent'};
  font-weight: 700;
  cursor: pointer;
`
