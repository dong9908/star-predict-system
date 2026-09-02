// 1. 이메일 중복 확인
export const emailCheckAPI = async (email) => {
  const response = await fetch(`/api/member/emailCheck/${encodeURIComponent(email)}`, {
    method: 'GET',
  });
  if (!response.ok) {
    throw new Error('이메일 중복 확인 중 오류가 발생했습니다.');
  }
  return response.json(); // { isFind: true/false }
};

// 2. 회원가입 요청 (birthDate, phone 추가)
export const signupAPI = async ({ name, email, pwd, birthDate, phone }) => {
  const response = await fetch('/api/member/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, pwd, birthDate, phone }),
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || '회원가입에 실패했습니다.');
  }
  return response.json(); // { isSignup: true, message: "..." }
};

// 3. 로그인 요청
export const loginAPI = async ({ email, pwd }) => {
  const response = await fetch('/api/member/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, pwd }),
    credentials: 'include', // RefreshToken 쿠키 수신
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || '이메일 또는 비밀번호가 올바르지 않습니다.');
  }
  return response.json(); // { isLogin: true, accessToken, user }
};

// 4. 로그아웃 요청
export const logoutAPI = async () => {
  const response = await fetch('/api/member/logout', {
    method: 'POST',
    credentials: 'include', // RefreshToken 쿠키 만료 처리
  });
  if (!response.ok) {
    throw new Error('로그아웃 처리에 실패했습니다.');
  }
  return response.json(); // { isLogout: true }
};

// 5. 내 정보 확인 (토큰 유효성 검증)
export const getMyInfoAPI = async (accessToken) => {
  const response = await fetch('/api/member/me', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) throw new Error('인증이 만료되었습니다.');
  return response.json(); // { email, name, birth_date, phone, role }
};