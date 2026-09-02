import { useState, useMemo } from 'react'
import { Search } from 'lucide-react'
import {
  PageContainer,
  ContentWrapper,
  PageHeader,
  PageTitle,
  PageDescription,
  MainContainer,
  SidebarSection,
  SidebarTitle,
  CatalogInfo,
  CatalogLabel,
  CatalogCount,
  ProgressCircle,
  ProgressText,
  StatsList,
  StatItem,
  StatLabel,
  StatValue,
  ContentSection,
  FilterBar,
  FilterButton,
  SearchBar,
  SearchInput,
  SearchIcon,
  ConstellationGrid,
  ConstellationCard,
  CardImage,
  NewBadge,
  CardName,
  CardDate,
  EmptyState,
} from './styles/ConstellationCatalogPage.styles'

function ConstellationCatalogPage() {
  const [filterType, setFilterType] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  // Mock data - 88개 별자리 중 일부만 표시
  const constellations = [
    { id: 1, name: '오리온자리', date: '2026.08.25', discovered: true, isNew: true },
    { id: 2, name: '카시오페이아자리', date: '2026.08.18', discovered: true, isNew: false },
    { id: 3, name: '큰곰자리', date: '2026.08.12', discovered: true, isNew: false },
    { id: 4, name: '작은곰자리', date: '2026.08.03', discovered: true, isNew: false },
    { id: 5, name: '백조자리', date: '2026.07.28', discovered: true, isNew: false },
    { id: 6, name: '거문고자리', date: '2026.07.19', discovered: true, isNew: false },
    ...Array.from({ length: 82 }, (_, i) => ({
      id: i + 7,
      name: `별자리 ${i + 7}`,
      date: '',
      discovered: false,
      isNew: false,
    })),
  ]

  const discoveredCount = constellations.filter(c => c.discovered).length
  const percentage = Math.round((discoveredCount / constellations.length) * 100)

  // Filter and search
  const filteredConstellations = useMemo(() => {
    return constellations.filter(c => {
      const matchesFilter = filterType === 'all' ||
                          (filterType === 'discovered' && c.discovered) ||
                          (filterType === 'undiscovered' && !c.discovered)
      const matchesSearch = c.name.toLowerCase().includes(searchQuery.toLowerCase())
      return matchesFilter && matchesSearch
    })
  }, [filterType, searchQuery])

  return (
    <PageContainer>
      <ContentWrapper>
        <PageHeader>
          <PageTitle>별자리 도감</PageTitle>
          <PageDescription>
            밤하늘에서 발견한 별자리를 하나씩 수집해보세요.
          </PageDescription>
        </PageHeader>

        <MainContainer>
          {/* Sidebar */}
          <SidebarSection>
            <SidebarTitle>나의 도감</SidebarTitle>

            <CatalogInfo>
              <CatalogLabel>전체 88개 중</CatalogLabel>
              <CatalogCount>{discoveredCount}개 발견</CatalogCount>
            </CatalogInfo>

            <ProgressCircle $percentage={percentage}>
              <ProgressText>{percentage}%</ProgressText>
            </ProgressCircle>

            <StatsList>
              <StatItem>
                <StatLabel>최근 발견</StatLabel>
                <StatValue>오리온자리</StatValue>
              </StatItem>
              <StatItem>
                <StatLabel>이번 달</StatLabel>
                <StatValue>{discoveredCount}개</StatValue>
              </StatItem>
            </StatsList>
          </SidebarSection>

          {/* Content */}
          <ContentSection>
            {/* Filter Bar */}
            <FilterBar>
              <FilterButton
                $active={filterType === 'all'}
                onClick={() => setFilterType('all')}
              >
                전체 {constellations.length}
              </FilterButton>
              <FilterButton
                $active={filterType === 'discovered'}
                onClick={() => setFilterType('discovered')}
              >
                발견 {discoveredCount}
              </FilterButton>
              <FilterButton
                $active={filterType === 'undiscovered'}
                onClick={() => setFilterType('undiscovered')}
              >
                미발견 {constellations.length - discoveredCount}
              </FilterButton>
            </FilterBar>

            {/* Search Bar */}
            <SearchBar>
              <SearchIcon>
                <Search size={16} />
              </SearchIcon>
              <SearchInput
                type="text"
                placeholder="별자리 이름 검색"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </SearchBar>

            {/* Constellation Grid */}
            <ConstellationGrid>
              {filteredConstellations.length > 0 ? (
                filteredConstellations.map(constellation => (
                  <ConstellationCard key={constellation.id} $discovered={constellation.discovered}>
                    <CardImage $discovered={constellation.discovered}>
                      ✦
                      {constellation.isNew && <NewBadge>NEW</NewBadge>}
                    </CardImage>
                    {constellation.discovered && (
                      <>
                        <CardName>{constellation.name}</CardName>
                        <CardDate>{constellation.date}</CardDate>
                      </>
                    )}
                  </ConstellationCard>
                ))
              ) : (
                <EmptyState>
                  검색 결과가 없습니다.
                </EmptyState>
              )}
            </ConstellationGrid>
          </ContentSection>
        </MainContainer>
      </ContentWrapper>
    </PageContainer>
  )
}

export default ConstellationCatalogPage
