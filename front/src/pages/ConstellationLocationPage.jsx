import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check } from 'lucide-react'
import {
  PageContainer,
  ContentWrapper,
  PageHeader,
  PageTitle,
  PageDescription,
  MainContainer,
  FormSection,
  FormGroup,
  FormGroupNumber,
  FormGroupTitle,
  FormGroupContent,
  Input,
  LocationCheckBox,
  LocationButton,
  LocationNotice,
  CheckStatus,
  VisualizationSection,
  VisualizationHeader,
  ConstellationSearchWrapper,
  ConstellationDropdown,
  ConstellationOption,
  ConstellationNoResult,
  ConstellationImageBox,
  ConstellationImage,
  ResultContainer,
  ResultRow,
  ResultLabel,
  ResultValue,
  ResultActionWrapper,
  InfoLinkButton,
  BottomButtonWrapper,
  FortuneButton,
} from './styles/ConstellationLocationPage.styles'

import {
  getConstellationPositionAPI,
  getConstellationCatalogAPI,
} from '../api/auth'

function ConstellationLocationPage() {
  const navigate = useNavigate()

  const [formData, setFormData] = useState({
    constellation: '',
    date: '',
    time: '00:00',
    latitude: '',
    longitude: '',
  })

  const [locationConfirmed, setLocationConfirmed] = useState(false)
  const [useCurrentTime, setUseCurrentTime] = useState(false)
  const [searchCompleted, setSearchCompleted] = useState(false)
  const [searchResult, setSearchResult] = useState(null)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [searchDateTime, setSearchDateTime] = useState(null)

  const [constellations, setConstellations] = useState([])
  const [showConstellationList, setShowConstellationList] = useState(false)

  // 별자리 목록 가져오기
  useEffect(() => {
    const loadConstellations = async () => {
      try {
        const data = await getConstellationCatalogAPI()
        setConstellations(data)
      } catch (error) {
        console.error('별자리 목록 조회 실패:', error)
      }
    }

    loadConstellations()
  }, [])

  // 입력값 변경
  const handleInputChange = (e) => {
    const { name, value } = e.target

    setFormData(prev => ({
      ...prev,
      [name]: value,
    }))

    if (name === 'constellation') {
      setShowSuggestions(true)
    }
  }

  // 별자리 검색 필터
  const filteredConstellations = constellations.filter(
    (constellation) =>
      constellation.name_ko.includes(
        formData.constellation.trim()
      )
  )

  // 별자리 선택
  const handleConstellationSelect = (constellation) => {
    setFormData(prev => ({
      ...prev,
      constellation: constellation.name_ko,
    }))

    setShowConstellationList(false)

    // 이전 검색 결과 초기화
    setSearchCompleted(false)
    setSearchResult(null)
  }

  // 현재 사용자 위치 가져오기
  const handleLocationConfirm = () => {
    if (!navigator.geolocation) {
      alert('이 브라우저에서는 위치 정보를 사용할 수 없습니다.')
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const latitude = position.coords.latitude
        const longitude = position.coords.longitude

        setFormData(prev => ({
          ...prev,
          latitude: latitude.toFixed(2),
          longitude: longitude.toFixed(2),
        }))

        setLocationConfirmed(true)
      },
      (error) => {
        console.error('위치 정보를 가져오지 못했습니다.', error)

        switch (error.code) {
          case error.PERMISSION_DENIED:
            alert('위치 정보 사용 권한이 거부되었습니다.')
            break
          case error.POSITION_UNAVAILABLE:
            alert('현재 위치 정보를 가져올 수 없습니다.')
            break
          case error.TIMEOUT:
            alert('위치 정보 요청 시간이 초과되었습니다.')
            break
          default:
            alert('위치 정보를 가져오는 중 오류가 발생했습니다.')
        }
      }
    )
  }

  // 현재 시간 설정
  const handleUseCurrentTime = () => {
    const now = new Date()

    const dateStr =
      `${now.getFullYear()}-` +
      `${String(now.getMonth() + 1).padStart(2, '0')}-` +
      `${String(now.getDate()).padStart(2, '0')}`

    const timeStr =
      `${String(now.getHours()).padStart(2, '0')}:` +
      `${String(now.getMinutes()).padStart(2, '0')}`

    setFormData(prev => ({
      ...prev,
      date: dateStr,
      time: timeStr,
    }))
  }

  // 별자리 위치 검색
  const handleConstellationSearch = async () => {
    setShowConstellationList(false)

    if (!formData.constellation.trim()) {
      alert('별자리 이름을 입력해주세요.')
      return
    }

    if (!formData.date) {
      alert('날짜를 입력해주세요.')
      return
    }

    if (!formData.time) {
      alert('시간을 입력해주세요.')
      return
    }

    if (!formData.latitude || !formData.longitude) {
      alert('위치를 지정해주세요.')
      return
    }

    try {
      const result = await getConstellationPositionAPI({
        constellation: formData.constellation,
        date: formData.date,
        time: formData.time,
        latitude: formData.latitude,
        longitude: formData.longitude,
      })

      setSearchResult(result)
      setSearchDateTime({
        date: formData.date,
        time: formData.time,
      })
      setSearchCompleted(true)

    } catch (error) {
      console.error('별자리 위치 조회 실패:', error)
      alert(error.message)
    }
  }

  // 운세 페이지로 이동
  const handleFortuneClick = () => {
    navigate('/fortune-reading')
  }

  // 별자리 정보 페이지로 이동
  const handleGoToConstellationInfo = () => {
    if (selectedConstellation?.constellation_id) {
      navigate(`/constellation-info?constellation_id=${selectedConstellation.constellation_id}`)
    } else {
      alert('조회할 별자리를 먼저 선택해주세요.')
    }
  }

  // 고도 표시
  const formatAltitude = (altitude) => {
    if (altitude === null || altitude === undefined) {
      return '관측 불가'
    }

    if (altitude < 0) {
      return '관측 불가'
    }

    if (altitude < 5) {
      return '지평선근처'
    }

    return `${altitude.toFixed(2)}°`
  }

  // 방향 표시
  const formatDirection = (direction, altitude) => {
    if (
      !direction ||
      altitude === null ||
      altitude === undefined ||
      altitude < 0
    ) {
      return '관측 불가'
    }

    return direction
  }

  const selectedConstellations = constellations.filter(
    (constellation) =>
      constellation.name_ko === formData.constellation
  )
  const selectedConstellation = selectedConstellations.length > 0 ? selectedConstellations[0] : null

  return (
    <PageContainer>
      <ContentWrapper>

        {/* 페이지 제목 */}
        <PageHeader>
          <PageTitle>별자리 위치</PageTitle>
          <PageDescription>
            지금 내 위치에서 원하는 별자리를 찾아보세요
          </PageDescription>
        </PageHeader>

        <MainContainer>

          {/* =========================================
              왼쪽 : 01 ~ 03
          ========================================= */}
          <FormSection>

            {/* 01. 별자리 입력 */}
            <FormGroup>
              <FormGroupNumber>01</FormGroupNumber>
              <FormGroupTitle>
                찾을 별자리를 입력해주세요
              </FormGroupTitle>
              <FormGroupContent>
                <ConstellationSearchWrapper>
                  <Input
                    type="text"
                    name="constellation"
                    value={formData.constellation}
                    onChange={(e) => {
                      handleInputChange(e)
                      setShowConstellationList(true)
                    }}
                    onFocus={() => {
                      if (formData.constellation) {
                        setShowConstellationList(true)
                      }
                    }}
                    placeholder="오리온자리"
                  />

                  {showConstellationList &&
                    formData.constellation &&
                    filteredConstellations.length > 0 && (
                      <ConstellationDropdown>
                        {filteredConstellations.map((constellation) => (
                          <ConstellationOption
                            key={constellation.constellation_id}
                            type="button"
                            onClick={() =>
                              handleConstellationSelect(constellation)
                            }
                          >
                            {constellation.name_ko}
                          </ConstellationOption>
                        ))}
                      </ConstellationDropdown>
                    )}

                  {showConstellationList &&
                    formData.constellation &&
                    filteredConstellations.length === 0 && (
                      <ConstellationNoResult>
                        검색 결과가 없습니다.
                      </ConstellationNoResult>
                    )}
                </ConstellationSearchWrapper>
              </FormGroupContent>
            </FormGroup>

            {/* 02. 날짜 및 시간 */}
            <FormGroup>
              <FormGroupNumber>02</FormGroupNumber>
              <FormGroupTitle>
                관측할 날짜와 시간을 입력해주세요
              </FormGroupTitle>
              <FormGroupContent>
                <Input
                  type="date"
                  name="date"
                  value={formData.date}
                  onChange={handleInputChange}
                />
                <Input
                  type="time"
                  name="time"
                  value={formData.time}
                  onChange={handleInputChange}
                />
                <LocationCheckBox>
                  <input
                    type="checkbox"
                    checked={useCurrentTime}
                    onChange={(e) => {
                      const checked = e.target.checked
                      setUseCurrentTime(checked)
                      if (checked) {
                        handleUseCurrentTime()
                      } else {
                        setFormData(prev => ({
                          ...prev,
                          date: '',
                          time: '00:00',
                        }))
                      }
                    }}
                  />
                  <span>현재 시간으로 설정</span>
                </LocationCheckBox>
              </FormGroupContent>
            </FormGroup>

            {/* 03. 위치 설정 */}
            <FormGroup>
              <FormGroupNumber>03</FormGroupNumber>
              <FormGroupTitle>
                위치 설정 버튼을 눌러 현재위치를 지정해주세요
              </FormGroupTitle>
              <FormGroupContent>
                <Input
                  type="text"
                  name="latitude"
                  value={formData.latitude}
                  onChange={handleInputChange}
                  placeholder="위도 (예: 37.5)"
                />
                <Input
                  type="text"
                  name="longitude"
                  value={formData.longitude}
                  onChange={handleInputChange}
                  placeholder="경도 (예: 127.0)"
                />
                <LocationButton onClick={handleLocationConfirm}>
                  위치 설정
                </LocationButton>
                <LocationNotice>
                  위치 정보는 별자리 위치 계산 목적으로만 사용됩니다.
                </LocationNotice>
                {locationConfirmed && (
                  <CheckStatus>
                    <Check size={16} />
                    현재 위치 설정 완료!
                  </CheckStatus>
                )}
              </FormGroupContent>
            </FormGroup>

          </FormSection>


          {/* =========================================
              오른쪽 : 04
          ========================================= */}
          <VisualizationSection>

            <VisualizationHeader>
              <FormGroupNumber>04</FormGroupNumber>
              <FormGroupTitle>
                별자리 위치 검색 버튼을 눌러 별자리를 찾아보세요
              </FormGroupTitle>
              <FormGroupContent>
                <LocationButton onClick={handleConstellationSearch}>
                  별자리 위치 검색
                </LocationButton>
              </FormGroupContent>
            </VisualizationHeader>

            {/* 검색 완료 시 결과 렌더링 */}
            {searchCompleted && searchResult && (
              <>
                <ConstellationImageBox>
                  {selectedConstellation?.image_url ? (
                    <ConstellationImage
                      src={selectedConstellation.image_url}
                      alt={selectedConstellation.name_ko}
                    />
                  ) : (
                    <div style={{ color: '#cbd5e1' }}>별자리 이미지를 불러올 수 없습니다.</div>
                  )}
                </ConstellationImageBox>

                <ResultContainer>
                  <ResultRow>
                    <ResultLabel>별자리명</ResultLabel>
                    <ResultValue>{searchResult.constellation}</ResultValue>
                  </ResultRow>

                  <ResultRow>
                    <ResultLabel>관측 날짜/시간</ResultLabel>
                    <ResultValue>
                      {searchDateTime?.date} {searchDateTime?.time}
                    </ResultValue>
                  </ResultRow>

                  <ResultRow>
                    <ResultLabel>고도 (Altitude)</ResultLabel>
                    <ResultValue>
                      {formatAltitude(searchResult.altitude)}
                    </ResultValue>
                  </ResultRow>

                  <ResultRow>
                    <ResultLabel>방향 (Direction)</ResultLabel>
                    <ResultValue>
                      {formatDirection(searchResult.direction, searchResult.altitude)}
                    </ResultValue>
                  </ResultRow>

                  {/* 관측 정보 박스 하단에 '별자리 정보 보러가기' 배치 */}
                  <ResultActionWrapper>
                    <InfoLinkButton onClick={handleGoToConstellationInfo}>
                      별자리 정보 보러가기
                    </InfoLinkButton>
                  </ResultActionWrapper>
                </ResultContainer>
              </>
            )}

            {/* 운세 버튼 (결과 유무와 관계없이 항상 하단 단독 한 줄 노출, 검색 버튼 색상 통일) */}
            <BottomButtonWrapper>
              <FortuneButton onClick={handleFortuneClick}>
                오늘의 나의 운세 보기 (pro)
              </FortuneButton>
            </BottomButtonWrapper>

          </VisualizationSection>

        </MainContainer>
      </ContentWrapper>
    </PageContainer>
  )
}

export default ConstellationLocationPage