import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MessageCircle, Chrome } from 'lucide-react'
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

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    alert('로그인 요청이 정상 처리되었습니다.')
    navigate('/')
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

          <SubmitButton type="submit">로그인</SubmitButton>
        </Form>

        <LinksGroup>
          <span>
            계정이 없으신가요?{' '}
            <SignupLink onClick={() => navigate('/signup')}>회원가입</SignupLink>
          </span>
          <ForgotLink href="#">아이디/비밀번호 찾기</ForgotLink>
        </LinksGroup>

        <Divider>
          <DividerText>간편 로그인</DividerText>
        </Divider>

        <SocialButtonsGroup>
          <SocialButton>
            <SocialIcon>
              <MessageCircle size={16} color="#facc15" />
            </SocialIcon>
            카카오
          </SocialButton>
          <SocialButton>
            <SocialIcon>
              <Chrome size={16} color="#60a5fa" />
            </SocialIcon>
            구글
          </SocialButton>
        </SocialButtonsGroup>
      </FormWrapper>
    </FormContainer>
  )
}

export default LoginPage
