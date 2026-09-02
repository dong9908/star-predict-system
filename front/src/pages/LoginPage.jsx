import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loginAPI } from '../api/auth'
import {
  FormContainer,
  FormWrapper,
  Title,
  Form,
  FormGroup,
  Label,
  Input,
  CheckboxGroup,
  CheckboxInput,
  CheckboxLabel,
  SubmitButton,
  LinksGroup,
  SignupLink,
  ForgotLink,
  Divider,
  DividerText,
  SocialButtonsGroup,
  SocialButton,
  SocialIcon,
} from './styles/LoginPage.styles'

function LoginPage() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    remember: false,
  })
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      // 1. 백엔드로 로그인 요청
      const data = await loginAPI({
        email: formData.email.trim(),
        pwd: formData.password,
      })

      // 2. 서버가 준 토큰을 Local Storage에 저장
      if (data.accessToken) {
        localStorage.setItem('accessToken', data.accessToken)
        localStorage.setItem('user', JSON.stringify(data.user))
      }

      alert('로그인이 완료되었습니다!')
      navigate('/') // 메인 페이지로 이동
    } catch (error) {
      alert(error.message || '이메일 또는 비밀번호가 올바르지 않습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <FormContainer>
      <FormWrapper>
        <Title>로그인</Title>

        <Form onSubmit={handleSubmit}>
          <FormGroup>
            <Label>이메일</Label>
            <Input
              type="email"
              name="email"
              required
              placeholder="name@example.com"
              value={formData.email}
              onChange={handleChange}
            />
          </FormGroup>

          <FormGroup>
            <Label>비밀번호</Label>
            <Input
              type="password"
              name="password"
              required
              placeholder="••••••••"
              value={formData.password}
              onChange={handleChange}
            />
          </FormGroup>

          <CheckboxGroup>
            <CheckboxInput
              type="checkbox"
              id="login-stay"
              name="remember"
              checked={formData.remember}
              onChange={handleChange}
            />
            <CheckboxLabel htmlFor="login-stay">로그인 유지</CheckboxLabel>
          </CheckboxGroup>

          <SubmitButton type="submit" disabled={loading}>
            {loading ? '로그인 중...' : '로그인'}
          </SubmitButton>
        </Form>

        <LinksGroup>
          <span>
            계정이 없으신가요?{' '}
            <SignupLink onClick={() => navigate('/signup')}>회원가입</SignupLink>
          </span>
          <ForgotLink href="#">아이디/비밀번호 찾기</ForgotLink>
        </LinksGroup>
      </FormWrapper>
    </FormContainer>
  )
}

export default LoginPage