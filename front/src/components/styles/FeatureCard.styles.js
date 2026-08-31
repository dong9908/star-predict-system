import styled from 'styled-components'

export const CardWrapper = styled.div`
  padding: 1.5rem;
  border-radius: 0.75rem;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid #1e293b;
  transition: all 150ms ease-in-out;
  cursor: pointer;

  &:hover {
    border-color: rgba(147, 51, 234, 0.5);
  }
`

export const CardNumber = styled.div`
  font-size: 0.75rem;
  font-family: 'Courier New', monospace;
  color: #a855f7;
  font-weight: 700;
  margin-bottom: 0.5rem;
`

export const CardTitle = styled.h3`
  font-size: 1.125rem;
  font-weight: 700;
  color: white;
  margin: 0.5rem 0;
`

export const CardDescription = styled.p`
  font-size: 0.75rem;
  color: #94a3b8;
  line-height: 1.5;
  margin-bottom: 1rem;
`

export const CardLink = styled.a`
  font-size: 0.75rem;
  font-weight: 600;
  color: #a855f7;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  transition: color 150ms ease-in-out;

  &:hover {
    color: #d8b4fe;
  }
`
