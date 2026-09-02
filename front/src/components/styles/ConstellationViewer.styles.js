import styled, { keyframes } from 'styled-components'

const pulse = keyframes`
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
`

export const CardWrapper = styled.div`
  background: linear-gradient(to bottom right, rgba(15, 23, 42, 0.9), rgba(3, 7, 18, 0.9));
  border: 1px solid #1e293b;
  padding: 1.5rem;
  border-radius: 1.25rem;
  position: relative;
  overflow: hidden;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(4px);
`

export const CardHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;
  color: #22d3ee;
  font-family: 'Courier New', monospace;
  letter-spacing: 0.1rem;
  margin-bottom: 1.5rem;
`

export const HeaderText = styled.span``

export const HeaderIcon = styled.span`
  display: flex;
  align-items: center;
  justify-content: center;
`

export const SVGContainer = styled.div`
  position: relative;
  height: 12rem;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;

  svg {
    width: 100%;
    height: 100%;
  }

  .star-pulse {
    animation: ${pulse} 2s ease-in-out infinite;
  }
`

export const CardFooter = styled.div`
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(30, 41, 59, 0.8);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.75rem;
`

export const LocationText = styled.span`
  color: #94a3b8;
`

export const ConditionBadge = styled.span`
  color: #34d399;
  font-weight: 500;
`
