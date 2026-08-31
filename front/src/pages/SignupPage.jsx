import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
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

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (formData.password !== formData.passwordConfirm) {
      alert('비밀번호가 일치하지 않습니다.')
      return
    }
    alert('회원가입 요청이 정상 처리되었습니다.')
    navigate('/')
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
              type="tel"
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

          <SubmitButton type="submit">회원가입</SubmitButton>
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
