import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, AlertCircle } from 'lucide-react'
import {
  PageContainer,
  FormWrapper,
  PageHeader,
  BackButton,
  PageTitle,
  FormCard,
  FormGroup,
  Label,
  InputWrapper,
  Input,
  AtSymbol,
  ErrorMessage,
  SuccessMessage,
  GeneralError,
  SubmitButton,
  LoadingSpinner,
  PasswordRequirements,
  FormDivider,
  InfoText,
} from './styles/EditProfilePage.styles'

function EditProfilePage() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [generalError, setGeneralError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const [formData, setFormData] = useState({
    name: '',
    birthDate: '',
    emailPrefix: '',
    emailDomain: '',
    password: '',
    passwordConfirm: '',
    phone: '',
  })

  const [errors, setErrors] = useState({
    name: '',
    birthDate: '',
    email: '',
    password: '',
    passwordConfirm: '',
    phone: '',
  })

  // 사용자 정보 로드
  useEffect(() => {
    const userString = localStorage.getItem('user')
    if (!userString) {
      navigate('/login')
      return
    }

    const user = JSON.parse(userString)
    const [emailPrefix, emailDomain] = user.email ? user.email.split('@') : ['', '']

    setFormData(prev => ({
      ...prev,
      name: user.name || '',
      birthDate: user.birthDate || '',
      emailPrefix: emailPrefix || '',
      emailDomain: emailDomain || '',
      phone: user.phone || '',
    }))
  }, [navigate])

  // 입력값 변경 처리
  const handleChange = e => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }))
    // 입력 시 해당 필드의 에러 제거
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: '',
      }))
    }
  }

  // 휴대폰 번호 자동 포맷팅
  const formatPhoneNumber = value => {
    const numbers = value.replace(/\D/g, '')
    if (numbers.length <= 3) return numbers
    if (numbers.length <= 7) return `${numbers.slice(0, 3)}-${numbers.slice(3)}`
    return `${numbers.slice(0, 3)}-${numbers.slice(3, 7)}-${numbers.slice(7, 11)}`
  }

  const handlePhoneChange = e => {
    const formatted = formatPhoneNumber(e.target.value)
    setFormData(prev => ({
      ...prev,
      phone: formatted,
    }))
  }

  // 유효성 검사
  const validateForm = () => {
    const newErrors = {}

    // 이름 검사
    if (!formData.name || formData.name.trim().length < 2) {
      newErrors.name = '이름은 2자 이상이어야 합니다'
    } else if (formData.name.length > 50) {
      newErrors.name = '이름은 50자 이하여야 합니다'
    }

    // 생년월일 검사
    if (!formData.birthDate) {
      newErrors.birthDate = '생년월일을 입력하세요'
    }

    // 이메일 검사
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    const fullEmail = `${formData.emailPrefix}@${formData.emailDomain}`
    if (!formData.emailPrefix || !formData.emailDomain) {
      newErrors.email = '이메일을 입력하세요'
    } else if (!emailRegex.test(fullEmail)) {
      newErrors.email = '유효한 이메일 형식이 아닙니다'
    }

    // 비밀번호 검사 (선택)
    if (formData.password) {
      if (formData.password.length < 8) {
        newErrors.password = '비밀번호는 8자 이상이어야 합니다'
      } else if (formData.password !== formData.passwordConfirm) {
        newErrors.passwordConfirm = '비밀번호가 일치하지 않습니다'
      }
    }

    // 휴대폰 검사
    const phoneNumbers = formData.phone.replace(/\D/g, '')
    if (!formData.phone || phoneNumbers.length < 10) {
      newErrors.phone = '유효한 휴대폰 번호를 입력하세요'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // 폼 제출
  const handleSubmit = async e => {
    e.preventDefault()
    setGeneralError('')
    setSuccessMessage('')

    if (!validateForm()) {
      return
    }

    setIsLoading(true)

    try {
      // 실제 API 호출은 여기에 구현
      // const response = await fetch('/api/users/profile', {
      //   method: 'PUT',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({
      //     name: formData.name,
      //     birthDate: formData.birthDate,
      //     email: `${formData.emailPrefix}@${formData.emailDomain}`,
      //     phone: formData.phone,
      //     ...(formData.password && { password: formData.password }),
      //   }),
      // })

      // 임시로 localStorage 업데이트
      const updatedUser = {
        ...JSON.parse(localStorage.getItem('user')),
        name: formData.name,
        birthDate: formData.birthDate,
        email: `${formData.emailPrefix}@${formData.emailDomain}`,
        phone: formData.phone,
      }
      localStorage.setItem('user', JSON.stringify(updatedUser))

      setSuccessMessage('회원 정보가 저장되었습니다')
      setTimeout(() => {
        navigate('/mypage')
      }, 1500)
    } catch (error) {
      setGeneralError('회원 정보 저장 중 오류가 발생했습니다. 다시 시도해주세요.')
      console.error('Error updating profile:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <PageContainer>
      <FormWrapper>
        <PageHeader>
          <BackButton onClick={() => navigate('/mypage')}>
            <ChevronLeft size={20} />
            돌아가기
          </BackButton>
        </PageHeader>

        <PageTitle>회원 정보 수정</PageTitle>

        <FormCard>
          {generalError && (
            <GeneralError>
              <AlertCircle size={16} />
              {generalError}
            </GeneralError>
          )}

          <form onSubmit={handleSubmit}>
            {/* 이름 */}
            <FormGroup>
              <Label htmlFor="name">이름</Label>
              <Input
                id="name"
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="이름을 입력하세요"
                disabled={isLoading}
              />
              {errors.name && <ErrorMessage>{errors.name}</ErrorMessage>}
            </FormGroup>

            {/* 생년월일 */}
            <FormGroup>
              <Label htmlFor="birthDate">생년월일</Label>
              <Input
                id="birthDate"
                type="text"
                name="birthDate"
                value={formData.birthDate}
                onChange={handleChange}
                placeholder="2000.04.12"
                disabled={isLoading}
              />
              {errors.birthDate && <ErrorMessage>{errors.birthDate}</ErrorMessage>}
            </FormGroup>

            {/* 이메일 */}
            <FormGroup>
              <Label>이메일</Label>
              <InputWrapper $flex $gap="0.5rem">
                <Input
                  type="text"
                  name="emailPrefix"
                  value={formData.emailPrefix}
                  onChange={handleChange}
                  placeholder="user"
                  disabled={isLoading}
                  $flex="1"
                />
                <AtSymbol>@</AtSymbol>
                <Input
                  type="text"
                  name="emailDomain"
                  value={formData.emailDomain}
                  onChange={handleChange}
                  placeholder="example.com"
                  disabled={isLoading}
                  $flex="1"
                />
              </InputWrapper>
              {errors.email && <ErrorMessage>{errors.email}</ErrorMessage>}
            </FormGroup>

            <FormDivider />

            {/* 비밀번호 */}
            <FormGroup>
              <Label htmlFor="password">비밀번호</Label>
              <Input
                id="password"
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="새 비밀번호를 입력하세요 (선택사항)"
                disabled={isLoading}
              />
              {errors.password && <ErrorMessage>{errors.password}</ErrorMessage>}
              {formData.password && (
                <PasswordRequirements>
                  <p>✓ 8자 이상</p>
                  <p>✓ 영문, 숫자, 특수문자 조합 권장</p>
                </PasswordRequirements>
              )}
            </FormGroup>

            {/* 비밀번호 확인 */}
            {formData.password && (
              <FormGroup>
                <Label htmlFor="passwordConfirm">비밀번호 확인</Label>
                <Input
                  id="passwordConfirm"
                  type="password"
                  name="passwordConfirm"
                  value={formData.passwordConfirm}
                  onChange={handleChange}
                  placeholder="비밀번호를 다시 입력하세요"
                  disabled={isLoading}
                />
                {errors.passwordConfirm && <ErrorMessage>{errors.passwordConfirm}</ErrorMessage>}
                {formData.passwordConfirm &&
                  formData.password === formData.passwordConfirm && (
                    <SuccessMessage>✓ 비밀번호가 일치합니다</SuccessMessage>
                  )}
              </FormGroup>
            )}

            <FormDivider />

            {/* 휴대폰 */}
            <FormGroup>
              <Label htmlFor="phone">휴대폰</Label>
              <Input
                id="phone"
                type="tel"
                name="phone"
                value={formData.phone}
                onChange={handlePhoneChange}
                placeholder="010-1234-5678"
                disabled={isLoading}
              />
              {errors.phone && <ErrorMessage>{errors.phone}</ErrorMessage>}
            </FormGroup>

            {/* 저장 버튼 */}
            <SubmitButton type="submit" disabled={isLoading}>
              {isLoading ? (
                <>
                  <LoadingSpinner /> 저장 중...
                </>
              ) : (
                '저장하기'
              )}
            </SubmitButton>

            {successMessage && (
              <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                <SuccessMessage>{successMessage}</SuccessMessage>
              </div>
            )}
          </form>

          <InfoText>비밀번호를 입력하지 않으면 기존 비밀번호가 유지됩니다.</InfoText>
        </FormCard>
      </FormWrapper>
    </PageContainer>
  )
}

export default EditProfilePage
