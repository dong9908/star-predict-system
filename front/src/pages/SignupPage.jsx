import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { signupAPI } from '../api/auth'
import {
  FormContainer,
  FormWrapper,
  Title,
  Form,
  FormGroup,
  Label,
  Input,
  EmailGroup,
  EmailSeparator,
  CheckboxGroup,
  CheckboxInput,
  CheckboxLabel,
  SubmitButton,
  SignupLink,
} from './styles/SignupPage.styles'

function SignupPage() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    name: '',
    birthDate: '',
    emailId: '',
    emailDomain: '',
    password: '',
    passwordConfirm: '',
    phone: '',
    agreeTos: false,
  })
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target

    // 1. 생년월일: 숫자만 최대 8자리 입력 허용
    if (name === 'birthDate') {
      const onlyNumbers = value.replace(/[^0-9]/g, '').slice(0, 8)
      setFormData((prev) => ({ ...prev, birthDate: onlyNumbers }))
      return
    }

    // 2. 휴대폰 번호: 숫자 입력 시 자동으로 010-XXXX-XXXX 하이픈 포맷 적용
    if (name === 'phone') {
      const rawDigits = value.replace(/[^0-9]/g, '').slice(0, 11)
      let formattedPhone = rawDigits
      if (rawDigits.length > 3 && rawDigits.length <= 7) {
        formattedPhone = `${rawDigits.slice(0, 3)}-${rawDigits.slice(3)}`
      } else if (rawDigits.length > 7) {
        formattedPhone = `${rawDigits.slice(0, 3)}-${rawDigits.slice(3, 7)}-${rawDigits.slice(7)}`
      }
      setFormData((prev) => ({ ...prev, phone: formattedPhone }))
      return
    }

    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    // 비밀번호 확인
    if (formData.password !== formData.passwordConfirm) {
      alert('비밀번호가 일치하지 않습니다.')
      return
    }

    // 생년월일 8자리 검증 (예: 20030909)
    if (formData.birthDate.length !== 8) {
      alert('생년월일을 8자리 숫자(YYYYMMDD)로 정확히 입력해 주세요. (예: 20030909)')
      return
    }

    // 약관 동의 체크
    if (!formData.agreeTos) {
      alert('이용약관 및 개인정보처리방침에 동의해 주세요.')
      return
    }

    setLoading(true)
    try {
      // 이메일 결합
      const email = `${formData.emailId.trim()}@${formData.emailDomain.trim()}`

      // 생년월일을 DB DATE 규격(YYYY-MM-DD)으로 변환
      const formattedBirthDate = `${formData.birthDate.slice(0, 4)}-${formData.birthDate.slice(4, 6)}-${formData.birthDate.slice(6, 8)}`

      // 회원가입 API 호출
      await signupAPI({
        name: formData.name.trim(),
        email: email,
        pwd: formData.password,
        birthDate: formattedBirthDate,
        phone: formData.phone.trim(),
      })

      alert('회원가입이 완료되었습니다! 로그인해 주세요.')
      navigate('/login')
    } catch (error) {
      alert(error.message || '회원가입 처리 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <FormContainer>
      <FormWrapper>
        <Title>회원가입</Title>

        <Form onSubmit={handleSubmit}>
          <FormGroup>
            <Label>이름</Label>
            <Input
              type="text"
              name="name"
              required
              placeholder="홍길동"
              value={formData.name}
              onChange={handleChange}
            />
          </FormGroup>

          <FormGroup>
            <Label>생년월일</Label>
            <Input
              type="text"
              name="birthDate"
              required
              maxLength={8}
              placeholder="YYYYMMDD (예: 20030909)"
              value={formData.birthDate}
              onChange={handleChange}
            />
          </FormGroup>

          <FormGroup>
            <Label>이메일</Label>
            <EmailGroup>
              <Input
                type="text"
                name="emailId"
                required
                placeholder="이메일 아이디"
                value={formData.emailId}
                onChange={handleChange}
                style={{ flex: 1 }}
              />
              <EmailSeparator>@</EmailSeparator>
              <Input
                type="text"
                name="emailDomain"
                required
                placeholder="example.com"
                value={formData.emailDomain}
                onChange={handleChange}
                style={{ flex: 1 }}
              />
            </EmailGroup>
          </FormGroup>

          <FormGroup>
            <Label>비밀번호</Label>
            <Input
              type="password"
              name="password"
              required
              placeholder="8자 이상 영문, 숫자 조합"
              value={formData.password}
              onChange={handleChange}
            />
          </FormGroup>

          <FormGroup>
            <Label>비밀번호 확인</Label>
            <Input
              type="password"
              name="passwordConfirm"
              required
              placeholder="비밀번호 재입력"
              value={formData.passwordConfirm}
              onChange={handleChange}
            />
          </FormGroup>

          <FormGroup>
            <Label>휴대폰 번호</Label>
            <Input
              type="text"
              name="phone"
              required
              placeholder="010-0000-0000"
              value={formData.phone}
              onChange={handleChange}
            />
          </FormGroup>

          <CheckboxGroup>
            <CheckboxInput
              type="checkbox"
              id="signup-terms"
              name="agreeTos"
              required
              checked={formData.agreeTos}
              onChange={handleChange}
            />
            <CheckboxLabel htmlFor="signup-terms">
              이용약관 및 개인정보처리방침 동의 (필수)
            </CheckboxLabel>
          </CheckboxGroup>

          <SubmitButton type="submit" disabled={loading}>
            {loading ? '처리 중...' : '회원가입'}
          </SubmitButton>
        </Form>

        <div style={{ textAlign: 'center', fontSize: '0.75rem', color: '#94a3b8', marginTop: '1rem' }}>
          이미 계정이 있으신가요?{' '}
          <SignupLink onClick={() => navigate('/login')}>로그인</SignupLink>
        </div>
      </FormWrapper>
    </FormContainer>
  )
}

export default SignupPage