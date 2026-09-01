import styled from 'styled-components'

export const PageContainer = styled.div`
  width: 100%;
  padding: 3rem 2rem;
  min-height: calc(100vh - 80px);
`

export const ContentWrapper = styled.div`
  max-width: 1400px;
  margin: 0 auto;
`

export const PageHeader = styled.div`
  margin-bottom: 2rem;

  @media (max-width: 768px) {
    margin-bottom: 1.5rem;
  }
`

export const PageTitle = styled.h1`
  font-size: 2rem;
  color: white;
  margin-bottom: 0.5rem;

  @media (max-width: 768px) {
    font-size: 1.5rem;
  }
`

export const PageDescription = styled.p`
  color: #cbd5e1;
  font-size: 1rem;
`

export const MainContainer = styled.div`
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 2rem;

  @media (max-width: 1024px) {
    grid-template-columns: 250px 1fr;
  }

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`

export const SidebarSection = styled.div`
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 1rem;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  height: fit-content;

  @media (max-width: 768px) {
    padding: 1rem;
  }
`

export const SidebarTitle = styled.h3`
  color: white;
  font-size: 0.875rem;
  margin-bottom: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #a78bfa;
`

export const CatalogInfo = styled.div`
  margin-bottom: 2rem;
`

export const CatalogLabel = styled.p`
  color: #cbd5e1;
  font-size: 0.875rem;
  margin: 0 0 0.5rem 0;
`

export const CatalogCount = styled.p`
  color: white;
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
`

export const ProgressCircle = styled.div`
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: conic-gradient(
    #a78bfa 0deg ${props => (props.$percentage / 100) * 360}deg,
    rgba(167, 139, 250, 0.2) ${props => (props.$percentage / 100) * 360}deg
  );
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.5rem;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.5);
`

export const ProgressText = styled.div`
  color: white;
  font-size: 1.75rem;
  font-weight: 700;
`

export const StatsList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`

export const StatItem = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(167, 139, 250, 0.2);

  &:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }
`

export const StatLabel = styled.span`
  color: #cbd5e1;
  font-size: 0.875rem;
`

export const StatValue = styled.span`
  color: white;
  font-weight: 600;
`

export const ContentSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`

export const FilterBar = styled.div`
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;

  @media (max-width: 768px) {
    gap: 0.5rem;
  }
`

export const FilterButton = styled.button`
  padding: 0.5rem 1rem;
  background: ${props => props.$active ? '#a78bfa' : 'rgba(30, 41, 59, 0.8)'};
  color: ${props => props.$active ? 'white' : '#cbd5e1'};
  border: 1px solid ${props => props.$active ? '#a78bfa' : 'rgba(167, 139, 250, 0.3)'};
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 300ms ease;

  &:hover {
    border-color: #a78bfa;
    background: ${props => !props.$active && 'rgba(167, 139, 250, 0.1)'};
  }
`

export const SearchBar = styled.div`
  position: relative;
`

export const SearchInput = styled.input`
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 2.5rem;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 0.5rem;
  color: white;
  font-size: 0.875rem;

  &::placeholder {
    color: #64748b;
  }

  &:focus {
    outline: none;
    border-color: #a78bfa;
    box-shadow: 0 0 10px rgba(167, 139, 250, 0.2);
  }
`

export const SearchIcon = styled.span`
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: #a78bfa;
`

export const ConstellationGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;

  @media (max-width: 1024px) {
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  }

  @media (max-width: 768px) {
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  }
`

export const ConstellationCard = styled.div`
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 0.75rem;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.3);
  text-align: center;
  transition: all 300ms ease;
  cursor: pointer;
  position: relative;

  &:hover {
    border-color: #a78bfa;
    background: rgba(167, 139, 250, 0.1);
    transform: translateY(-4px);
    box-shadow: 0 10px 25px rgba(167, 139, 250, 0.2);
  }

  ${props => !props.$discovered && `
    opacity: 0.5;
  `}
`

export const CardImage = styled.div`
  width: 100%;
  aspect-ratio: 1;
  background: linear-gradient(135deg, #1e293b, #0f172a);
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.75rem;
  font-size: 2rem;
  position: relative;

  ${props => props.$discovered && `
    background: linear-gradient(135deg, rgba(167, 139, 250, 0.2), rgba(167, 139, 250, 0.05));
  `}
`

export const NewBadge = styled.span`
  position: absolute;
  top: -0.5rem;
  right: -0.5rem;
  background: #f472b6;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.7rem;
  font-weight: 600;
`

export const CardName = styled.p`
  color: white;
  font-size: 0.875rem;
  font-weight: 500;
  margin: 0.5rem 0 0.25rem 0;
`

export const CardDate = styled.p`
  color: #a78bfa;
  font-size: 0.75rem;
  margin: 0;
`

export const EmptyState = styled.div`
  grid-column: 1 / -1;
  text-align: center;
  padding: 3rem 2rem;
  color: #cbd5e1;
`
