import { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
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
  DifficultyFilterButton,
  FilterInfo,
  FilterGroup,
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
import {
  getCatalogMyAPI,
} from '../api/auth'

function ConstellationCatalogPage() {
  const navigate = useNavigate()
  const [filterType, setFilterType] = useState('all')
  const [difficultyFilter, setDifficultyFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [constellations, setConstellations] = useState([])


  // 로컬 스토리지에서 로그인된 유저 정보 가져오기
  const userString = localStorage.getItem('user')
  const user = userString ? JSON.parse(userString) : null

  // 로그인하지 않은 경우 로그인 페이지로 이동
  if (!user) {
    return (
      <PageContainer>
        <div
          style={{
            color: '#a78bfa',
            textAlign: 'center',
            padding: '3rem 1rem',
          }}
        >
          <p
            style={{
              fontSize: '1.125rem',
              marginBottom: '1rem',
            }}
          >
            로그인이 필요합니다.
          </p>

          <button
            onClick={() => navigate('/login')}
            style={{
              padding: '0.75rem 1.5rem',
              borderRadius: '0.5rem',
              backgroundColor: '#9333ea',
              color: 'white',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '600',
            }}
          >
            로그인하기
          </button>
        </div>
      </PageContainer>
    )
  }

  useEffect(() => {
    const fetchConstellations = async () => {
      try {
        const token = localStorage.getItem('accessToken')
        const myCatalog = await getCatalogMyAPI(token)

        const data = myCatalog.map(item => ({
          id: item.constellation_id,
          name: item.name_ko,
          difficulty: item.difficulty,
          date: item.discovered_at
            ? item.discovered_at.split('T')[0]
            : '',
          discovered: item.discovered,
          isNew: false,
          imageUrl: item.image_url,
        }))


        setConstellations(data)

      } catch (error) {
        console.error('별자리 도감 조회 실패:', error)
      }
    }

    fetchConstellations()
  }, [])

  const discoveredCount = constellations.filter(c => c.discovered).length
  const percentage = constellations.length > 0 ? Math.round((discoveredCount / constellations.length) * 100) : 0

  // Filter and search
  const filteredConstellations = useMemo(() => {
    return constellations.filter(c => {
      // 발견 여부 필터
      const matchesFilter =
        filterType === 'all' ||
        (filterType === 'discovered' && c.discovered) ||
        (filterType === 'undiscovered' && !c.discovered)

      // 난이도 필터
      const matchesDifficulty =
        difficultyFilter === 'all' ||
        c.difficulty === difficultyFilter

      // 이름 검색
      const matchesSearch =
        c.name.toLowerCase().includes(searchQuery.toLowerCase())

      return matchesFilter && matchesDifficulty && matchesSearch
    })
  }, [constellations, filterType, difficultyFilter, searchQuery])

  const recentConstellation = useMemo(() => {
    const discovered = constellations
      .filter(c => c.discovered && c.date)
      .sort(
        (a,b) => new Date(b.date) - new Date(a.date)
      )

    return discovered[0]?.name || '없음'

  }, [constellations])

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
                <StatValue>{recentConstellation}</StatValue>
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
            <FilterGroup>
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
            </FilterGroup>


            </FilterBar>

            <FilterBar>
              <FilterGroup>
                <FilterButton
                  $active={difficultyFilter === 'all'}
                  onClick={() => setDifficultyFilter('all')}
                >
                  전체
                </FilterButton>

                <DifficultyFilterButton
                  $active={difficultyFilter === '1'}
                  $difficulty="1"
                  onClick={() => setDifficultyFilter('1')}
                >
                  ✦
                </DifficultyFilterButton>

                <DifficultyFilterButton
                  $active={difficultyFilter === '2'}
                  $difficulty="2"
                  onClick={() => setDifficultyFilter('2')}
                >
                  ✦✦
                </DifficultyFilterButton>

                <DifficultyFilterButton
                  $active={difficultyFilter === '3'}
                  $difficulty="3"
                  onClick={() => setDifficultyFilter('3')}
                >
                  ✦✦✦
                </DifficultyFilterButton>

                <DifficultyFilterButton
                  $active={difficultyFilter === '4'}
                  $difficulty="4"
                  onClick={() => setDifficultyFilter('4')}
                >
                  ✦✦✦✦
                </DifficultyFilterButton>

                <FilterButton
                  $active={difficultyFilter === '관측불가'}
                  onClick={() => setDifficultyFilter('관측불가')}
                >
                  관측불가
                </FilterButton>
              </FilterGroup>
              <FilterInfo>
                관측불가 : 일반적으로 한국에서 관측이 불가합니다.
              </FilterInfo>
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
                  <ConstellationCard 
                    key={constellation.id}
                    $discovered={constellation.discovered}
                    onClick={() =>
                      navigate(`/constellation-info?constellation_id=${constellation.id}`)
                    }
                  >
                    <CardImage $discovered={constellation.discovered}>
                    {
                      constellation.discovered
                        ? (
                            <img
                              src={constellation.imageUrl}
                              alt={constellation.name}
                            />
                          )
                        : (
                          constellation.difficulty === "관측불가"
                            ? <span className="unavailable">관측불가</span>
                            : (
                                <span className={`difficulty difficulty-${constellation.difficulty}`}>
                                  {"✦".repeat(Number(constellation.difficulty))}
                                </span>
                            )
                        )
                    }

                    {constellation.isNew && <NewBadge>NEW</NewBadge>}

                    </CardImage>
                    <CardName>
                      {constellation.name}
                    </CardName>
                    <CardDate>
                      {constellation.discovered
                        ? constellation.date
                        : '미발견'
                      }
                    </CardDate>
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
