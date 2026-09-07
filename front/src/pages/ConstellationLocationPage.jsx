import { useEffect, useState } from 'react'
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
  HighlightText,
} from './styles/ConstellationLocationPage.styles'

import {
  getConstellationPositionAPI,
  getConstellationsAPI,
} from '../api/auth'

function ConstellationLocationPage() {
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

  const filteredConstellations = useMemo(() => {
    if (!formData.constellation.trim()) return constellations
    return constellations.filter(c =>
      c.name.toLowerCase().includes(formData.constellation.toLowerCase()) ||
      c.englishName.toLowerCase().includes(formData.constellation.toLowerCase())
    )
  }, [formData.constellation])

  const [constellations, setConstellations] = useState([])
  const [showConstellationList, setShowConstellationList] = useState(false)

  // 별자리 목록 가져오기
  useEffect(() => {
    const loadConstellations = async () => {
      try {
        const data = await getConstellationsAPI()
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

  const handleSelectConstellation = (name) => {
    setFormData(prev => ({
      ...prev,
      constellation: name,
    }))
    setShowSuggestions(false)
  }

  // 별자리 검색
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
    // 검색 목록 닫기
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

      console.log('========== 별자리 위치 검색 결과 ==========')
      console.log(result)

      setSearchResult(result)
      setSearchCompleted(true)

    } catch (error) {
      console.error('별자리 위치 조회 실패:', error)
      alert(error.message)
    }
  }

  const selectedConstellation = constellations.find(
    (constellation) =>
      constellation.name_ko === formData.constellation
  )

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

                  {/* 검색 결과 */}
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

                  {/* 검색 결과 없음 */}
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


            {/* 검색 결과 */}
            {searchCompleted && searchResult && (
              <>
                {/* 별자리 이미지 */}
                <ConstellationImageBox>
                  {selectedConstellation?.image_url ? (
                    <ConstellationImage
                      src={selectedConstellation.image_url}
                      alt={selectedConstellation.name_ko}
                    />
                  ) : (
                    <div>별자리 이미지를 불러올 수 없습니다.</div>
                  )}
                </ConstellationImageBox>


                {/* 결과 설명 */}
                <div>
                  {searchResult.constellation}는{' '}
                  {formData.date} {formData.time} 기준

                  <br />

                  {/* 현재 관측 불가 */}
                  {searchResult.observable === '현재 관측 불가' && (
                    <>
                      지평선 밑에 있어{' '}
                      <HighlightText>
                        관측이 불가능
                      </HighlightText>
                      {' '}합니다.
                    </>
                  )}

                  {/* 전체 관측 가능 */}
                  {searchResult.observable === '전체 관측 가능' && (
                    <>
                      <HighlightText>
                        {searchResult.direction}쪽하늘
                      </HighlightText>
                      {' '}고도 약{' '}
                      <HighlightText>
                        {searchResult.altitude}°
                      </HighlightText>
                      에서 관측할 수 있습니다.
                    </>
                  )}

                  {/* 일부 관측 가능 - 고도 5도 이상 */}
                  {searchResult.observable === '일부 관측 가능' &&
                    searchResult.altitude > 5 && (
                      <>
                        <HighlightText>
                          {searchResult.direction}쪽하늘
                        </HighlightText>
                        {' '}고도 약{' '}
                        <HighlightText>
                          {searchResult.altitude}°
                        </HighlightText>
                        에서 별자리 일부를 관측할 수 있습니다.
                      </>
                  )}

                  {/* 일부 관측 가능 - 고도 5도 미만 */}
                  {searchResult.observable === '일부 관측 가능' &&
                    searchResult.altitude <= 5 && (
                      <>
                        <HighlightText>
                          {searchResult.direction}쪽하늘
                        </HighlightText>
                        {' '}지평선 근처에서
                        별자리 일부를 관측할 수 있습니다.
                      </>
                  )}

                </div>
              </>
            )}

          </VisualizationSection>

        </MainContainer>
      </ContentWrapper>
    </PageContainer>
  )
}

export default ConstellationLocationPage