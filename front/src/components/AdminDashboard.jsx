import { useState, useEffect } from 'react'
import {
  Container,
  HeaderArea,
  Title,
  Subtitle,
  TabsArea,
  TabButton,
  ContentArea,
  Card,
  CardHeaderRow,
  CardTitle,
  AddButton,
  Table,
  TableHeaderRow,
  Th,
  Td,
  TableRow,
  EmptyCell,
  ActionButtonGroup,
  DeleteButton,
  EditButton,
  LoadingWrapper,
  ModalOverlay,
  ModalContent,
  ModalTitle,
  StyledForm,
  StyledInput,
  StyledTextarea,
  ModalButtonGroup,
  CancelButton,
  SubmitButton,
} from './styles/AdminDashboard.js'

function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('users') // 'users', 'payments', 'constellations'
  const [users, setUsers] = useState([])
  const [payments, setPayments] = useState([])
  const [constellations, setConstellations] = useState([])
  const [loading, setLoading] = useState(true)

  // 별자리 등록/수정 모달 관련 상태
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [formData, setFormData] = useState({
    name_ko: '',
    name_en: '',
    description: '',
    mythology: '',
    difficulty: 1,
    image_url: '',
    abbreviation: ''
  })

  // 1. 처음 진입 시 회원 목록과 결제 내역을 함께 로드
  const fetchInitialData = async () => {
    try {
      const token = localStorage.getItem('accessToken')
      const requestOptions = {
        headers: { Authorization: `Bearer ${token}` }
      }

      const [userRes, payRes] = await Promise.all([
        fetch('http://127.0.0.1:8000/api/admin/users', requestOptions),
        fetch('http://127.0.0.1:8000/api/admin/payments', requestOptions)
      ])

      if (userRes.ok) setUsers(await userRes.json())
      if (payRes.ok) setPayments(await payRes.json())
    } catch (error) {
      console.error('관리자 데이터를 불러오는데 실패했습니다.', error)
    } finally {
      setLoading(false)
    }
  }

  // 2. 별자리 탭을 눌렀을 때만 비동기로 호출
  const fetchConstellations = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/constellation')
      if (res.ok) setConstellations(await res.json())
    } catch (error) {
      console.error('별자리 목록을 불러오는데 실패했습니다.', error)
    }
  }

  useEffect(() => {
    fetchInitialData()
  }, [])

  useEffect(() => {
    if (activeTab === 'constellations') {
      fetchConstellations()
    }
  }, [activeTab])

  // 사용자 탈퇴(삭제) 핸들러
  const handleDeleteUser = async (userId, userEmail) => {
    if (!window.confirm(`정말 [${userEmail}] 회원을 탈퇴(삭제)시키겠습니까?`)) return

    try {
      const token = localStorage.getItem('accessToken')
      const res = await fetch(`http://127.0.0.1:8000/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })

      if (res.ok) {
        alert('성공적으로 탈퇴 처리되었습니다.')
        fetchInitialData()
      } else {
        const errData = await res.json()
        alert(`탈퇴 처리 실패: ${errData.detail || '알 수 없는 오류'}`)
      }
    } catch (error) {
      console.error('회원 탈퇴 처리 중 에러 발생:', error)
      alert('회원 탈퇴 처리 중 오류가 발생했습니다.')
    }
  }

  // 별자리 등록 및 수정 핸들러
  const handleSaveConstellation = async (e) => {
    e.preventDefault()
    const token = localStorage.getItem('accessToken')
    const method = editingId ? 'PUT' : 'POST'
    const url = editingId 
      ? `http://127.0.0.1:8000/api/admin/constellations/${editingId}`
      : 'http://127.0.0.1:8000/api/admin/constellations'

    try {
      const res = await fetch(url, {
        method: method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      })

      if (res.ok) {
        alert(editingId ? '별자리 정보가 수정되었습니다.' : '새로운 별자리가 추가되었습니다.')
        setShowModal(false)
        setEditingId(null)
        setFormData({ name_ko: '', name_en: '', description: '', mythology: '', difficulty: 1, image_url: '', abbreviation: '' })
        fetchConstellations()
      } else {
        alert('처리에 실패했습니다.')
      }
    } catch (error) {
      console.error('별자리 저장 중 에러 발생:', error)
      alert('요청 중 오류가 발생했습니다.')
    }
  }

  // 별자리 삭제 핸들러
  const handleDeleteConstellation = async (constellationId, nameKo) => {
    if (!window.confirm(`정말 [${nameKo}] 별자리를 삭제하시겠습니까?`)) return

    try {
      const token = localStorage.getItem('accessToken')
      const res = await fetch(`http://127.0.0.1:8000/api/admin/constellations/${constellationId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })

      if (res.ok) {
        alert('별자리가 성공적으로 삭제되었습니다.')
        fetchConstellations()
      } else {
        alert('별자리 삭제에 실패했습니다.')
      }
    } catch (error) {
      console.error('별자리 삭제 중 에러 발생:', error)
      alert('요청 중 오류가 발생했습니다.')
    }
  }

  // 수정 모달 오픈
  const handleOpenEdit = (item) => {
    setEditingId(item.constellation_id)
    setFormData({
      name_ko: item.name_ko || '',
      name_en: item.name_en || '',
      description: item.description || '',
      mythology: item.mythology || '',
      difficulty: item.difficulty || 1,
      image_url: item.image_url || '',
      abbreviation: item.abbreviation || ''
    })
    setShowModal(true)
  }

  if (loading) {
    return <LoadingWrapper>관리자 데이터를 불러오는 중...</LoadingWrapper>
  }

  return (
    <Container>
      <HeaderArea>
        <Title>관리자 대시보드</Title>
        <Subtitle>회원 정보, 결제 내역 및 별자리 정보를 통합 관리합니다.</Subtitle>
      </HeaderArea>

      <TabsArea>
        <TabButton $active={activeTab === 'users'} onClick={() => setActiveTab('users')}>
          회원 목록 관리 ({users.length})
        </TabButton>
        <TabButton $active={activeTab === 'payments'} onClick={() => setActiveTab('payments')}>
          카카오페이 결제 내역 ({payments.length})
        </TabButton>
        <TabButton $active={activeTab === 'constellations'} onClick={() => setActiveTab('constellations')}>
          별자리 정보 관리 ({constellations.length})
        </TabButton>
      </TabsArea>

      <ContentArea>
        {activeTab === 'users' && (
          <Card>
            <CardTitle>가입된 회원 목록</CardTitle>
            <Table>
              <thead>
                <TableHeaderRow>
                  <Th $width="15%">ID</Th>
                  <Th $width="40%">이메일</Th>
                  <Th $width="30%">이름</Th>
                  <Th $width="15%" $align="center">관리</Th>
                </TableHeaderRow>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr><EmptyCell colSpan="4">등록된 회원이 없습니다.</EmptyCell></tr>
                ) : (
                  users.map(u => (
                    <TableRow key={u.user_id}>
                      <Td>{u.user_id}</Td>
                      <Td>{u.email}</Td>
                      <Td>{u.name}</Td>
                      <Td $align="center">
                        <DeleteButton onClick={() => handleDeleteUser(u.user_id, u.email)}>
                          강제 탈퇴
                        </DeleteButton>
                      </Td>
                    </TableRow>
                  ))
                )}
              </tbody>
            </Table>
          </Card>
        )}

        {activeTab === 'payments' && (
          <Card>
            <CardTitle>카카오페이 결제 내역</CardTitle>
            <Table>
              <thead>
                <TableHeaderRow>
                  <Th>결제 고유번호(TID)</Th>
                  <Th>회원 ID</Th>
                  <Th>상품명</Th>
                  <Th>결제 금액</Th>
                  <Th>상태</Th>
                  <Th>결제 일시</Th>
                </TableHeaderRow>
              </thead>
              <tbody>
                {payments.length === 0 ? (
                  <tr><EmptyCell colSpan="6">결제 내역이 없습니다.</EmptyCell></tr>
                ) : (
                  payments.map(p => (
                    <TableRow key={p.tid}>
                      <Td $size="0.85rem" $color="#94a3b8">{p.tid}</Td>
                      <Td>{p.user_id}</Td>
                      <Td>{p.item_name}</Td>
                      <Td $color="#34d399" $weight="600">{p.total_amount?.toLocaleString()}원</Td>
                      <Td>{p.status}</Td>
                      <Td $color="#94a3b8">{p.created_at || '-'}</Td>
                    </TableRow>
                  ))
                )}
              </tbody>
            </Table>
          </Card>
        )}

        {activeTab === 'constellations' && (
          <Card>
            <CardHeaderRow>
              <CardTitle>별자리 정보 관리</CardTitle>
              <AddButton
                onClick={() => {
                  setEditingId(null)
                  setFormData({ name_ko: '', name_en: '', description: '', mythology: '', difficulty: 1, image_url: '', abbreviation: '' })
                  setShowModal(true)
                }}
              >
                + 새 별자리 추가
              </AddButton>
            </CardHeaderRow>
            <Table>
              <thead>
                <TableHeaderRow>
                  <Th>ID</Th>
                  <Th>한글 이름</Th>
                  <Th>영문 이름</Th>
                  <Th>약자</Th>
                  <Th>난이도</Th>
                  <Th $align="center">관리</Th>
                </TableHeaderRow>
              </thead>
              <tbody>
                {constellations.length === 0 ? (
                  <tr><EmptyCell colSpan="6">등록된 별자리가 없습니다.</EmptyCell></tr>
                ) : (
                  constellations.map(c => (
                    <TableRow key={c.constellation_id}>
                      <Td>{c.constellation_id}</Td>
                      <Td>{c.name_ko}</Td>
                      <Td>{c.name_en}</Td>
                      <Td>{c.abbreviation || '-'}</Td>
                      <Td>{c.difficulty}</Td>
                      <Td $align="center">
                        <ActionButtonGroup>
                          <EditButton onClick={() => handleOpenEdit(c)}>수정</EditButton>
                          <DeleteButton onClick={() => handleDeleteConstellation(c.constellation_id, c.name_ko)}>삭제</DeleteButton>
                        </ActionButtonGroup>
                      </Td>
                    </TableRow>
                  ))
                )}
              </tbody>
            </Table>
          </Card>
        )}
      </ContentArea>

      {showModal && (
        <ModalOverlay>
          <ModalContent>
            <ModalTitle>{editingId ? '별자리 정보 수정' : '새 별자리 추가'}</ModalTitle>
            <StyledForm onSubmit={handleSaveConstellation}>
              <StyledInput type="text" placeholder="한글 이름 (예: 안드로메다자리)" value={formData.name_ko} onChange={e => setFormData({...formData, name_ko: e.target.value})} required />
              <StyledInput type="text" placeholder="영문 이름 (예: Andromeda)" value={formData.name_en} onChange={e => setFormData({...formData, name_en: e.target.value})} required />
              <StyledInput type="text" placeholder="약자 (예: And)" value={formData.abbreviation} onChange={e => setFormData({...formData, abbreviation: e.target.value})} />
              <StyledInput type="number" placeholder="난이도 (숫자)" value={formData.difficulty} onChange={e => setFormData({...formData, difficulty: Number(e.target.value)})} />
              <StyledTextarea placeholder="설명" value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} />
              <StyledTextarea placeholder="신화 이야기" value={formData.mythology} onChange={e => setFormData({...formData, mythology: e.target.value})} />
              <StyledInput type="text" placeholder="이미지 URL" value={formData.image_url} onChange={e => setFormData({...formData, image_url: e.target.value})} />
              
              <ModalButtonGroup>
                <CancelButton type="button" onClick={() => setShowModal(false)}>취소</CancelButton>
                <SubmitButton type="submit">저장하기</SubmitButton>
              </ModalButtonGroup>
            </StyledForm>
          </ModalContent>
        </ModalOverlay>
      )}
    </Container>
  )
}

export default AdminDashboard