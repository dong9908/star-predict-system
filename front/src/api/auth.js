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
export const loginAPI = async ({ email, pwd, remember }) => {
  const response = await fetch('/api/member/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, pwd, remember }), // remember 값 전송
    credentials: 'include',
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || '이메일 또는 비밀번호가 올바르지 않습니다.');
  }
  return response.json();
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
  if (!response.ok) {
    const error = new Error('인증이 만료되었습니다. 다시 로그인해주세요.');
    error.status = response.status;
    throw error;
  }
  return response.json(); // { email, name, birth_date, phone, role }
};

// 6. 회원 정보 수정
export const updateMyInfoAPI = async (accessToken, profile) => {
  const response = await fetch('/api/member/me', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
    },
    body: JSON.stringify(profile),
  });

  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json')
    ? await response.json()
    : { detail: await response.text() };

  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map(item => item.msg).join('\n')
      : data.detail;
    const error = new Error(detail || '회원 정보 수정에 실패했습니다.');
    error.status = response.status;
    throw error;
  }
  return data;
};

// 7. 회원 탈퇴
export const deleteMyAccountAPI = async (accessToken, password) => {
  const response = await fetch('/api/member/me', {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
    },
    credentials: 'include',
    body: JSON.stringify({ pwd: password }),
  });

  if (!response.ok) {
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json')
      ? await response.json()
      : { detail: await response.text() };
    const error = new Error(data.detail || '회원 탈퇴에 실패했습니다.');
    error.status = response.status;
    throw error;
  }
};

// 8. 별자리 위치 조회
export const getConstellationPositionAPI = async ({
  constellation,
  date,
  time,
  latitude,
  longitude,
}) => {
  const response = await fetch('/api/constellation/position', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      constellation,
      date,
      time,
      latitude: Number(latitude),
      longitude: Number(longitude),
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(
      errorData.detail ||
      errorData.message ||
      '별자리 위치 조회에 실패했습니다.'
    );
  }

  return response.json();
};

// 9. 별자리 전체 목록 조회
export const getConstellationsAPI = async () => {
  const response = await fetch('/api/constellation/', {
    method: 'GET',
  });

  if (!response.ok) {
    const errorData = await response.json();

    throw new Error(
      errorData.detail || '별자리 목록을 불러오는데 실패했습니다.'
    );
  }

  return response.json();
};

// 10. 별자리 간략 목록 조회
export const getConstellationCatalogAPI = async () => {
  const response = await fetch('/api/constellation/catalog', {
    method: 'GET',
  });

  if (!response.ok) {
    const errorData = await response.json();

    throw new Error(
      errorData.detail ||
      '별자리 간략 목록을 불러오는데 실패했습니다.'
    );
  }

  return response.json();
};

// 11. 개인 도감용 별자리 목록 조회
export const getCatalogMyAPI = async (accessToken) => {
  const response = await fetch('/api/constellation/catalog/my', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  })

  if (!response.ok) {
    const contentType = response.headers.get('content-type') || ''
    const errorData = contentType.includes('application/json')
      ? await response.json()
      : { detail: await response.text() }

    const error = new Error(
      errorData.detail ||
      '개인 도감 정보를 불러오는데 실패했습니다.'
    )
    error.status = response.status
    throw error
  }

  return response.json()
}
