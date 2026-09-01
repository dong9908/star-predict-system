import { useState } from 'react'
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
  CheckStatus,
  VisualizationSection,
  StepLabel,
  VisualizationPlaceholder,
} from './styles/ConstellationLocationPage.styles'

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

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleLocationConfirm = () => {
    if (formData.latitude && formData.longitude) {
      setLocationConfirmed(true)
    } else {
      alert('위도와 경도를 입력해주세요.')
    }
  }

  const handleUseCurrentTime = () => {
    if (useCurrentTime) {
      const now = new Date()
      const dateStr = now.toISOString().split('T')[0]
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
      setFormData(prev => ({
        ...prev,
        date: dateStr,
        time: timeStr,
      }))
    }
  }

  return (
    <PageContainer>
      <ContentWrapper>
        <PageHeader>
          <PageTitle>별자리 위치</PageTitle>
          <PageDescription>
            지금 내 위치에서 원하는 별자리를 찾아보세요
          </PageDescription>
        </PageHeader>

        <MainContainer>
          {/* Form Section */}
          <FormSection>
            {/* 01. 별자리 입력 */}
            <FormGroup>
              <FormGroupNumber>01</FormGroupNumber>
              <FormGroupTitle>첫 글자 별자리를 입력해주세요</FormGroupTitle>
              <FormGroupContent>
                <Input
                  type="text"
                  name="constellation"
                  value={formData.constellation}
                  onChange={handleInputChange}
                  placeholder="오리온자리"
                />
              </FormGroupContent>
            </FormGroup>

            {/* 02. 날짜 및 시간 */}
            <FormGroup>
              <FormGroupNumber>02</FormGroupNumber>
              <FormGroupTitle>관측할 날짜와 시간을 입력해주세요</FormGroupTitle>
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
                      setUseCurrentTime(e.target.checked)
                      if (e.target.checked) {
                        handleUseCurrentTime()
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
              <FormGroupTitle>위치 설정 버튼을 눌러 위치를 지정해주세요</FormGroupTitle>
              <FormGroupContent>
                <Input
                  type="number"
                  name="latitude"
                  value={formData.latitude}
                  onChange={handleInputChange}
                  placeholder="위도 (예: 37.5)"
                  step="0.01"
                />
                <Input
                  type="number"
                  name="longitude"
                  value={formData.longitude}
                  onChange={handleInputChange}
                  placeholder="경도 (예: 127.0)"
                  step="0.01"
                />
                <LocationButton onClick={handleLocationConfirm}>
                  위치 설정
                </LocationButton>
                {locationConfirmed && (
                  <CheckStatus>
                    <Check size={16} />
                    현재 위치 설정 완료!
                  </CheckStatus>
                )}
              </FormGroupContent>
            </FormGroup>
          </FormSection>

          {/* Visualization Section */}
          <VisualizationSection>
            <StepLabel>04 별자리 위치</StepLabel>
            <VisualizationPlaceholder>
              <p>📍 별자리 시각화 영역</p>
              <p style={{ fontSize: '0.75rem', marginTop: '0.5rem' }}>
                입력 정보를 바탕으로 별자리 위치가 표시됩니다
              </p>
            </VisualizationPlaceholder>
          </VisualizationSection>
        </MainContainer>
      </ContentWrapper>
    </PageContainer>
  )
}

export default ConstellationLocationPage
