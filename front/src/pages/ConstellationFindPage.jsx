import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Cloud, MapPin, Zap } from 'lucide-react'
import {
  PageContainer,
  ContentWrapper,
  ProcessIndicator,
  ProcessStep,
  StepCircle,
  StepLabel,
  MainTitle,
  MainDescription,
  UploadArea,
  UploadIcon,
  UploadLabel,
  UploadText,
  UploadSubText,
  FileInput,
  SelectButton,
  FeaturesGrid,
  FeatureBox,
  FeatureIcon,
  FeatureTitle,
  FeatureDescription,
} from './styles/ConstellationFindPage.styles'

function ConstellationFindPage() {
  const navigate = useNavigate()
  const [dragActive, setDragActive] = useState(false)
  const [uploadedFile, setUploadedFile] = useState(null)
  const fileInputRef = useRef(null)

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleFile = (file) => {
    if (file.type.startsWith('image/')) {
      setUploadedFile(file)
    } else {
      alert('이미지 파일만 업로드 가능합니다.')
    }
  }

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleSelectFile = () => {
    fileInputRef.current?.click()
  }

  const features = [
    {
      icon: '🌙',
      title: '어둠은 장소에서 촬영',
      description: '별이 잘 보이는 어두운 곳에서 촬영해주세요.',
    },
    {
      icon: '📷',
      title: '카메라를 흔들지 않기',
      description: '삼각대나 안정적인 곳에서 촬영하세요.',
    },
    {
      icon: '✨',
      title: '별이 선명한 사진',
      description: '초점을 별에 맞춰 선명하게 촬영하세요.',
    },
  ]

  return (
    <PageContainer>
      <ContentWrapper>
        {/* Process Indicator */}
        <ProcessIndicator>
          <ProcessStep>
            <StepCircle $active>01</StepCircle>
            <StepLabel>사진 업로드</StepLabel>
          </ProcessStep>
          <ProcessStep>
            <StepCircle>02</StepCircle>
            <StepLabel>별자리 분석</StepLabel>
          </ProcessStep>
          <ProcessStep>
            <StepCircle>03</StepCircle>
            <StepLabel>결과 확인</StepLabel>
          </ProcessStep>
        </ProcessIndicator>

        {/* Main Content */}
        <MainTitle>밤하늘 사진을 올려주세요</MainTitle>
        <MainDescription>
          사진 속 별자리를 AI가 찾아 암면주세요.
        </MainDescription>

        {/* Upload Area */}
        <UploadArea
          $dragActive={dragActive}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <UploadIcon>📸</UploadIcon>
          <UploadLabel>
            <UploadText>사진을 드래그하거나 클릭해 업로드</UploadText>
            <UploadSubText>JPG, PNG · 최대 10MB</UploadSubText>
            <SelectButton onClick={handleSelectFile}>
              사진 선택
            </SelectButton>
          </UploadLabel>
          <FileInput
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png"
            onChange={handleFileInput}
          />
        </UploadArea>

        {uploadedFile && (
          <div style={{ textAlign: 'center' }}>
            <p style={{ color: '#10b981', fontSize: '0.875rem', marginBottom: '1rem' }}>
              ✓ {uploadedFile.name} 선택됨
            </p>
            <button
              onClick={() => navigate('/constellation-find-result', { state: { image: uploadedFile } })}
              style={{
                padding: '0.75rem 2rem',
                background: '#a78bfa',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                fontSize: '1rem',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
              }}
              onMouseOver={(e) => {
                e.target.style.background = '#c084fc'
                e.target.style.transform = 'translateY(-2px)'
              }}
              onMouseOut={(e) => {
                e.target.style.background = '#a78bfa'
                e.target.style.transform = 'translateY(0)'
              }}
            >
              분석하기
            </button>
          </div>
        )}

        {/* Features Grid */}
        <FeaturesGrid>
          {features.map((feature, index) => (
            <FeatureBox key={index}>
              <FeatureIcon>{feature.icon}</FeatureIcon>
              <FeatureTitle>{feature.title}</FeatureTitle>
              <FeatureDescription>{feature.description}</FeatureDescription>
            </FeatureBox>
          ))}
        </FeaturesGrid>
      </ContentWrapper>
    </PageContainer>
  )
}

export default ConstellationFindPage
