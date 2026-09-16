import styled from 'styled-components'

export const Container = styled.div`
  width: 100%;
  min-height: 100vh;
  padding: 3rem 4rem;
  color: white;
  box-sizing: border-box;

  @media (max-width: 768px) {
    padding: 1.5rem 1rem;
  }
`

export const HeaderArea = styled.div`
  max-width: 1400px;
  margin: 0 auto 2rem auto;
`

export const Title = styled.h1`
  font-size: 2rem;
  font-weight: bold;
  margin-bottom: 0.5rem;
`

export const Subtitle = styled.p`
  color: #a78bfa;
  font-size: 1rem;
`

export const TabsArea = styled.div`
  max-width: 1400px;
  margin: 0 auto 2rem auto;
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
`

export const TabButton = styled.button`
  padding: 0.75rem 1.5rem;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  background: ${({ $active }) => ($active ? '#9333ea' : '#1e293b')};
  transition: background 0.2s ease;

  &:hover {
    opacity: 0.9;
  }
`

export const ContentArea = styled.div`
  max-width: 1400px;
  margin: 0 auto;
`

export const Card = styled.div`
  background: rgba(30, 41, 59, 0.6);
  padding: 2rem;
  borderRadius: 1rem;
  border: 1px solid rgba(167, 139, 250, 0.3);
  backdrop-filter: blur(4px);
`

export const CardHeaderRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
`

export const CardTitle = styled.h3`
  font-size: 1.25rem;
  margin: 0;
`

export const AddButton = styled.button`
  padding: 0.6rem 1.2rem;
  background: #9333ea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;

  &:hover {
    background: #7e22ce;
  }
`

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  text-align: left;
`

export const TableHeaderRow = styled.tr`
  border-bottom: 1px solid rgba(167, 139, 250, 0.3);
  color: #a78bfa;
`

export const Th = styled.th`
  padding: 1rem;
  width: ${({ $width }) => $width || 'auto'};
  text-align: ${({ $align }) => $align || 'left'};
`

export const Td = styled.td`
  padding: 1rem;
  text-align: ${({ $align }) => $align || 'left'};
  font-size: ${({ $size }) => $size || '1rem'};
  color: ${({ $color }) => $color || 'inherit'};
  font-weight: ${({ $weight }) => $weight || 'normal'};
`

export const TableRow = styled.tr`
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);

  &:hover {
    background: rgba(255, 255, 255, 0.02);
  }
`

export const EmptyCell = styled.td`
  padding: 3rem;
  text-align: center;
  color: #94a3b8;
`

export const ActionButtonGroup = styled.div`
  display: flex;
  justify-content: center;
  gap: 0.5rem;
`

export const DeleteButton = styled.button`
  padding: 0.4rem 0.9rem;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 0.3rem;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;

  &:hover {
    background: #dc2626;
  }
`

export const EditButton = styled.button`
  padding: 0.4rem 0.8rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.3rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.85rem;

  &:hover {
    background: #2563eb;
  }
`

export const LoadingWrapper = styled.div`
  color: white;
  text-align: center;
  padding: 4rem;
  font-size: 1.1rem;
`

export const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
`

export const ModalContent = styled.div`
  background: #1e293b;
  padding: 2rem;
  border-radius: 1rem;
  width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  border: 1px solid rgba(167, 139, 250, 0.3);
  color: white;
`

export const ModalTitle = styled.h3`
  margin-bottom: 1.5rem;
  font-size: 1.25rem;
`

export const StyledForm = styled.form`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`

export const StyledInput = styled.input`
  padding: 0.75rem;
  border-radius: 0.4rem;
  border: 1px solid #475569;
  background: #0f172a;
  color: white;
  font-size: 1rem;

  &:focus {
    outline: none;
    border-color: #a78bfa;
  }
`

export const StyledTextarea = styled.textarea`
  padding: 0.75rem;
  border-radius: 0.4rem;
  border: 1px solid #475569;
  background: #0f172a;
  color: white;
  height: 80px;
  resize: vertical;
  font-size: 1rem;

  &:focus {
    outline: none;
    border-color: #a78bfa;
  }
`

export const ModalButtonGroup = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1rem;
`

export const CancelButton = styled.button`
  padding: 0.6rem 1.2rem;
  background: #64748b;
  color: white;
  border: none;
  border-radius: 0.4rem;
  cursor: pointer;

  &:hover {
    background: #475569;
  }
`

export const SubmitButton = styled.button`
  padding: 0.6rem 1.2rem;
  background: #9333ea;
  color: white;
  border: none;
  border-radius: 0.4rem;
  cursor: pointer;
  font-weight: 600;

  &:hover {
    background: #7e22ce;
  }
`